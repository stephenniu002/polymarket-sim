import requests
import logging
from datetime import datetime, timezone

logger = logging.getLogger("LOBSTER-MARKET")
BASE_URL = "https://clob.polymarket.com"

# 你的 7 大猎物：只看 5 分钟价格预测
CRYPTO_KEYWORDS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "HYPE"]

def get_all_active_5min_markets():
    """实时侦察所有符合条件的 5 分钟加密盘口"""
    try:
        resp = requests.get(f"{BASE_URL}/markets", timeout=10)
        all_markets = resp.json()
        targets = []
        for m in all_markets:
            q = m.get("question", "")
            # 必须包含 5 min 关键词，且属于目标币种
            if ("5 min" in q.lower() or "5-minute" in q.lower()) and \
               any(k.lower() in q.lower() for k in CRYPTO_KEYWORDS):
                targets.append(m)
        return targets
    except Exception as e:
        logger.error(f"❌ 侦察失败: {e}")
        return []

def is_last_minute(market):
    """【策略核心】判断是否进入最后 60 秒的‘末日反转’窗口"""
    try:
        end_time_str = market.get("end_date_iso")
        if not end_time_str: return False
        
        # 将 ISO 字符串转为 UTC 时间进行对比
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
        seconds_left = (end_time - datetime.now(timezone.utc)).total_seconds()
        
        # 🟢 窗口期：距离结束 10s 到 65s 之间
        return 10 < seconds_left < 65
    except:
        return False

def top_markets():
    """【火控权限】只有进入最后 1 分钟，相关 Token 才会进入白名单"""
    active_markets = get_all_active_5min_markets()
    valid_ids = []
    for m in active_markets:
        if is_last_minute(m):
            # 将该市场的 YES 和 NO 全都加入可交易名单
            for t in m.get("tokens", []):
                valid_ids.append(t.get("token_id"))
    return valid_ids

def get_tokens(market):
    """提取涨(UP/YES)和跌(DOWN/NO)的 ID"""
    yes, no = None, None
    for t in market.get("tokens", []):
        out = t.get("outcome", "").lower()
        if out in ["up", "yes", "above"]: yes = t["token_id"]
        else: no = t["token_id"]
    return yes, no
