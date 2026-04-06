import os
import asyncio
import requests
import logging
import sys
from web3 import Web3

# ===== Web3 兼容层 =====
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except:
    try:
        from web3.middleware import geth_poa_middleware
    except:
        geth_poa_middleware = None

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 1. 日志与通知 =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LOBSTER-PRO")

def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                          json={"chat_id": chat_id, "text": f"🦞 {msg}"}, timeout=5)
        except: pass

# ================= 2. 链上资产同步 (Alchemy) =================
RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://polygon-mainnet.g.alchemy.com/v2/duKptaPdJfV8R0-y8-VxY")
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

async def get_w3():
    while True:
        try:
            w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 15}))
            if geth_poa_middleware:
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            w3.eth.get_block_number()
            logger.info("✅ Alchemy 专线已连接")
            return w3
        except Exception as e:
            logger.error(f"❌ RPC故障: {e}")
            await asyncio.sleep(10)

def get_balance(w3):
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E), abi=ABI)
        matic = w3.eth.get_balance(addr) / 1e18
        usdc = contract.functions.balanceOf(addr).call() / 1e6
        logger.info(f"📊 资产: {usdc:.2f} USDC | {matic:.4f} MATIC")
        return usdc, matic
    except: return 0, 0

# ================= 3. 市场与下单逻辑 =================
def get_book(token_id):
    try:
        r = requests.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=5).json()
        asks = r.get("asks", [])
        return float(asks[0]["price"]) if asks else 1.0
    except: return 1.0

async def safe_order(client, token_id, price, size):
    try:
        res = await asyncio.to_thread(client.post_order, {
            "price": round(price, 3),
            "size": size,
            "side": "BUY",
            "token_id": token_id
        })
        # 只要返回结果包含 success 或订单 ID 就算成功发出
        return res.get("success") or "orderID" in str(res)
    except Exception as e:
        logger.error(f"下单异常: {e}")
        return False

# ================= 4. 主循环 =================
async def main():
    logger.info("🚀 Lobster-Pro 最终修复版启动...")
    w3 = await get_w3()
    usdc, matic = get_balance(w3)
    
    client = ClobClient(host="https://clob.polymarket.com", key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"), api_secret=os.getenv("POLY_SECRET"), api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            # 获取采样市场
            resp = requests.get("https://clob.polymarket.com/sampling-markets", timeout=10).json()
            markets = resp if isinstance(resp, list) else resp.get("data", [])

            for m in markets[:12]:
                tokens = m.get("tokens", [])
                if len(tokens) < 2: continue
                
                y_id, n_id = tokens[0]["token_id"], tokens[1]["token_id"]
                y_ask = get_book(y_id)
                n_ask = get_book(n_id)
                total = y_ask + n_ask

                # 核心套利逻辑
                if 0.1 < total < 0.965:
                    logger.info(f"🔥 捕获机会: {total:.3f}")
                    order_size = max(1.0, min(usdc * 0.1, 15.0)) # 动态仓位

                    # 利润敏感型调价策略
                    price_y, price_n = y_ask, n_ask
                    if total < 0.94: # 只有利润足够厚时，才加价 0.002 强行吃单
                        price_y += 0.002
                        price_n += 0.002
                    
                    # 并发下单
                    tasks = [
                        safe_order(client, y_id, price_y, order_size),
                        safe_order(client, n_id, price_n, order_size)
                    ]
                    results = await asyncio.gather(*tasks)

                    if all(results):
                        msg = f"✅ 对冲成功 | 成本: {total:.3f} | 规模: {order_size}"
                        send_tg(msg)
                        logger.info(msg)
                        await asyncio.sleep(5)
                    elif any(results):
                        logger.warning("⚠️ 单边成交！尝试补单对冲...")
                        # 简单的自动补单尝试
                        fail_id = n_id if results[0] else y_id
                        fail_price = n_ask if results[0] else y_ask
                        await safe_order(client, fail_id, fail_price + 0.005, order_size)
                        send_tg("❗ 发生单边成交，已尝试溢价补单")

                await asyncio.sleep(0.3)

            # 轮询结束更新资产
            usdc, matic = get_balance(w3)
            await asyncio.sleep(20)

        except Exception as e:
            logger.error(f"💥 系统循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
