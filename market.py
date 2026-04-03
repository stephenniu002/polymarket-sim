import requests
import logging
from datetime import datetime, timezone

logger = logging.getLogger("LOBSTER-CRYPTO")
BASE_URL = "https://clob.polymarket.com"

# 你的 7 大猎物核心关键词
CRYPTO_KEYWORDS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "HYPE"]

def get_all_active_5min_markets():
    """
    全频段扫描：只抓取‘5-minute’且属于你的 7 大币种的市场
    """
    try:
        resp = requests.get(f"{BASE_URL}/markets", timeout=10)
        all_markets = resp.json()
        
        targets = []
        for m in all_markets:
            q = m.get("question", "")
            # 必须包含 5分钟 且在关键词清单里
            if ("5 min" in q.lower() or "5-minute" in q.lower()) and \
               any(k.lower() in q.lower() for k in CRYPTO_KEYWORDS):
                targets.append(m)
        return targets
    except Exception as e:
        logger.error(f"❌ 扫描加密市场失败: {e}")
        return []

def is_last_minute(market):
    """
    【策略核心】判断是否进入最后一分钟反转窗口
    Polymarket 的 5min 盘通常在整 5 分钟（如 12:05, 12:10）结算
    """
    try:
        # 获取市场结束时间 (通常是 ISO 格式)
        end_time_str = market.get("end_date_iso")
        if not end_time_str:
            return False
        
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        
        # 计算距离结束还有多少秒
        seconds_left = (end_time - now).total_seconds()
        
        # 🟢 最后一分钟反转窗口：剩余 10s 到 65s 之间
        # 留 10s 缓冲是为了防止签名和网络延迟导致下单失败
        return 10 < seconds_left < 65
    except:
        return False

def top_markets():
    """
    【火控开关】动态白名单
    只有处于‘最后一分钟’且符合币种的市场，token_id 才会进入白名单
    """
    active_markets = get_all_active_5min_markets()
    valid_ids = []
    
    for m in active_markets:
        if is_last_minute(m):
            for t in m.get("tokens", []):
                valid_ids.append(t.get("token_id"))
                
    return valid_ids

def get_tokens(market):
    """提取 涨(UP/YES) 和 跌(DOWN/NO) 的 ID"""
    yes, no = None, None
    for t in market.get("tokens", []):
        outcome = t.get("outcome", "").lower()
        if outcome in ["up", "yes", "above"]:
            yes = t["token_id"]
        else:
            no = t["token_id"]
    return yes, no
