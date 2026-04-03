import asyncio
import logging
from market import get_all_active_5min_markets, get_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LOBSTER-CORE")

async def hunting_filter(t, data):
    if t != "TRADE": return
    
    # 动态匹配最后一分钟
    active_tokens = top_markets()
    token_id = data.get("token_id")
    if token_id not in active_tokens: return

    # 策略执行
    strategy = choose_strategy()
    score = score_signal(data, strategy)
    if score < 2: return

    balance = get_balance()
    size = calc_size(balance, strategy)
    if size <= 0: return

    price = float(data["price"])
    logger.info(f"🎯 最后一分钟反转! Score: {score} | Market: {token_id[:8]} | Size: {size}")
    place_order(token_id=token_id, price=price, size=size, side="BUY")

async def main():
    logger.info("🚀 龙虾高频猎手 V2.0 启动")
    while True:
        try:
            markets = get_all_active_5min_markets()
            listen_list = []
            for m in markets:
                y, n = get_tokens(m)
                if y: listen_list.append(y)
                if n: listen_list.append(n)

            if not listen_list:
                await asyncio.sleep(30); continue

            # 监听主序列
            await stream(listen_list[0], hunting_filter)
        except Exception as e:
            logger.error(f"📡 监听异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
