import requests
import logging

# 基础配置
BASE_GAMMA = "https://gamma-api.polymarket.com"
# 目标币种清单
SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "HYPE", "DOGE", "BNB"]

def fetch_latest_market_map():
    """
    抓取最新的 7 路币种双向 Token ID。
    返回结构: { 'BTC': { 'upTokenId': '...', 'downTokenId': '...', 'name': '...' } }
    """
    mapping = {}
    
    # --- 备选/参考库：你提供的固定 Token ID (用于匹配或备份) ---
    # 下单核心参数：clobTokenIds[0] 是 Up，clobTokenIds[1] 是 Down
    try:
        params = {
            "active": "true",
            "closed": "false",
            "search": "Price",
            "limit": 50
        }
        resp = requests.get(f"{BASE_GAMMA}/markets", params=params, timeout=10)
        
        if resp.status_code == 200:
            all_markets = resp.json()
            # 过滤并按成交量排序
            valid_markets = [m for m in all_markets if m.get("clobTokenIds") and len(m["clobTokenIds"]) >= 2]
            valid_markets.sort(key=lambda x: float(x.get("volume", 0)), reverse=True)

            for s in SYMBOLS:
                for m in valid_markets:
                    q_lower = m.get("question", "").lower()
                    # 精准匹配币种和价格特征词
                    if s.lower() in q_lower and any(k in q_lower for k in ["above", "below", "price"]):
                        # 排除干扰
                        if any(n in q_lower for n in ["gta", "airdrop", "fifa", "launch"]):
                            continue
                        
                        if s not in mapping:
                            mapping[s] = {
                                "upTokenId": m["clobTokenIds"][0],    # 看涨 Token ID
                                "downTokenId": m["clobTokenIds"][1],  # 看跌 Token ID
                                "name": m.get("question")
                            }
                            break
                            
        if mapping:
            logging.info(f"📡 成功锁定 {len(mapping)} 个活跃市场的 Token ID")
        else:
            logging.warning("⚠️ 未能在 Gamma API 找到活跃市场，请检查网络或关键词")
            
    except Exception as e:
        logging.error(f"❌ market.py 获取动态 ID 失败: {e}")
    
    return mapping

# --- 如果需要手动指定，这里是你提供的 ID 快速索引 (用于 main.py 或测试) ---
STATIC_IDS = {
    "BTC": {
        "up": "68033518322462335017843667442682033117378620344572675041159649454017731343067",
        "down": "4857959446965795970976860511013818094677564843650044896579455854964354881854"
    },
    "ETH": {
        "up": "69256652064245782780529774986464293775776470783862394043049517906034686817838",
        "down": "5463917290293294768422587344326048548268618362346459234743933989476551528987"
    },
    "SOL": {
        "up": "69279838525883726555095532302298388729363341281749130469766889916023297995857",
        "down": "64765597988237464006795534311868785038220787854016227382174572792711823011082"
    },
    "XRP": {
        "up": "104411914481477053534318561802554024712780205781706160410044625323904170812315",
        "down": "78305837986307999911003841491899832231273386732702850651664192323121509554051"
    },
    "HYPE": {
        "up": "50038771340418993294018272397092069940213741826586333972616522505039311929390",
        "down": "96937935180550481071812156164606220550297160543323408939052294433375284503029"
    },
    "DOGE": {
        "up": "77246462665187791918411548893693981594268749639354665802735462289608435220396",
        "down": "53200683549240953177111470267108001228810714120869358213345876103084235397625"
    },
    "BNB": {
        "up": "88438400974108281071153782653753259556878826837492102662188120562364103801244",
        "down": "44276292184228714549958513042732610153778868935733901181917332805027190282661"
    }
}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = fetch_latest_market_map()
    import json
    print(json.dumps(res, indent=2, ensure_ascii=False))
