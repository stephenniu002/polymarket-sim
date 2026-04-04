import requests
import logging

def get_latest_market(asset="Bitcoin"):
    """直接从 Polymarket 抓取当前最新的盘口 ID"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "search": f"{asset} Price",
        "limit": 5
    }
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        # 寻找包含 'above' 的主价格盘
        valid = [m for m in resp if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
        if valid:
            # 选成交量最高的盘口
            m = max(valid, key=lambda x: float(x.get("volume", 0)))
            return {
                "question": m.get("question"),
                "token_id": m.get("clobTokenIds")[0] # Yes Token
            }
    except Exception as e:
        logging.error(f"📡 扫描 {asset} 盘口失败: {e}")
    return None
