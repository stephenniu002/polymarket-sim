import asyncio
import logging
import os
# 🔧 这里的导入严格按照方案 A 执行
from market import load_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LOBSTER-CORE")

async def hunting_filter(t, data):
    if t != "TRADE": return
    token_id = data.get("token_id")
    
    # 过滤：只在目标 Token 列表里才处理
    if token_id not in top_markets():
        return

    strategy = choose_strategy()
    score = score_signal(data, strategy)
    if score < 2: return

    balance = get_balance()
    size = calc_size(balance, strategy)
    if size <= 0: return

    price = float(data.get("price", 0))
    logger.info(f"🎯 命中目标! Price: {price} | Token: {token_id[:8]}")
    place_order(token_id=token_id, price=price, size=size, side="BUY")

async def main():
    logger.info("🚀 龙虾系统 V2.0 (方案 A) 启动...")
    while True:
        try:
            # 🔧 修改后的获取方式
            targets = load_tokens()
            
            if not targets:
                # logger.info("💤 等待盘口中...")
                await asyncio.sleep(30)
                continue

            # 监听第一个目标的 WebSocket
            first_token = targets[0]["token"]
            await stream(first_token, hunting_filter)
            
        except Exception as e:
            logger.error(f"📡 运行异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
