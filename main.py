import os
import asyncio
import requests
import logging
import sys
from web3 import Web3

# ===== Web3 V6 完全兼容 =====
try:
    from web3.middleware import ExtraDataToPOAMiddleware
    geth_poa_middleware = ExtraDataToPOAMiddleware
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

# ================= RPC（Alchemy） =================
RPC_URL = os.getenv(
    "ALCHEMY_RPC_URL",
    "https://polygon-mainnet.g.alchemy.com/v2/duKptaPdJfV8R0-y8-VxY"
)

def get_w3():
    while True:
        try:
            w3 = Web3(Web3.HTTPProvider(
                RPC_URL,
                request_kwargs={"timeout": 10}
            ))

            # 注入 middleware（兼容所有版本）
            if geth_poa_middleware:
                try:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except:
                    pass

            # 强检测（比 is_connected 稳）
            w3.eth.block_number

            logger.info("✅ RPC连接成功")
            return w3

        except Exception as e:
            logger.error(f"❌ RPC失败: {e}")
            asyncio.run(asyncio.sleep(5))

# ================= 余额 =================
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

ERC20_ABI = [{
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
            abi=ERC20_ABI
        )

        matic = w3.eth.get_balance(addr) / 1e18
        usdc = contract.functions.balanceOf(addr).call() / 1e6

        logger.info(f"📊 余额: {usdc:.2f} USDC | {matic:.4f} MATIC")
        return usdc, matic

    except Exception as e:
        logger.error(f"❌ 余额读取失败: {e}")
        return 0, 0

# ================= 市场 =================
BASE = "https://clob.polymarket.com"

def get_markets():
    try:
        r = requests.get(f"{BASE}/sampling-markets", timeout=10).json()
        data = r if isinstance(r, list) else r.get("data", [])
        return [m for m in data if "tokens" in m][:10]
    except:
        return []

def get_book(token_id):
    try:
        r = requests.get(f"{BASE}/book?token_id={token_id}", timeout=5).json()

        bids = r.get("bids", [])
        asks = r.get("asks", [])

        best_bid = float(bids[0]["price"]) if bids else 0
        best_ask = float(asks[0]["price"]) if asks else 1

        return best_bid, best_ask

    except:
        return 0, 1

# ================= 风控 =================
def calc_size(usdc):
    return max(1, min(usdc * 0.1, 10))

def safe_order(client, order):
    try:
        res = client.post_order(order)
        return bool(res)
    except:
        return False

# ================= 主程序 =================
async def main():
    logger.info("🚀 Lobster-Final 实盘启动")

    w3 = get_w3()
    usdc, matic = get_balance(w3)

    if matic < 0.1:
        logger.error("❌ MATIC不足")
        send_tg("❌ MATIC不足，无法交易")
        return

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
            logger.info(f"🔎 扫描市场: {len(markets)}")

            for m in markets:
                try:
                    q = m.get("question", "")
                    tokens = m.get("tokens", [])

                    if len(tokens) < 2:
                        continue

                    y_id = tokens[0]["token_id"]
                    n_id = tokens[1]["token_id"]

                    y_bid, y_ask = get_book(y_id)
                    n_bid, n_ask = get_book(n_id)

                    total = y_ask + n_ask

                    if 0.1 < total < 0.96:
                        logger.info(f"🔥 套利机会: {total:.3f}")

                        order_size = calc_size(usdc)

                        ok1 = await asyncio.to_thread(safe_order, client, {
                            "price": round(y_ask, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": y_id
                        })

                        ok2 = await asyncio.to_thread(safe_order, client, {
                            "price": round(n_ask, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": n_id
                        })

                        if ok1 and ok2:
                            msg = f"✅ 套利成功 | 成本: {total:.3f} | 单量: {order_size}"
                            logger.info(msg)
                            send_tg(msg)
                        else:
                            logger.warning("❌ 对冲失败")

                    await asyncio.sleep(0.3)

                except Exception:
                    continue

            usdc, matic = get_balance(w3)
            await asyncio.sleep(20)

        except Exception as e:
            logger.error(f"💥 循环异常: {e}")
            await asyncio.sleep(5)

# ================= 启动 =================
if __name__ == "__main__":
    asyncio.run(main()

