import requests
import logging
from datetime import datetime, timezone

logger = logging.getLogger("LOBSTER-MARKET")
BASE_URL = "https://clob.polymarket.com"

# 7 大猎物关键词
CRYPTO_KEYWORDS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "HYPE"]

def get_all_active_5min_markets():
    """侦察所有活跃的 5min 加密盘口"""
    try:
        resp = requests.get(f"{BASE_URL}/markets", timeout=10)
        all_markets = resp.json()
        targets = []
        for m in all_markets:
            q = m.get("question", "")
            if ("5 min" in q.lower() or "5-minute" in q.lower()) and \
               any(k.lower() in q.lower() for k in CRYPTO_KEYWORDS):
                targets.append(m)
        return targets
    except Exception as e:
        logger.error(f"❌ 侦察失败: {e}")
        return []

def is_last_minute(market):
    """判断是否进入最后一分钟反转窗口"""
    try:
        end_time_str = market.get("end_date_iso")
        if not end_time_str: return False
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
        seconds_left = (end_time - datetime.now(timezone.utc)).total_seconds()
        return 10 < seconds_left < 65
    except:
        return False

def top_markets():
    """火控权限白名单"""
    active_markets = get_all_active_5min_markets()
    return [t.get("token_id") for m in active_markets if is_last_minute(m) for t in m.get("tokens", [])]

def get_tokens(market):
    """提取涨跌 ID"""
    yes, no = None, None
    for t in market.get("tokens", []):
        out = t.get("outcome", "").lower()
        if out in ["up", "yes", "above"]: yes = t["token_id"]
        else: no = t["token_id"]
    return yes, no
