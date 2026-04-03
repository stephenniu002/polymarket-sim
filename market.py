import requests

BASE = "https://clob.polymarket.com"
# 目标监控关键词
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "BTC", "ETH", "SOL"]

def get_market(keyword=None):
    """获取市场列表，严格过滤非法数据类型"""
    try:
        resp = requests.get(f"{BASE}/markets", timeout=10)
        if resp.status_code != 200:
            return []
        
        markets = resp.json()
        
        # 确保 markets 是列表
        if not isinstance(markets, list):
            return []

        filtered = []
        for m in markets:
            # 只有当 m 是字典且包含 question 键时才处理
            if isinstance(m, dict) and "question" in m:
                q_text = str(m.get("question", "")).lower()
                if keyword:
                    if keyword.lower() in q_text:
                        filtered.append(m)
                else:
                    filtered.append(m)
        return filtered
    except Exception as e:
        print(f"❌ 获取市场异常: {e}")
        return []

def get_tokens():
    """补齐 main.py 需要的函数：提取所有目标 Token ID"""
    markets = get_market() # 调用上面的函数获取所有市场
    result = []
    
    for m in markets:
        # 过滤包含关键词的市场
        q_text = m.get("question", "").lower()
        if any(t.lower() in q_text for t in TARGETS):
            # 寻找 YES / UP 端的 Token ID
            for token in m.get("tokens", []):
                outcome = token.get("outcome", "").lower()
                if outcome in ["yes", "up", "above"]:
                    result.append({
                        "name": m["question"],
                        "token": token.get("token_id")
                    })
    return result

def top_markets():
    """补齐 main.py 需要的函数：返回纯 ID 列表"""
    tokens_data = get_tokens()
    return [item["token"] for item in tokens_data]
