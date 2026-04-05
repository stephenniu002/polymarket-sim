import time
import requests
import logging

from trade import execute_trade
from strategy import generate_signal
from config import MARKETS

logging.basicConfig(level=logging.INFO)

BASE = "https://clob.polymarket.com"

# ===============================
# 控制
# ===============================
cooldown = {}
COOLDOWN_TIME = 30

trade_log = []
MAX_TRADES_PER_MIN = 3


# ===============================
def can_trade():
    now = time.time()

    while trade_log and now - trade_log[0] > 60:
        trade_log.pop(0)

    return len(trade_log) < MAX_TRADES_PER_MIN


def record_trade():
    trade_log.append(time.time())


# ===============================
def get_trades(token_id):
    try:
        url = f"{BASE}/trades?token_id={token_id}"
        res = requests.get(url, timeout=5)

        if res.status_code != 200:
            return []

        data = res.json()

        # 兼容结构
        if isinstance(data, dict):
            data = data.get("trades", [])

        if not isinstance(data, list):
            return []

        return data

    except Exception as e:
        logging.warning(f"⚠️ trades获取失败: {e}")
        return []


# ===============================
def main():
    logging.info("🚀 REST 实盘稳定版启动")

    while True:
        try:
            for symbol, m in MARKETS.items():

                now = time.time()

                # 冷却
                if symbol in cooldown and now - cooldown[symbol] < COOLDOWN_TIME:
                    continue

                token_id = m["YES"]

                trades = get_trades(token_id)

                if not trades:
                    continue

                last = trades[-1]

                try:
                    price = float(last.get("price", 0))
                except:
                    continue

                if price <= 0:
                    continue

                state = {
                    "trades": trades[-50:],
                    "last_price": price,
                    "last_token": token_id
                }

                signal = generate_signal(state)

                if not signal:
                    continue

                if not can_trade():
                    logging.warning("⛔ 频率限制")
                    continue

                logging.info(f"🎯 {symbol} | {signal} | {price}")

                execute_trade(
                    symbol,
                    m["YES"] if signal == "BUY" else m["NO"],
                    signal,
                    price,
                    0.3   # 小仓测试
                )

                cooldown[symbol] = now
                record_trade()

            time.sleep(2)

        except Exception as e:
            logging.error(f"❌ 主循环错误: {e}")
            time.sleep(3)


# ===============================
if __name__ == "__main__":
    main()
