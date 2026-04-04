import requests
import logging

BASE_GAMMA = "https://gamma-api.polymarket.com"
# 定义你想监控的资产关键字
ASSETS = ["Bitcoin", "Ethereum", "Solana", "HYPE", "Dogecoin", "BNB"]

def fetch_active_markets():
    """实时抓取最新的价格预测盘口 ID"""
    active_map = {}
    try:
        # 搜索包含 "Price" 且处于活跃状态的市场
        params = {"active": "true", "closed": "false", "search": "Price", "limit": 100}
        resp = requests.get(f"{BASE_GAMMA}/markets", params=params, timeout=10)
        markets = resp.json()

        for m in markets:
            q_text = m.get("question", "")
            c_id = m.get("conditionId")
            clob_ids = m.get("clobTokenIds", [])

            if not c_id or len(clob_ids) < 2: continue

            # 匹配资产并确认为价格盘 (排除掉干扰项)
            for asset in ASSETS:
                if asset.lower() in q_text.lower() and "above" in q_text.lower():
                    # 我们只取成交量最大的那个作为当前主力盘
                    symbol = asset.upper() if asset != "Bitcoin" else "BTC"
                    if symbol == "ETHEREUM": symbol = "ETH"
                    if symbol == "DOGECOIN": symbol = "DOGE"

                    if symbol not in active_map or float(m.get("volume", 0)) > active_map[symbol]['volume']:
                        active_map[symbol] = {
                            "name": q_text,
                            "conditionId": c_id,
                            "UP": clob_ids[0],   # Yes
                            "DOWN": clob_ids[1], # No
                            "volume": float(m.get("volume", 0))
                        }
        return active_map
    except Exception as e:
        logging.error(f"📡 动态市场扫描失败: {e}")
        return {}
