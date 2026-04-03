import requests

BASE = "https://clob.polymarket.com"

def get_market(keyword=None):
    """获取市场列表，严格过滤非法数据类型"""
    try:
        resp = requests.get(f"{BASE}/markets", timeout=10)
        # 如果返回不是 200，或者不是 JSON，直接返回空
        if resp.status_code != 200:
            return []
        
        markets = resp.json()
        
        # 核心修复：确保 markets 是列表
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
