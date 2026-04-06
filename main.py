import os
import asyncio
import time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================== 目标市场配置 ==================
# 将你提供的 ID 填入列表
MARKETS = [
    {"name": "BTC", "yes": "104411914481477053534318561802554024712780205781706160410044625323904170812315", "no": "78305837986307999911003841491899832231273386732702850651664192323121509554051"},
    {"name": "HYPE", "yes": "50038771340418993294018272397092069940213741826586333972616522505039311929390", "no": "96937935180550481071812156164606220550297160543323408939052294433375284503029"},
    {"name": "DOGE", "yes": "77246462665187791918411548893693981594268749639354665802735462289608435220396", "no": "53200683549240953177111470267108001228810714120869358213345876103084235397625"},
    {"name": "BNB", "yes": "88438400974108281071153782653753259556878826837492102662188120562364103801244", "no": "44276292184228714549958513042732610153778868935733901181917332805027190282661"}
]

# 策略参数
EDGE_THRESHOLD = 0.006     # 利润空间 > 0.6% 触发
ORDER_SIZE = 1.0           # 基础下单 1 USDC

# ================== 初始化 Client ==================
client = ClobClient(host="https://clob.polymarket.com", key=os.getenv("POLY_PRIVATE_KEY"), chain_id=137)
client.set_api_creds(ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
))

async def get_best_ask(token_id):
    """获取卖一价"""
    try:
        book = client.get_orderbook(token_id)
        if hasattr(book, 'asks') and len(book.asks) > 0:
            return float(book.asks[0].price)
        return 1.0
    except:
        return 1.0

async def trade_logic():
    print("🦞 Lobster 多市场对冲监控中...")
    while True:
        for m in MARKETS:
            try:
                # 1. 获取盘口数据
                y_ask = await get_best_ask(m["yes"])
                n_ask = await get_best_ask(m["no"])
                
                total = y_ask + n_ask
                edge = 1 - total
                
                print(f"🔍 [{m['name']}] Total: {total:.4f} | Edge: {edge*100:.2f}%")

                # 2. 发现套利空间
                if edge > EDGE_THRESHOLD:
                    print(f"💰 捕捉到机会! 在 {m['name']} 市场执行对冲...")
                    
                    # 同时买入 YES 和 NO 锁定利润
                    # 动态分配：Edge 每增加 1%，投入加 1 USDC
                    dynamic_size = round(min(ORDER_SIZE + (edge * 100), 4.0), 2)
                    
                    await asyncio.gather(
                        asyncio.to_thread(client.post_order, {
                            "price": round(y_ask + 0.001, 3),
                            "size": dynamic_size, "side": "BUY", "token_id": m["yes"]
                        }),
                        asyncio.to_thread(client.post_order, {
                            "price": round(n_ask + 0.001, 3),
                            "size": dynamic_size, "side": "BUY", "token_id": m["no"]
                        })
                    )
                    print(f"🔥 对冲成功: 投入 {dynamic_size}x2 | 锁定利润: {edge * dynamic_size:.4f} USDC")
                
            except Exception as e:
                print(f"⚠️ {m['name']} 处理异常: {e}")
            
            await asyncio.sleep(0.5) # 每个市场查完歇半秒，防止被限流

async def main():
    await trade_logic()

if __name__ == "__main__":
    asyncio.run(main())
