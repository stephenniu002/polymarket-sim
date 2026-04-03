import requests
from datetime import datetime, timezone

BASE_URL = "https://clob.polymarket.com"
CRYPTO_KEYWORDS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "HYPE"]

def get_all_active_5min_markets():
    try:
        resp = requests.get(f"{BASE_URL}/markets", timeout=10)
        all_markets = resp.json()
        return [m for m in all_markets if ("5 min" in m.get("question", "").lower()) and \
                any(k.lower() in m.get("question", "").lower() for k in CRYPTO_KEYWORDS)]
    except:
        return []

def is_last_minute(market):
    try:
        end_time = datetime.fromisoformat(market.get("end_date_iso").replace("Z", "+00:00"))
        seconds_left = (end_time - datetime.now(timezone.utc)).total_seconds()
        return 10 < seconds_left < 65
    except:
        return False

def top_markets():
    """这是给 main.py 用的白名单函数"""
    markets = get_all_active_5min_markets()
    ids = []
    for m in markets:
        if is_last_minute(m):
            ids.extend([t.get("token_id") for t in m.get("tokens", [])])
    return ids

def get_tokens(market):
    """这是给 main.py 用的 Token 提取函数"""
    yes, no = None, None
    for t in market.get("tokens", []):
        if t.get("outcome", "").lower() in ["up", "yes", "above"]: yes = t["token_id"]
        else: no = t["token_id"]
    return yes, no
