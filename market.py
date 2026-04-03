import requests

BASE = "https://clob.polymarket.com"
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "BTC", "ETH", "SOL"]

def get_market(keyword=None):
    """获取市场列表，支持按关键词过滤"""
    try:
        # 获取所有活跃市场
        resp = requests.get(f"{BASE}/markets", timeout=10)
        markets = resp.json()
        if keyword:
            # 如果 main.py 传了 "Trump"，这里进行过滤
            return [m for m in markets if keyword.lower() in str(m.get("question", "")).lower()]
        return markets
    except Exception as e:
        print(f"❌ 获取市场失败: {e}")
        return []

def get_tokens():
    """方案 A 核心函数：提取目标 Token ID"""
    markets = get_market()
    result = []
    for m in markets:
        if not isinstance(m, dict) or "tokens" not in m or "question" not in m:
            continue

        q_text = m["question"].lower()
        if any(t.lower() in q_text for t in TARGETS):
            yes_token = None
            for token in m.get("tokens", []):
                outcome = token.get("outcome", "").lower()
                if outcome in ["yes", "up", "above"]:
                    yes_token = token.get("token_id")
            
            if yes_token:
                result.append({"name": m["question"], "token": yes_token})
    return result

def top_markets():
    """返回纯 ID 列表供快速过滤"""
    tokens_data = get_tokens()
    return [item["token"] for item in tokens_data]
