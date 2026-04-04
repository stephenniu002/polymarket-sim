import requests
import logging

def get_active_market_ids(asset_name="Bitcoin"):
    """
    从 Gamma API 动态获取该资产最新的盘口数据
    asset_name: 'Bitcoin', 'Ethereum', 'Solana' 等
    """
    url = "https://gamma-api.polymarket.com/markets"
    # 搜索包含资产名 + Price 的价格预测盘，且处于活跃状态
    params = {
        "active": "true",
        "closed": "false",
        "search": f"{asset_name} Price",
        "limit": 10
    }
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        # 过滤出包含 'above' 的价格预测盘 (排除世界杯等杂项)
        valid_markets = [m for m in resp if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
        
        if valid_markets:
            # 取成交量最大的那个盘口
            m = max(valid_markets, key=lambda x: float(x.get("volume", 0)))
            return {
                "question": m.get("question"),
                "up_id": m.get("clobTokenIds")[0],   # Yes Token (看涨)
                "down_id": m.get("clobTokenIds")[1], # No Token (看跌)
                "condition_id": m.get("conditionId"),
                "volume": m.get("volume")
            }
    except Exception as e:
        logging.error(f"📡 抓取 {asset_name} 盘口失败: {e}")
    return None
