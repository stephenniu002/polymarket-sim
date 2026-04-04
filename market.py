import requests

# 建议使用 Gamma API 获取更完整的市场信息（包括 Condition ID）
BASE_GAMMA = "https://gamma-api.polymarket.com"
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin", "BTC", "ETH", "SOL"]

def get_market(keyword=None):
    """获取活跃市场列表，严格过滤"""
    try:
        # 实盘建议增加 active=true 过滤掉已结束的市场
        url = f"{BASE_GAMMA}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "limit": 100
        }
        if keyword:
            params["search"] = keyword

        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []
        
        markets = resp.json()
        if not isinstance(markets, list):
            return []

        filtered = []
        for m in markets:
            if isinstance(m, dict) and "question" in m:
                q_text = str(m.get("question", "")).lower()
                # 排除没有 Token ID 的观察类市场
                if not m.get("clobTokenIds"):
                    continue
                
                # 如果传入了 keyword，做二次校验
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
    """提取目标 Token ID 及其对应的市场元数据"""
    all_markets = get_market()
    result = []
    
    # 记录已处理的 conditionId 避免重复
    seen_conditions = set()

    for m in all_markets:
        q_text = m.get("question", "").lower()
        cond_id = m.get("conditionId")

        # 1. 匹配关键词 2. 确保 conditionId 唯一 3. 确保有交易 Token
        if any(t.lower() in q_text for t in TARGETS) and cond_id not in seen_conditions:
            
            clob_ids = m.get("clobTokenIds", [])
            if len(clob_ids) < 2:
                continue

            # 提取 UP/YES Token (通常是索引 0) 和 DOWN/NO Token (通常是索引 1)
            # 在 Polymarket 价格盘中：0 -> Up/Yes, 1 -> Down/No
            result.append({
                "name": m["question"],
                "condition_id": cond_id,
                "up_token": clob_ids[0],
                "down_token": clob_ids[1],
                "volume": float(m.get("volume", 0))
            })
            seen_conditions.add(cond_id)
            
    # 按成交量排序，确保最热的市场排在前面
    result.sort(key=lambda x: x['volume'], reverse=True)
    return result

def top_markets():
    """返回纯 Up/Yes Token ID 列表供监控"""
    tokens_data = get_tokens()
    # 只返回 UP 端的 Token ID
    return [item["up_token"] for item in tokens_data]

def get_market_map():
    """实盘推荐：返回以 Symbol 为 Key 的字典，方便 strategy.py 调用"""
    tokens_data = get_tokens()
    mapping = {}
    for item in tokens_data:
        # 简单提取名字，例如 "Will Bitcoin be above..." 提取出 BTC
        for t in TARGETS:
            if t.lower() in item['name'].lower():
                mapping[t.upper()] = item
                break
    return mapping
