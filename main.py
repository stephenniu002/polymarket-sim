import asyncio
import json
import websockets
import time
import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs

# ================= 配置 =================
WS_URL = "wss://clob.polymarket.com/ws/"
EDGE_THRESHOLD = 0.006      # 0.6% 空间即下单
ORDER_SIZE = 1.0            # 每次 1U
REPORT_INTERVAL = 300       

# ===== 真实 Token ID 映射 (已填入你提供的 ID) =====
MARKETS = {
    "BTC": {
        "YES": "104411914481477053534318561802554024712780205781706160410044625323904170812315", 
        "NO": "78305837986307999911003841491899832231273386732702850651664192323121509554051"
    },
    "HYPE": {
        "YES": "50038771340418993294018272397092069940213741826586333972616522505039311929390", 
        "NO": "96937935180550481071812156164606220550297160543323408939052294433375284503029"
    },
    "DOGE": {
        "YES": "77246462665187791918411548893693981594268749639354665802735462289608435220396", 
        "NO": "53200683549240953177111470267108001228810714120869358213345876103084235397625"
    },
    "BNB": {
        "YES": "88438400974108281071153782653753259556878826837492102662188120562364103801244", 
        "NO": "44276292184228714549958513042732610153778868935733901181917332805027190282661"
    },
    # SOL/XRP/ADA 暂无真实 ID 可先注释或填入后启用
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ================= 初始化官方 SDK =================
def get_client():
    client = ClobClient("https://clob.polymarket.com", key=os.getenv("POLY_PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))
    return client

poly_client = get_client()

# ================= 核心逻辑 =================
async def execute_trade(market, y_id, n_id, y_p, n_p, edge):
    logging.info(f"🔥 发现机会! {market} Edge: {edge:.2%} | 执行对冲下单")
    
    def place(t_id, price):
        return poly_client.post_order(OrderArgs(
            price=round(price + 0.001, 3), # 微加价确保成交
            size=ORDER_SIZE,
            side="BUY",
            token_id=t_id
        ))

    # 并发下单
    await asyncio.gather(
        asyncio.to_thread(place, y_id, y_p),
        asyncio.to_thread(place, n_id, n_p)
    )

async def run():
    # 构建反向映射
    token_map = {}
    for m, t in MARKETS.items():
        token_map[t["YES"]] = (m, "YES", t["YES"], t["NO"])
        token_map[t["NO"]] = (m, "NO", t["YES"], t["NO"])

    prices = {}
    last_report = 0

    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                # 订阅符合 V2 规范的消息
                sub_msg = {
                    "type": "subscribe",
                    "topic": "book",
                    "market_ids": list(token_map.keys())
                }
                await ws.send(json.dumps(sub_msg))
                logging.info("✅ WebSocket 连接成功，开始监听盘口...")

                async for msg in ws:
                    data = json.loads(msg)
                    
                    # WebSocket 数据解析 (Polymarket 返回格式通常是列表)
                    if not isinstance(data, list): continue
                    
                    for item in data:
                        t_id = item.get("market_id")
                        if t_id in token_map:
                            market, side, y_id, n_id = token_map[t_id]
                            
                            # 更新盘口卖一价
                            if "asks" in item and item["asks"]:
                                prices.setdefault(market, {})[side] = float(item["asks"][0]["price"])

                            # 套利检测逻辑
                            if "YES" in prices.get(market, {}) and "NO" in prices.get(market, {}):
                                y_p = prices[market]["YES"]
                                n_p = prices[market]["NO"]
                                total = y_p + n_p
                                edge = 1 - total

                                # 过滤异常并判断门槛
                                if 0.8 < total < 0.994: # 满足 EDGE_THRESHOLD
                                    if edge > EDGE_THRESHOLD:
                                        await execute_trade(market, y_id, n_id, y_p, n_p, edge)
                                        prices[market] = {} # 下单后清空缓存，防止重复触发
                                    elif time.time() - last_report > 30: # 降低扫描日志频率
                                        logging.info(f"🔍 [{market}] Total: {total:.3f} | Edge: {edge:.2%}")

                    # 定时余额汇报
                    if time.time() - last_report > REPORT_INTERVAL:
                        try:
                            # 官方 SDK 获取余额
                            bal = await asyncio.to_thread(poly_client.get_balance)
                            logging.info(f"💰 当前账户状态: {bal}")
                            last_report = time.time()
                        except: pass

        except Exception as e:
            logging.warning(f"⚠️ 链接中断: {e}，5秒后重试")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run())
