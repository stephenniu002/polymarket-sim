import requests

BASE = "https://clob.polymarket.com"
# 扩展了关键词，确保 5min 盘口能被搜到
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "BTC", "ETH", "SOL"]

def get_markets():
    try:
        return requests.get(f"{BASE}/markets", timeout=10).json()
    except:
        return []

def load_tokens():
    """方案 A 核心函数：提取所有目标 Token ID"""
    markets = get_markets()
    result = []

    for m in markets:
        if "tokens" not in m or "question" not in m:
            continue

        q_text = m["question"].lower()
        # 匹配币种关键词
        if any(t.lower() in q_text for t in TARGETS):
            yes_token = None
            for token in m.get("tokens", []):
                # 寻找 YES / UP 端的 Token ID
                outcome = token.get("outcome", "").lower()
                if outcome in ["yes", "up", "above"]:
                    yes_token = token.get("token_id")
            
            if yes_token:
                result.append({
                    "name": m["question"],
                    "token": yes_token
                })
    return result

def top_markets():
    """兼容层：返回纯 ID 列表供 main.py 快速过滤"""
    tokens_data = load_tokens()
    return [item["token"] for item in tokens_data]
