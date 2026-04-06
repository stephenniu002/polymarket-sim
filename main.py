import os
import time
import asyncio
import requests
import logging
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 配置 =================
RPC_URL = os.getenv("ALCHEMY_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ADDRESS = os.getenv("POLY_ADDRESS")

API_KEY = os.getenv("POLY_API_KEY")
API_SECRET = os.getenv("POLY_SECRET")
API_PASS = os.getenv("POLY_PASSPHRASE")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

TARGET_PROFIT = 1.0
MIN_EDGE = 0.01
PRE_EDGE = 0.005

ORDER_SIZE = 2
MAX_POS = 20

REPORT_INTERVAL = 300

profit = 0
trades = 0
last_report = time.time()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LOBSTER")

# ================= 工具 =================
def send_tg(msg):
    if not TG_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg}
        )
    except:
        pass

def get_book(token):
    try:
        r = requests.get(f"https://clob.polymarket.com/book?token_id={token}", timeout=3).json()
        bid = float(r["bids"][0]["price"]) if r["bids"] else 0
        ask = float(r["asks"][0]["price"]) if r["asks"] else 1
        return bid, ask
    except:
        return 0, 1

def get_markets():
    try:
        r = requests.get("https://clob.polymarket.com/sampling-markets", timeout=5).json()
        return r if isinstance(r, list) else r.get("data", [])
    except:
        return []

def calc_orders(p_yes, p_no):
    edge = 1 - (p_yes + p_no)
    if edge <= 0:
        return None

    total = TARGET_PROFIT / edge
    total = min(total, MAX_POS)

    yes_amt = total * p_no / (p_yes + p_no)
    no_amt = total - yes_amt

    return yes_amt, no_amt, edge

# ================= 主逻辑 =================
async def trade_logic(client):
    global profit, trades, ORDER_SIZE, last_report

    markets = get_markets()[:30]

    for m in markets:
        tokens = m.get("tokens", [])
        if len(tokens) < 2:
            continue

        y = tokens[0]["token_id"]
        n = tokens[1]["token_id"]

        y_bid, y_ask = get_book(y)
        n_bid, n_ask = get_book(n)

        total = y_ask + n_ask
        edge = 1 - total

        log.info(f"📈 {y_ask:.3f}+{n_ask:.3f}={total:.3f} edge={edge:.4f}")

        # ================= 套利 =================
        if edge > MIN_EDGE:
            res = calc_orders(y_ask, n_ask)
            if res:
                yes_amt, no_amt, edge = res

                log.info(f"🔥 套利执行 edge={edge:.4f}")

                await asyncio.gather(
                    asyncio.to_thread(client.post_order, {
                        "price": y_ask,
                        "size": round(yes_amt, 2),
                        "side": "BUY",
                        "token_id": y
                    }),
                    asyncio.to_thread(client.post_order, {
                        "price": n_ask,
                        "size": round(no_amt, 2),
                        "side": "BUY",
                        "token_id": n
                    })
                )

                profit += TARGET_PROFIT
                trades += 1

        # ================= 提前布局 =================
        elif PRE_EDGE < edge <= MIN_EDGE:
            log.info("🟡 提前布局")

            await asyncio.to_thread(client.post_order, {
                "price": y_ask,
                "size": ORDER_SIZE,
                "side": "BUY",
                "token_id": y
            })

            await asyncio.to_thread(client.post_order, {
                "price": n_ask,
                "size": ORDER_SIZE,
                "side": "BUY",
                "token_id": n
            })

        # ================= 单边反手 =================
        elif y_ask > 0.85:
            log.info("🔴 单边 → 买 NO")

            await asyncio.to_thread(client.post_order, {
                "price": n_ask,
                "size": ORDER_SIZE,
                "side": "BUY",
                "token_id": n
            })

        elif y_ask < 0.15:
            log.info("🟢 单边 → 买 YES")

            await asyncio.to_thread(client.post_order, {
                "price": y_ask,
                "size": ORDER_SIZE,
                "side": "BUY",
                "token_id": y
            })

        # ================= 强制成交 =================
        else:
            if 0.3 < y_ask < 0.7:
                log.info("⚖️ 强制成交")

                await asyncio.to_thread(client.post_order, {
                    "price": y_ask,
                    "size": ORDER_SIZE,
                    "side": "BUY",
                    "token_id": y
                })

        await asyncio.sleep(0.3)

    # ================= 盈利复投 =================
    if profit > 5:
        ORDER_SIZE = min(ORDER_SIZE + 0.5, 5)

    # ================= Telegram 汇报 =================
    if time.time() - last_report > REPORT_INTERVAL:
        msg = f"""
📊 Lobster 报告
━━━━━━━━━━
📈 交易次数: {trades}
💰 利润: {profit:.2f} USDC
📦 仓位: {ORDER_SIZE}
"""
        send_tg(msg)
        last_report = time.time()

# ================= 主入口 =================
async def main():
    log.info("🚀 Lobster Pro 启动")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    log.info("✅ RPC连接成功")

    client = ClobClient(
        host="https://clob.polymarket.com",
        key=PRIVATE_KEY,
        chain_id=137
    )

    client.set_api_creds(ApiCreds(
        api_key=API_KEY,
        api_secret=API_SECRET,
        api_passphrase=API_PASS
    ))

    while True:
        try:
            await trade_logic(client)
            await asyncio.sleep(5)
        except Exception as e:
            log.error(f"❌ 错误: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
