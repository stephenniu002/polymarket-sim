import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 1. 环境变量 (Railway 设置)
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ======================
# 2. 模拟盘配置
# ======================
INITIAL_BALANCE = 100000.0  # 初始 100万U 虚拟金
BET_AMOUNT = 10.0         # 每次下注 10U (加大筹码看效果)
INTERVAL = 300             # 5分钟频率

# 模拟统计池
balance = INITIAL_BALANCE
total_win = 0
total_lose = 0
hour_profit = 0.0
cycle_count = 0

# 模拟市场列表
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
    """
    核心算法占位：未来这里接入真实 API 价格判断
    目前模拟：35% 胜率，但获利倍数设为 3倍 (高赔率策略)
    """
    is_win = random.random() < 0.35
    return "WIN" if is_win else "LOSE"

# ======================
# 4. 交易循环
# ======================
async def run_trade_cycle():
    global balance, total_win, total_lose, hour_profit, cycle_count

    market = random.choice(MARKETS)
    result = get_simulated_outcome()
    
    # 模拟真实磨损：扣除 0.1% 手续费
    fee = BET_AMOUNT * 0.001
    
    if result == "WIN":
        # 假设买入的是 0.3 价格的订单，赢了翻 3.3 倍
        profit = (BET_AMOUNT * 2.3) - fee
        total_win += 1
    else:
        profit = -BET_AMOUNT - fee
        total_lose += 1

    balance += profit
    hour_profit += profit
    cycle_count += 1
    roi = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    # --- 5分钟：单次结果报告 ---
    msg_5m = f"""
🦞 龙虾虚拟盘 | 5min
⏰ {datetime.now().strftime('%H:%M:%S')}
📊 市场: {market}
🎯 结果: {result}
💰 盈亏: {profit:+.2f}U (含手续费)
💼 余额: {balance:.2f}U
📈 累计ROI: {roi:.2f}%
"""
    print(msg_5m)
    send_telegram(msg_5m)

    # --- 1小时：阶段复盘报告 ---
    if cycle_count >= 12:
        win_rate = (total_win / (total_win + total_lose)) * 100
        msg_1h = f"""
📊【龙虾模拟盘 - 小时结转】
━━━━━━━━━━━━━━
🧾 周期交易: 12 次
✅ 胜: {total_win} | ❌ 负: {total_lose}
🎯 总胜率: {win_rate:.2f}%
💰 本小时盈亏: {hour_profit:+.2f}U
💼 当前总资产: {balance:.2f}U
━━━━━━━━━━━━━━
"""
        send_telegram(msg_1h)
        # 重置小时缓存
        hour_profit = 0.0
        cycle_count = 0

# ======================
# 5. 主程序入口
# ======================
async def main():
    start_msg = f"🚀 龙虾虚拟盘系统启动\n💰 初始资金: {INITIAL_BALANCE}U\n🛠️ 模式: 策略回测模式"
    send_telegram(start_msg)
    
    while True:
        start_time = time.time()
        
        await run_trade_cycle()
        
        # 确保每 5 分钟精准运行
        elapsed = time.time() - start_time
        await asyncio.sleep(max(0, INTERVAL - elapsed))

# ----------------------------
# 启动入口（必须有）
# ----------------------------
if __name__ == "__main__":
    print("🚀 系统启动中...")
    asyncio.run(run())
    # 使用标准入口
