import requests

BASE = "https://clob.polymarket.com"
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "BTC", "ETH", "SOL"]

# 修改 1: 将 get_markets 改为 get_market (或者保留两者)
def get_market(): 
    try:
        # 注意：CLOB API 的 /markets 接口返回数据量很大，建议确认接口路径正确
        response = requests.get(f"{BASE}/markets", timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

# 修改 2: 将 load_tokens 改为 get_tokens
def get_tokens():
    """提取所有目标 Token ID"""
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
                result.append({
                    "name": m["question"],
                    "token": yes_token
                })
    return result

# 保持不变
def top_markets():
    """返回纯 ID 列表"""
    tokens_data = get_tokens() # 注意这里同步改为调用 get_tokens
    return [item["token"] for item in tokens_data]
