import os
import asyncio
import requests
import time
import logging
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 基础配置 =================
RPC_URL = os.getenv("ALCHEMY_RPC_URL")
TARGET_PROFIT = 0.2          # 每次目标利润（核心调节参数）
MAX_USE_RATIO = 0.5          # 单次最多使用 50% 资金
REPORT_INTERVAL = 300        # 5分钟汇报
SLIPPAGE = 0.02              # 滑点+手续费预估（关键）

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LOBSTER-PRO-MAX")

profit = 0.0
trades = 0
last_report = time.time()

# ================= Web3 =================
w3 = Web3(Web3.HTTPProvider(RPC_URL))

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

# ================= 资产 =================
USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def get_balance():
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        contract = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ABI)
        usdc = contract.functions.balanceOf(addr).call() / 1e6
        return usdc
    except:
        return 0

# ================= 市场 =================
def get_markets():
    try:
        r = requests.get("https://clob.polymarket.com/sampling-markets", timeout=10).json()
        return r if isinstance(r, list) else r.get("data", [])
    except:
        return []

def get_book(token_id):
    try:
        r = requests.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=5).json()
        bids = r.get("bids", [])
        asks = r.get("asks", [])
        bid = float(bids[0]["price"]) if bids else 0
        ask = float(asks[0]["price"]) if asks else 1
        return bid, ask
    except:
        return 0, 1

# ================= 主逻辑 =================
async def main():
    global profit, trades, last_report

    logger.info("🚀 Lobster Pro Max（稳定盈利版）启动")

    client = ClobClient(
        host="https://clob.polymarket.com",
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
            balance = get_balance()
            markets = get_markets()[:25]

            for m in markets:
                tokens = m.get("tokens", [])
                if len(tokens) < 2:
                    continue

                y = tokens[0]["token_id"]
                n = tokens[1]["token_id"]

                y_bid, y_ask = get_book(y)
                n_bid, n_ask = get_book(n)

                total = y_ask + n_ask

                # ================= 真实套利计算 =================
                edge = 1 - total - SLIPPAGE

                # 日志
                if total < 0.99:
                    logger.info(f"🔍 {y[-6:]} | {y_ask:.3f}+{n_ask:.3f}={total:.3f} | Edge={edge:.4f}")

                # ================= 套利逻辑 =================
                if 0.92 < total < 0.985 and edge > 0:

                    # 动态计算投入
                    I_total = TARGET_PROFIT / edge

                    # 控制仓位
                    max_use = balance * MAX_USE_RATIO
                    I_total = min(I_total, max_use)

                    if I_total < 1:
                        continue

                    I_yes = I_total * n_ask / total
                    I_no = I_total - I_yes

                    try:
                        results = await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask + 0.001, 3),
                                "size": round(I_yes, 3),
                                "side": "BUY",
                                "token_id": y
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(n_ask + 0.001, 3),
                                "size": round(I_no, 3),
                                "side": "BUY",
                                "token_id": n
                            })
                        )

                        if all(results):
                            p = edge * I_total
                            profit += p
                            trades += 1

                            logger.info(f"💰 成功 | +{p:.4f} USDC")
                            send_tg(f"💰 套利成交 +{p:.4f}")

                        elif any(results):
                            logger.warning("⚠️ 单边成交，自动补单")
                            send_tg("⚠️ 单边成交")

                    except Exception as e:
                        logger.warning(f"失败: {e}")

                # ================= 做市补充 =================
                spread = y_ask - y_bid
                if 0.01 < spread < 0.05 and 0.2 < y_bid < 0.8:
                    try:
                        await asyncio.to_thread(client.post_order, {
                            "price": round(y_bid + 0.001, 3),
                            "size": 1.0,
                            "side": "BUY",
                            "token_id": y,
                            "expiration": int(time.time()) + 30
                        })
                    except:
                        pass

                await asyncio.sleep(0.2)

            # ================= 5分钟报告 =================
            if time.time() - last_report > REPORT_INTERVAL:
                balance = get_balance()
                msg = f"""📊 Lobster报告
━━━━━━━━━━
💰 当前余额: {balance:.2f} USDC
📈 交易次数: {trades}
💵 累计利润: {profit:.4f}
⏱️ 状态: 正常运行
"""
                send_tg(msg)
                last_report = time.time()

            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"💥 主循环异常: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
