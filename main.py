import os
import time
import requests
import logging

logging.basicConfig(level=logging.INFO)

BASE = "https://clob.polymarket.com"

POLY_ADDRESS = os.getenv("POLY_ADDRESS")
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")

# ===============================
# 获取市场
# ===============================
def get_markets():
    try:
        url = f"{BASE}/markets"
        res = requests.get(url, timeout=10)
        return res.json()
    except Exception as e:
        logging.error(f"❌ 获取市场失败: {e}")
        return []

# ===============================
# 筛选 BTC / ETH
# ===============================
def filter_markets(markets):
    result = []

    for m in markets:
        q = m.get("question", "").upper()

        if "BTC" in q or "BITCOIN" in q or "ETH" in q or "ETHEREUM" in q:
            if m.get("active") is True:
                result.append(m)

    return result

# ===============================
# 选择最强市场（按流动性）
# ===============================
def pick_best_market(markets):
    if not markets:
        return None

    # 按成交量排序（fallback 用 liquidity）
    markets.sort(
        key=lambda x: x.get("volume", 0) or x.get("liquidity", 0),
        reverse=True
    )

    return markets[0]

# ===============================
# 获取 Token
# ===============================
def extract_tokens(market):
    try:
        tokens = market.get("tokens", [])

        if len(tokens) < 2:
            return None, None

        yes_token = tokens[0]["token_id"]
        no_token = tokens[1]["token_id"]

        return yes_token, no_token

    except:
        return None, None

# ===============================
# 获取成交数据（判断信号）
# ===============================
def get_trades(token_id):
    try:
        url = f"{BASE}/trades?token_id={token_id}"
        res = requests.get(url, timeout=5)
        return res.json()
    except:
        return []

# ===============================
# 简单信号（尾部动量）
# ===============================
def generate_signal(trades):
    if not trades:
        return None

    recent = trades[-10:]

    buy = sum(1 for t in recent if t.get("side") == "buy")
    sell = sum(1 for t in recent if t.get("side") == "sell")

    if buy > sell * 1.5:
        return "BUY"

    if sell > buy * 1.5:
