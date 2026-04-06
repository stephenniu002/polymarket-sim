import os
import asyncio
import requests
import logging
import sys
from web3 import Web3

# ===== Web3 V6 兼容 =====
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except:
    try:
        from web3.middleware import geth_poa_middleware
    except:
        geth_poa_middleware = None

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 日志 =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LOBSTER-FINAL")

# ================= Telegram =================
def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": f"🦞 {msg}"},
                timeout=5
            )
        except:
            pass

# ================= RPC =================
RPC_URL = os.getenv(
    "ALCHEMY_RPC_URL",
    "https://polygon-mainnet.g.alchemy.com/v2/duKptaPdJfV8R0-y8-VxY"
)

async def get_w3():
    while True:
        try:
            w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 15}))

            if geth_poa_middleware:
                try:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except:
                    pass

            w3.eth.get_block_number()
            logger.info("✅ RPC 已连接")
            return w3

        except Exception as e:
            logger.error(f"❌ RPC失败: {e}")
            await asyncio.sleep(10)

# ================= 余额 =================
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

ABI = [{
    "constant": True,
    "inputs": [{"name": "_owner","type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance","type": "uint256"}],
    "type": "function"
}]

def get_balance(w3):
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_E),
            abi=ABI
        )

        matic = w3.eth.get_balance(addr) / 1e18
        usdc = contract.functions.balanceOf(addr).call() / 1e6

        logger.info(f"💰 资产: {usdc:.2f} USDC | {matic:.4f} MATIC")
        return usdc, matic

    except Exception as e:
        logger.error(f"❌ 余额失败: {e}")
        return 0, 0

# ================= 参数 =================
SPREAD = 0.03
ARB_THRESHOLD = 0.98

def calc_size(usdc):
    if usdc < 20:
        return 1.0
    elif usdc < 100:
        return usdc * 0.1
    else:
        return min(usdc * 0.05, 20)

BASE = "https://clob.polymarket.com"

# ================= 市场 =================
def get_markets():
    try:
        r = requests.get(f"{BASE}/sampling-markets", timeout=10).json()
        data = r if isinstance(r, list) else r.get("data", [])
        return [m for m in data if "tokens" in m][:6]  # 控制市场数量
    except:
        return []

def get_price(token_id):
    try:
        r = requests.get(f"{BASE}/book?token_id={token_id}", timeout=5).json()
        asks = r.get("asks", [])
        return float(asks[0]["price"]) if asks else 1.0
    except:
        return 1.0

# ================= 下单 =================
async def safe_order(client, token_id, price, size, side):
    try:
        res = await asyncio.to_thread(client.post_order, {
            "price": round(price, 3),
            "size": size,
            "side": side,
            "token_id": token_id
        })
        return res
    except Exception as e:
        logger.error(f"❌ 下单失败: {e}")
        return None

# ================= 核心策略 =================
async def process_market(client, y_id, n_id, usdc):

    y = get_price(y_id)
    n = get_price(n_id)
    total = y + n

    logger.info(f"📈 {y:.3f} + {n:.3f} = {total:.3f}")

    size = calc_size(usdc)

    # ================= 套利 =================
    if 0.1 < total < ARB_THRESHOLD:
        logger.info(f"🔥 套利触发 {total:.3f}")

        results = await asyncio.gather(
            safe_order(client, y_id, y + 0.002, size, "BUY"),
            safe_order(client, n_id, n + 0.002, size, "BUY")
        )

        if all(results):
            send_tg(f"💰 套利成功 {total:.3f}")
        return

    # ================= 做市 =================
    if y > 0.85 or y < 0.15:
        logger.info("⚠️ 趋势过强，跳过")
        return

    mid = (y + (1 - n)) / 2

    buy = max(0.01, mid - SPREAD)
    sell = min(0.99, mid + SPREAD)

    await asyncio.gather(
        safe_order(client, y_id, buy, size, "BUY"),
        safe_order(client, y_id, sell, size, "SELL")
    )

    logger.info(f"💰 做市: 买{buy:.3f} 卖{sell:.3f}")

# ================= 主程序 =================
async def main():

    logger.info("🚀 Lobster Final 启动")

    w3 = await get_w3()
    usdc, matic = get_balance(w3)

    if matic < 0.1:
        send_tg("⚠️ MATIC 不足")

    client = ClobClient(
        host=BASE,
        key=os.getenv("PRIVATE_KEY"),
        chain_id=137
    )

    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            markets = get_markets()
            logger.info(f"🔎 市场数: {len(markets)}")

            for m in markets:
                tokens = m.get("tokens", [])
                if len(tokens) < 2:
                    continue

                y_id = tokens[0]["token_id"]
                n_id = tokens[1]["token_id"]

                await process_market(client, y_id, n_id, usdc)
                await asyncio.sleep(0.5)

            usdc, matic = get_balance(w3)
            await asyncio.sleep(20)

        except Exception as e:
            logger.error(f"💥 主循环异常: {e}")
            await asyncio.sleep(10)

# ================= 启动 =================
if __name__ == "__main__":
    asyncio.run(main())

