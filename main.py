import asyncio
import logging
import os
import requests

# ⚠️ 这里的导入名必须与 market.py 保持严格一致
from market import get_all_active_5min_markets, get_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LOBSTER-CORE")

TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_notification(msg):
    if TG_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": f"🦞 {msg}"}, timeout=5)
        except: pass

async def hunting_filter(t, data):
    if t != "TRADE": return
    token_id = data.get("token_id")
    
    # 只在“最后一分钟”开火
    if token_id not in top_markets(): return

    strategy = choose_strategy()
    score = score_signal(data, strategy)
    if score < 2: return

    balance = get_balance()
    size = calc_size(balance, strategy)
    if size <= 0: return

    price = float(data.get("price", 0))
    logger.info(f"🎯 捕捉反转信号! Score: {score} | Token: {token_id[:8]}")
    
    place_order(token_id=token_id, price=price, size=size, side="BUY")

async def main():
    logger.info("🚀 龙虾加密猎手 V2.0 启动...")
    while True:
        try:
            markets = get_all_active_5min_markets()
            listen_tokens = []
            for m in markets:
                y, n = get_tokens(m)
                if y: listen_tokens.append(y)
            
            if not listen_tokens:
                await asyncio.sleep(30)
                continue

            # 监听第一个活跃盘口
            await stream(listen_tokens[0], hunting_filter)
        except Exception as e:
            logger.error(f"📡 运行异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
