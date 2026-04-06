import time
import requests
import logging

logging.basicConfig(level=logging.INFO)

BASE = "https://clob.polymarket.com"

# ===== 示例市场（换成真实 token_id）=====
MARKETS = {
    "BTC": {"YES": "yes_id_btc", "NO": "no_id_btc"},
    "ETH": {"YES": "yes_id_eth", "NO": "no_id_eth"},
}

EDGE_THRESHOLD = 0.01

# ===== 获取盘口 =====
def get_price(token_id):
    try:
        url = f"{BASE}/book?token_id={token_id}"
        res = requests.get(url, timeout=5).json()

        ask = float(res["asks"][0]["price"]) if res["asks"] else None
        bid = float(res["bids"][0]["price"]) if res["bids"] else None

        return ask, bid
    except Exception as e:
        logging.warning(f"获取价格失败: {e}")
        return None, None

# ===== Edge =====
def calc_edge(y, n):
    if not y or not n:
        return None
    
    total = y + n
    
    # 防止你之前那个 -100% bug
    if total > 1.2 or total < 0.8:
        return None

    return 1 - total

# ===== 主循环 =====
def main():
    logging.info("🚀 程序启动成功（稳定版）")

    while True:
        try:
            for m, t in MARKETS.items():
                y_ask, _ = get_price(t["YES"])
                n_ask, _ = get_price(t["NO"])

                edge = calc_edge(y_ask, n_ask)

                if edge is None:
                    continue

                logging.info(
                    f"🔍 {m} YES:{y_ask:.3f} NO:{n_ask:.3f} Edge:{edge:.2%}"
                )

                if edge > EDGE_THRESHOLD:
                    logging.info(f"💰 套利触发 {m}")

            time.sleep(5)

        except Exception as e:
            logging.error(f"❌ 主循环错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
