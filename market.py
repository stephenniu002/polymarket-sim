import requests
import logging

BASE_GAMMA = "https://gamma-api.polymarket.com"
# 保持和你 JSON 一致的目标币种
TARGETS = ["BTC", "ETH", "SOL", "HYPE", "DOGE", "BNB", "Bitcoin", "Ethereum"]

def get_tokens():
    """提取目标 Token ID 及其对应的市场元数据，严格过滤价格盘"""
    result = []
    seen_conditions = set()

    try:
        # 实盘建议：直接搜索 "Price"，这样能过滤掉大部分非价格干扰项
        params = {
            "active": "true",
            "closed": "false",
            "search": "Price",
            "limit": 50
        }
        resp = requests.get(f"{BASE_GAMMA}/markets", params=params, timeout=10)
        if resp.status_code != 200:
            return []
        
        all_markets = resp.json()
        
        for m in all_markets:
            q_text = m.get("question", "")
            cond_id = m.get("conditionId")
            clob_ids = m.get("clobTokenIds", [])

            # 1. 基础过滤：必须有 conditionId 和 两个 TokenId
            if not cond_id or len(clob_ids) < 2:
                continue

            # 2. 关键词过滤：匹配你定义的 TARGETS
            is_target = any(t.lower() in q_text.lower() for t in TARGETS)
            if not is_target:
                continue

            # 3. 深度过滤：只保留价格涨跌盘，排除掉 GTA、世界杯、空投等
            # 价格盘通常包含 "above", "below", "price" 等词
            q_lower = q_text.lower()
            if not any(k in q_lower for k in ["above", "price", "hit"]):
                continue
            
            # 排除掉已知的干扰词
            if any(n in q_lower for n in ["gta", "airdrop", "fifa", "launch"]):
                continue

            if cond_id not in seen_conditions:
                # 构造和你展示的 JSON 一致的结构
                result.append({
                    "name": q_text,
                    "condition_id": cond_id,
                    "up_token": clob_ids[0],   # Yes / Up
                    "down_token": clob_ids[1], # No / Down
                    "volume": float(m.get("volume", 0))
                })
                seen_conditions.add(cond_id)
            
        # 按成交量排序，确保拿到的是该币种目前最火（最新）的盘口
        result.sort(key=lambda x: x['volume'], reverse=True)
        return result
    except Exception as e:
        logging.error(f"❌ 获取动态市场失败: {e}")
        return []

def get_market_map():
    """返回符合你要求的 JSON 映射格式"""
    tokens_data = get_tokens()
    mapping = {}
    
    # 定义标准 Symbol 映射，方便 main.py 索引
    symbols = ["BTC", "ETH", "SOL", "HYPE", "DOGE", "BNB"]
    
    for item in tokens_data:
        for s in symbols:
            # 只要标题里包含这个币种名，且 mapping 里还没存（因为我们排过序，第一个就是最热的）
            if s.lower() in item['name'].lower() and s not in mapping:
                mapping[s] = {
                    "conditionId": item['condition_id'],
                    "upTokenId": item['up_token'],
                    "downTokenId": item['down_token'],
                    "name": item['name']
                }
                break
    return mapping
    "conditionId": "0x3e04c9857b181113e1fe9f89cb809bcc587f8ff06502c5156f2529b7092eae84",
    "upTokenId": "88438400974108281071153782653753259556878826837492102662188120562364103801244",
    "downTokenId": "44276292184228714549958513042732610153778868935733901181917332805027190282661"
  }
}
