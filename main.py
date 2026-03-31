import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 1. 核心环境变量配置
# ======================
# 务必在 Railway 的 Variables 页面配置这两个 EXACT 名字的变量
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ======================
# 2. 模拟盘参数设置 (根据你的日志同步)
# ======================
INITIAL_BALANCE = 1000000.0  # 100万U 初始资金
balance = INITIAL_BALANCE
BET_AMOUNT = 10.01           # 包含滑点模拟

# 监控的市场列表
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE-0.3-YES", "SOL", "HYPE"]

# 统计数据
hour_win = 0
hour_lose = 0
hour_profit = 0.0
cycle_count = 0 

# ======================
# 3. 核心功能函数
# ======================
def send_telegram(msg):
    """
    发送消息到 Telegram
    如果变量没配好，会在日志里给出明确的红色警告
    """
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("🛑 [错误] TELEGRAM_TOKEN 或 CHAT_ID 为空！")
        print("👉 请去 Railway -> Variables 页面添加这两个变量。")
        print(f"📄 待发内容备份:\n{msg}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code != 200:
            print(f"❌ TG 发送失败，错误码: {response.status_code}, 原因: {response.text}")
    except Exception as e:
        print(f"❌ TG 网络连接异常: {e}")

def simulate_trade():
    """模拟 3.1% 的百倍暴利胜率"""
    return "WIN" if random.random() < 0.031 else "LOSE"

# ======================
# 4. 核心逻辑循环
# ======================
async def run_trade_cycle():
    global balance, hour_win, hour_lose, hour_profit, cycle_count

    now_time = datetime.now().strftime('%H:%M:%S')
    results_lines = []
    current_profit = 0.0

    # 遍历市场
    for market in MARKETS:
        result = simulate_trade()
        
        if result == "WIN":
            pnl = 990.0 - 0.01  # 模拟盈利扣除滑点
            status = "🟢 WIN "
            hour_win += 1
        else:
            pnl = -BET_AMOUNT
            status = "🔴 LOSE"
            hour_lose += 1
        
        balance += pnl
        current_profit += pnl
        hour_profit += pnl
        
        # 格式化报表，保证币种对齐
        results_lines.append(f"`{market:12}`: {status} ({pnl:+.2f}U)")

    cycle_count += 1
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    # --- 构建 Telegram 报表 ---
    report = f"🦞 *龙虾虚拟盘 | 5min 多市场报告*\n"
    report += f"⏰ 时间: `{now_time}`\n"
    report += "----------------------------\n"
    report += "\n".join(results_lines)
    report += "\n----------------------------\n"
    report += f"💰 当前余额: *{balance:.2f}U*\n"
    report += f"📈 累计 ROI: *{roi:.4f}%*"

    # 同步输出
    print(report)
    send_telegram(report)

    # 每 1 小时 (12次循环) 汇总
    if cycle_count >= 12:
        total = hour_win + hour_lose
        win_rate = (hour_win / total * 100) if total else 0
        summary = f"📊 *【1小时战报汇总】*\n"
        summary += f"----------------------------\n"
        summary += f"✅ 胜: {hour_win} | ❌ 负: {hour_lose}\n"
        summary += f"🎯 胜率: *{win_rate:.2f}%*\n"
        summary += f"💵 盈亏: *{hour_profit:+.2f}U*\n"
        summary += f"💼 余额: *{balance:.2f}U*\n"
        summary += f"----------------------------"
        send_telegram(summary)
        
        # 重置统计
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0.0, 0

# ======================
# 5. 启动入口
# ======================
async def main():
    # 初始检查环境变量
    status_icon = "🟢 已连接" if (TELEGRAM_TOKEN and CHAT_ID) else "🔴 未配置"
    
    start_msg = f"🚀 *龙虾模拟系统启动成功*\n----------------------------\n市场: 7个并发监控\n初始资金: {INITIAL_BALANCE}U\n电报状态: {status_icon}"
    print(start_msg)
    send_telegram(start_msg)

    while True:
        loop_start = time.time()
        await run_trade_cycle()
        
        # 严格 5 分钟轮询
        wait = max(0, 300 - (time.time() - loop_start))
        await asyncio.sleep(wait)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
