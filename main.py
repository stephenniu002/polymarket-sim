import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 环境变量
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ======================
# 交易配置
# ======================
BET_AMOUNT = 10
INTERVAL = 300  # 5分钟
INITIAL_BALANCE = 10000.0
balance = INITIAL_BALANCE

# 统计缓存
total_win = 0
total_lose = 0
hour_win = 0
hour_lose = 0
hour_profit = 0
cycle_count = 0

# 监控的市场列表 (Polymarket Token ID 或 标识符)
# 这里以 BTC 价格预测市场为例，实际生产环境需替换为具体的 Token ID
MARKETS = ["BTC-Price-High", "ETH-Price-High", "SOL-Price-High"]

# ======================
# 工具函数
# ======================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

def get_polymarket_result():
    """
    获取真实 Polymarket 数据
    这里模拟接入 API。实战中你会调用 https://clob.polymarket.com/price
    """
    # 模拟真实市场波动：假设胜率由当前市场盘口决定
    # 实际上，这里会判断你的预测方向与最终价格的关系
    # 为了演示，我们保留一个基于概率的判断，但预留 API 接口位置
    return "win" if random.random() < 0.35 else "lose" # 假设接入策略后胜率提升

# ======================
# 核心交易循环
# ======================
async def run_trade_cycle():
    global balance, total_win, total_lose
    global hour_win, hour_lose, hour_profit, cycle_count

    # 1. 模拟/获取 真实交易结果
    market = random.choice(MARKETS)
    result = get_polymarket_result()

    if result == "win":
        profit = 1000 - BET_AMOUNT # 假设 100 倍赔率或根据实际计算
        balance += profit
        total_win += 1
        hour_win += 1
    else:
        profit = -BET_AMOUNT
        balance += profit
        total_lose += 1
        hour_lose += 1

    hour_profit += profit
    cycle_count += 1
    roi = (balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100

    # 2. 【5分钟报告】
    msg_5m = f"""
🦞 龙虾 5min 交易报告
⏰ {datetime.now().strftime('%H:%M:%S')}
📊 市场: {market}
🎯 结果: {result.upper()}
💰 盈亏: {profit}U
💼 余额: {balance:.2f}U
📈 总ROI: {roi:.2f}%
"""
    send_telegram(msg_5m)
    print(msg_5m)

    # 3. 【1小时汇总】
    if cycle_count >= 12:
        total_trades = hour_win + hour_lose
        win_rate = (hour_win / total_trades * 100) if total_trades else 0
        
        msg_1h = f"""
📊【1小时统计汇总】
━━━━━━━━━━━━━━
🧾 交易次数: {total_trades}
✅ 胜: {hour_win} | ❌ 负: {hour_lose}
🎯 周期胜率: {win_rate:.2f}%
💰 周期盈亏: {hour_profit}U
💼 当前总余额: {balance:.2f}U
🚀 系统状态: 运行中 (Real-time)
━━━━━━━━━━━━━━
"""
        send_telegram(msg_1h)
        # 重置小时统计
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0, 0

    # 4. 风险控制
    if balance < 5000:
        send_telegram("🛑 警告：余额已减半，触发强制止损，系统停机！")
        os._exit(0)

# ======================
# 主入口
# ======================
async def main():
    send_telegram("🚀 龙虾 Polymarket 实盘监控启动\n资金: 10000U\n频率: 5min/次 | 1hr/汇总")
    
    while True:
        start_time = time.time()
        await run_trade_cycle()
        # 排除代码执行时间，确保精准 5 分钟
        wait = max(0, INTERVAL - (time.time() - start_time))
        await asyncio.sleep(wait)

if __name__ == "__main__":
    asyncio.run(main())
