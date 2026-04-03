import requests

BASE = "https://clob.polymarket.com"
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "BTC", "ETH", "SOL"]

def get_market(keyword=None):
    """获取市场并支持关键词过滤，增加了类型检查防止报错"""
    try:
        resp = requests.get(f"{BASE}/markets", timeout=10)
        markets = resp.json()
        
        # 核心修复：确保 markets 是列表，且只处理其中的字典对象
        if not isinstance(markets, list):
            return []

        if keyword:
            filtered = []
            for m in markets:
                # 只有当 m 是字典时才调用 .get()
                if isinstance(m, dict):
                    question = str(m.get("question", "")).lower()
                    if keyword.lower() in question:
                        filtered.append(m)
            return filtered
            
        return markets
    except Exception as e:
        # 这里打印具体的错误类型，方便后续调试
        print(f"❌ 获取市场异常: {e}")
        return []

# get_tokens 和 top_markets 保持不变...
