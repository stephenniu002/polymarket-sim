import requests
import logging

logger = logging.getLogger("LOBSTER-CRYPTO")
BASE_URL = "https://clob.polymarket.com"

# 你的 7 大猎物清单
CRYPTO_TARGETS = [
    "Bitcoin Price", 
    "Ethereum Price", 
    "Solana Price", 
    "XRP Price", 
    "BNB Price", 
    "Dogecoin Price", 
    "HYPE Price"
]

def get_all_active_5min_markets():
    """
    侦察兵：一次性把所有 5 分钟涨跌的市场全抓出来
    """
    try:
        resp = requests.get(f"{BASE_URL}/markets", timeout=10)
        all_markets = resp.json()
        
        # 只要带 "5 Minutes" 且在我们清单里的
        targets = []
        for m in all_markets:
            q = m.get("question", "")
            # 匹配 5分钟 逻辑
            if "5 min" in q.lower() or "5-minute" in q.lower():
                # 检查是否是我们关注的币种
                if any(name.lower() in q.lower() for name in CRYPTO_TARGETS):
                    targets.append(m)
        return targets
    except Exception as e:
        logger.error(f"❌ 侦察加密市场失败: {e}")
        return []

def top_markets():
    """
    【火控开关】只允许在这 7 个 5分钟 市场里开火
    """
    markets = get_all_active_5min_markets()
    ids = []
    for m in markets:
        for t in m.get("tokens", []):
            ids.append(t.get("token_id"))
    return ids

def get_tokens(market):
    """提取涨(YES)和跌(NO)的 ID"""
    yes, no = None, None
    for t in market.get("tokens", []):
        if t["outcome"].lower() == "up" or t["outcome"].lower() == "yes":
            yes = t["token_id"]
        else:
            no = t["token_id"]
    return yes, no
