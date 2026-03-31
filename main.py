import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 1. 环境变量 (Railway)
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ======================
# 2. 模拟盘配置
# ======================
INITIAL_BALANCE = 100000.0
BET_AMOUNT = 10.0         # 模拟每次下注 100U
INTERVAL = 300             # 5分钟

balance = INITIAL_BALANCE
total_win = 0
total_lose = 0
hour_profit = 0.0
cycle_count = 0

MARKETS = ["BTC-75K-YES", "ETH-4K-YES", "SOL-200-YES", "DOGE-0.3-YES"]

# ======================
# 3. 功能函数
# ======================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def get_simulated_outcome():
    # 模拟 35% 胜率（测试策略）
    return "WIN" if random.random() < 0.35 else "LOSE"

# ======================
# 4. 核心逻辑
# ======================
async def run_trade_cycle():
    global balance, total_win, total_lose, hour_profit, cycle_count

    market = random.choice(MARKETS)
    result = get_simulated_outcome()
    
    # 模拟真实损耗：0.1% 手续费
    fee = BET_AMOUNT * 0.001
    
    if result == "WIN":
        # 模拟高赔率：中奖翻倍
        profit = (BET_AMOUNT * 2.0) - fee
        total_win += 1
    else:
        profit = -BET_AMOUNT - fee
        total_lose += 1

    balance += profit
    hour_profit += profit
    cycle_count += 1
    roi = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    msg_5m = f"""
🦞 龙虾虚拟盘 | 5min
⏰ {datetime.now().strftime('%H:%M:%S')}
📊 市场: {market}
🎯 结果: {result}
💰 盈亏: {profit:+.2f}U
💼 余额: {balance:.2f}U
📈 累计ROI: {roi:.2f}%
"""
    print(msg_5m)
    send_telegram(msg_5m)

    if cycle_count >= 12:
        win_rate = (total_win / (total_win + total_lose)) * 100 if (total_win + total_lose) > 0 else 0
        msg_1h = f"""
📊【龙虾模拟盘 - 小时复盘】
━━━━━━━━━━━━━━
✅ 胜: {total_win} | ❌ 负: {total_lose}
🎯 总胜率: {win_rate:.2f}%
💰 本小时盈亏: {hour_profit:+.2f}U
💼 当前资产: {balance:.2f}U
━━━━━━━━━━━━━━
"""
        send_telegram(msg_1h)
        hour_profit = 0.0
        cycle_count = 0

# ======================
# 5. 主启动
# ======================
async def main():
    send_telegram("🚀 龙虾虚拟系统已修复启动！")
    while True:
        start_time = time.time()
        await run_trade_cycle()
        wait_time = max(0, INTERVAL - (time.time() - start_time))
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    # 注意：这里的括号已经补全，完美闭合
    asyncio.run(main())
