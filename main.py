import os
import asyncio
import requests
import logging
import sys
import time
from datetime import datetime
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ===== Web3 兼容 =====
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except:
    try:
        from web3.middleware import geth_poa_middleware
    except:
        geth_poa_middleware = None

# ================= 配置 =================
RPC_URL = os.getenv("ALCHEMY_RPC_URL")
ORDER_SIZE = float(os.getenv("ORDER_SIZE", "1"))
SPREAD_MIN = 0.01
REPORT_INTERVAL = 300  # 5分钟

logger = logging.getLogger("LOBSTER-PRO")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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
                try:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                except:
                    pass
            w3.eth.get_block_number()
            logger.info("✅ RPC连接成功")
            return w3
        except Exception as e:
            logger.error(f"❌ RPC失败: {e}")
            await asyncio.sleep(10)

# ================= 余额 =================
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def get_balance(w3):
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E), abi=ABI)
        matic = w3.eth.get_balance(addr) / 1e18
        usdc = contract.functions.balanceOf(addr).call() / 1e6
        return usdc, matic
    except:
        return 0, 0

# ================= 市场 =================
BASE = "https://clob.polymarket.com"

def get_markets():
    try:
        r = requests.get(f"{BASE}/sampling-markets", timeout=10).json()
        data = r if isinstance(r, list) else r.get("data", [])
        return data[:5]
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

# ================= 全局统计 =================
stats = {
    "orders": 0,
    "fills": 0,
    "start_balance": 0,
    "last_report": time.time()
}

# ================= 做市逻辑 =================
async def process_market(client, market):
    tokens = market.get("tokens", [])
    if len(tokens) < 2:
        return

    token = tokens[0]["token_id"]

    bid, ask = get_book(token)
    if bid == 0 or ask == 1:
        return

    mid = (bid + ask) / 2

    # 风控：趋势过滤
    if mid > 0.85 or mid < 0.15:
        return

    my_bid = round(bid + 0.001, 3)
    my_ask = round(ask - 0.001, 3)

    spread = my_ask - my_bid

    if spread < SPREAD_MIN:
        return

    logger.info(f"⚖️ {token[-6:]} 买:{my_bid} 卖:{my_ask} 差:{spread:.3f}")

    try:
        await asyncio.gather(
            asyncio.to_thread(client.post_order, {
                "price": my_bid,
                "size": ORDER_SIZE,
                "side": "BUY",
                "token_id": token,
                "expiration": int(time.time() + 60)
            }),
            asyncio.to_thread(client.post_order, {
                "price": my_ask,
                "size": ORDER_SIZE,
                "side": "SELL",
                "token_id": token,
                "expiration": int(time.time() + 60)
            })
        )
        stats["orders"] += 2
    except:
        pass

# ================= 电报汇报 =================
async def report_loop(w3):
    while True:
        await asyncio.sleep(REPORT_INTERVAL)

        usdc, matic = get_balance(w3)
        profit = usdc - stats["start_balance"]

        msg = f"""🦞 运行报告
时间: {datetime.now().strftime('%H:%M:%S')}

💰 USDC: {usdc:.2f}
⛽ MATIC: {matic:.2f}

📊 今日收益: {profit:.2f}
📈 下单次数: {stats["orders"]}
"""

        send_tg(msg)
        logger.info("📤 已发送电报报告")

# ================= 主程序 =================
async def main():
    logger.info("🚀 Lobster-MM Pro 启动")

    w3 = await get_w3()
    usdc, matic = get_balance(w3)

    stats["start_balance"] = usdc

    send_tg(f"🟢 机器人启动\n余额: {usdc:.2f} USDC")

    client = ClobClient(host=BASE, key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    # 启动电报线程
    asyncio.create_task(report_loop(w3))

    while True:
        try:
            markets = get_markets()

            for m in markets:
                await process_market(client, m)
                await asyncio.sleep(1)

            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"💥 主循环异常: {e}")
            await asyncio.sleep(5)

# ================= 启动 =================
if __name__ == "__main__":
    asyncio.run(main())

