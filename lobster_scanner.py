import requests
import logging

def get_live_market(asset="Bitcoin"):
    """实时从 Gamma API 抓取最新的盘口，不再使用本地 markets.json"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "search": f"{asset} Price",
        "limit": 5
    }
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        # 过滤出包含 'above' 的核心盘口，确保是看涨/看跌盘
        valid = [m for m in resp if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
        if valid:
            # 选成交量最大的那个最新盘口
            m = max(valid, key=lambda x: float(x.get("volume", 0)))
            return {
                "question": m.get("question"),
                "up_id": m.get("clobTokenIds")[0],   # Yes (看涨)
                "down_id": m.get("clobTokenIds")[1], # No (看跌)
                "condition_id": m.get("conditionId")
            }
    except Exception as e:
        logging.error(f"📡 扫描 {asset} 盘口失败: {e}")
    return None
