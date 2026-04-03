import asyncio
import logging
from market import get_all_active_5min_markets, get_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LOBSTER-CORE")

async def hunting_filter(t, data):
    """猎杀逻辑：白名单过滤 -> 评分 -> 控仓 -> 执行"""
    if t != "TRADE": return

    # 1. 检查当前成交的 Token 是否处于‘最后一分钟’
    # 如果不在 top_markets() 列表里，说明还没到开火时间
    active_tokens = top_markets()
    token_id = data.get("token_id")
    if token_id not in active_tokens:
        return

    # 2. 策略研判 (最后一分钟买反转)
    strategy = choose_strategy()
    score = score_signal(data, strategy)
    if score < 2: return # 分数不够不打

    # 3. 仓位管理
    balance = get_balance()
    size = calc_size(balance, strategy)
    if size <= 0: return

    # 4. 扣动扳机
    price = float(data["price"])
    logger.info(f"🎯 捕捉到末日反转信号! Score: {score} | Market: {token_id[:8]} | Size: {size}")
    
    # 异步下单
    place_order(token_id=token_id, price=price, size=size, side="BUY")

async def main():
    logger.info("🚀 龙虾高频猎手 V2.0 启动 (目标: 7大加密 5min 盘)")
    
    while True:
        try:
            # 扫描当前所有的 5min 目标
            markets = get_all_active_5min_markets()
            listen_list = []
            for m in markets:
                y, n = get_tokens(m)
                if y: listen_list.append(y)
                if n: listen_list.append(n)

            if not listen_list:
                logger.info("💤 扫描中：暂无活跃的加密 5min 盘口...")
                await asyncio.sleep(30)
                continue

            # 监听第一个热门 Token 开始循环。ws.py 的 stream 会持续推送数据给 hunting_filter
            await stream(listen_list[0], hunting_filter)
            
        except Exception as e:
            logger.error(f"📡 监听异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
