import time
import requests
import logging

BASE = "https://clob.polymarket.com"

MARKETS = {
    "BTC": {"YES": "yes_id_btc", "NO": "no_id_btc"},
    "ETH": {"YES": "yes_id_eth", "NO": "no_id_eth"},
}

EDGE_THRESHOLD = 0.01

logging.basicConfig(level=logging.INFO)

# ===== 获取盘口 =====
def get_price(token_id):
    try:
        url = f"{BASE}/book?token_id={token_id}"
        res = requests.get(url, timeout=5).json()

        best_ask = float(res["asks"][0]["price"]) if res["asks"] else None
        best_bid = float(res["bids"][0]["price"]) if res["bids"] else None

        return best_ask, best_bid
    except:
        return None, None

# ===== Edge =====
def calc_edge(y, n):
    if not y or not n:
        return None
    total = y + n
    if total > 1.2 or total < 0.8:
        return None
    return 1 - total

# ===== 主循环 =====
while True:
    for m, t in MARKETS.items():
        y_ask, _ = get_price(t["YES"])
        n_ask, _ = get_price(t["NO"])

        edge = calc_edge(y_ask, n_ask)
        if edge is None:
            continue

        logging.info(f"{m} YES:{y_ask} NO:{n_ask} Edge:{edge:.2%}")

        if edge > EDGE_THRESHOLD:
            logging.info(f"🚀 套利触发 {m}")

    time.sleep(5)
