import os
import asyncio
import requests
import logging
import sys
import time
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ===== Web3 兼容 =====
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except:
    from web3.middleware import geth_poa_middleware

# ================= 配置 =================
RPC_URL = os.getenv("ALCHEMY_RPC_URL")
ORDER_SIZE = float(os.getenv("ORDER_SIZE", "1.0"))
MAX_POSITION = 10
REPORT_INTERVAL = 300  # 5分钟

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LOBSTER-MAX")

# ================= Telegram =================
def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=5
            )
        except:
            pass

# ================= Web3 =================
async def get_w3():
    while True:
        try:
            w3 = Web3(Web3.HTTPProvider(RPC_URL))
            if geth_poa_middleware:
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            w3.eth.get_block_number()
            logger.info("✅ RPC 已连接")
            return w3
        except Exception as e:
            logger.error(f"RPC错误: {e}")
            await asyncio.sleep(5)

# ================= 资产 =================
USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def get_balance(w3):
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        contract = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ABI)
        usdc = contract.functions.balanceOf(addr).call() / 1e6
        matic = w3.eth.get_balance(addr) / 1e18
        return usdc, matic
    except:
        return 0, 0

# ================= 市场 =================
BASE = "https://clob.polymarket.com"

def get_markets():
    try:
        r = requests.get(f"{BASE}/sampling-markets", timeout=10).json()
        return r if isinstance(r, list) else r.get("data", [])
    except:
        return []

def get_book(token_id):
    try:
        r = requests.get(f"{BASE}/book?token_id={token_id}", timeout=5).json()
        bids = r.get("bids", [])
        asks = r.get("asks", [])
        bid = float(bids[0]["price"]) if bids else 0
        ask = float(asks[0]["price"]) if asks else 1
        return bid, ask
    except:
        return 0, 1

# ================= 全局状态 =================
profit = 0
trade_count = 0
last_report = time.time()

# ================= 核心策略 =================
async def trade_logic(client, market):
    global profit, trade_count

    tokens = market.get("tokens", [])
    if len(tokens) < 2:
        return

    y = tokens[0]["token_id"]
    n = tokens[1]["token_id"]

    y_bid, y_ask = get_book(y)
    n_bid, n_ask = get_book(n)

    total = y_ask + n_ask

    logger.info(f"📈 {y_ask:.3f} + {n_ask:.3f} = {total:.3f}")

    # ================= 套利 =================
    if 0.2 < total < 0.97:
        logger.info("🔥 套利触发")

        size = ORDER_SIZE

        try:
            await asyncio.gather(
                asyncio.to_thread(client.post_order, {
                    "price": round(y_ask + 0.002, 3),
                    "size": size,
                    "side": "BUY",
                    "token_id": y
                }),
                asyncio.to_thread(client.post_order, {
                    "price": round(n_ask + 0.002, 3),
                    "size": size,
                    "side": "BUY",
                    "token_id": n
                })
            )

            p = (1 - total) * size
            profit += p
            trade_count += 1

            send_tg(f"💰 套利成功 +{p:.3f}")

        except Exception as e:
            logger.error(f"套利失败: {e}")

    # ================= 做市 =================
    spread = y_ask - y_bid

    if 0.01 < spread < 0.1:
        buy_price = round(y_bid + 0.001, 3)
        sell_price = round(y_ask - 0.001, 3)

        try:
            await asyncio.gather(
                asyncio.to_thread(client.post_order, {
                    "price": buy_price,
                    "size": ORDER_SIZE,
                    "side": "BUY",
                    "token_id": y,
                    "expiration": int(time.time()) + 60
                }),
                asyncio.to_thread(client.post_order, {
                    "price": sell_price,
                    "size": ORDER_SIZE,
                    "side": "SELL",
                    "token_id": y,
                    "expiration": int(time.time()) + 60
                })
            )
        except:
            pass

# ================= 主循环 =================
async def main():
    global last_report

    logger.info("🚀 Lobster Pro Max 启动")

    w3 = await get_w3()
    usdc, matic = get_balance(w3)

    client = ClobClient(host=BASE, key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            markets = get_markets()[:10]

            for m in markets:
                await trade_logic(client, m)
                await asyncio.sleep(0.5)

            usdc, matic = get_balance(w3)

            # ================= 电报汇报 =================
            if time.time() - last_report > REPORT_INTERVAL:
                msg = f"""
📊 Lobster 报告
💰 USDC: {usdc:.2f}
⛽ MATIC: {matic:.2f}
📈 交易次数: {trade_count}
💵 累计利润: {profit:.2f} USDC
"""
                send_tg(msg)
                last_report = time.time()

            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"循环异常: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
