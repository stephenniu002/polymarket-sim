import time
import requests
import logging
from trade import execute_trade
from strategy import generate_signal
from config import MARKETS

logging.basicConfig(level=logging.INFO)

BASE = "https://clob.polymarket.com"

# ===============================
def get_trades(token_id):
    try:
        url = f"{BASE}/trades?token_id={token_id}"
        res = requests.get(url, timeout=5)
        return res.json()
    except:
        return []

# ===============================
def main():
    logging.info("🚀 REST 实盘模式启动")

    while True:
        try:
            for symbol, m in MARKETS.items():

                token_id = m["YES"]

                trades = get_trades(token_id)

                if not trades:
                    continue

                last = trades[-1]
                price = float(last.get("price", 0))

                state = {
                    "trades": trades[-50:],
                    "last_price": price,
                    "last_token": token_id
                }

                signal = generate_signal(state)

                if not signal:
                    continue

                logging.info(f"🎯 {symbol} | {signal} | {price}")

                execute_trade(
                    symbol,
                    m["YES"] if signal == "BUY" else m["NO"],
                    signal,
                    price,
                    0.5
                )

            time.sleep(2)

        except Exception as e:
            logging.error(f"❌ 错误: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
