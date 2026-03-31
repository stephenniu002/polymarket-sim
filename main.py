import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 环境变量（Railway）
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ======================
# 配置
# ======================
BET_AMOUNT = 10
INTERVAL = 300  # 5分钟

balance = 10000.0  # 初始资金
win = 0
lose = 0

MARKETS = ["BTC", "ETH", "XRP", "SOL", "DOGE", "BNB"]

# ======================
# Telegram 推送
# ======================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg
        })
    except Exception as e:
        print("TG error:", e)

# ======================
# 模拟交易逻辑
# ======================
def simulate_trade():
    return "win" if random.random() < 0.03 else "lose"

async def run_trade_cycle():
    global balance, win, lose

    market = random.choice(MARKETS)
    result = simulate_trade()

    if result == "win":
        profit = 1000 - BET_AMOUNT
        balance += profit
        win += 1
    else:
        balance -= BET_AMOUNT
        lose += 1

    roi = (balance - 10000) / 10000 * 100

    msg = f"""
🦞 龙虾交易报告

⏰ 时间: {datetime.now().strftime('%H:%M:%S')}
📊 市场: {market} 5m

🎯 结果: {result.upper()}
💰 本次下注: {BET_AMOUNT}U

📈 胜: {win} | 负: {lose}
💼 当前余额: {balance:.2f}U
📊 ROI: {roi:.2f}%
"""
    print(msg)
    send_telegram(msg)

    # 止损保护
    if balance < 8000:
        send_telegram("🛑 已触发止损（余额低于8000U），系统暂停运行")
        os._exit(0)

# ======================
# 主循环
# ======================
async def main():
    send_telegram("🚀 龙虾系统启动 | 初始资金 10000U | 已开启止损保护")

    while True:
        start_time = asyncio.get_event_loop().time()
        
        await run_trade_cycle()
        
        # 计算剩余等待时间，确保每5分钟运行一次
        elapsed = asyncio.get_event_loop().time() - start_time
        sleep_time = max(0, INTERVAL - elapsed)
        await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    asyncio.run(main())
