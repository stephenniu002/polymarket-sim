import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 1. 核心环境变量配置
# ======================
# 请在 Railway 的 Variables 页面配置这两个 Key
TELEGRAM_TOKEN = os.getenv("8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY")
CHAT_ID = os.getenv("5739995837")

# ======================
# 2. 模拟盘参数设置
# ======================
INITIAL_BALANCE = 100000.0  # 初始资金 10万U
balance = INITIAL_BALANCE
BET_AMOUNT = 10.01          # 每单下注 (含滑点模拟)
WIN_PAYOUT = 1000.0         # 100倍赔率

# 监控的市场列表
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE-0.3-YES", "SOL", "HYPE"]

# 统计数据
hour_win = 0
hour_lose = 0
hour_profit = 0.0
cycle_count = 0  # 计数器，到12次(1小时)触发汇总

# ======================
# 3. 功能函数
# ======================
def send_telegram(msg):
    """发送消息到 Telegram，带 Markdown 解析"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print(f"⚠️ [未配置 TG 变量] 消息内容:\n{msg}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        # 增加超时处理，防止网络波动卡死程序
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ TG 发送异常: {response.text}")
    except Exception as e:
        print(f"❌ TG 网络连接失败: {e}")

def simulate_trade():
    """
    模拟 Polymarket 极端反转胜率
    设定为 3.1% 的基础中奖概率
    """
    return "WIN" if random.random() < 0.031 else "LOSE"

# ======================
# 4. 核心逻辑循环
# ======================
async def run_trade_cycle():
    """每 5 分钟跑一次的全币种扫描报表"""
    global balance, hour_win, hour_lose, hour_profit, cycle_count

    now_time = datetime.now().strftime('%H:%M:%S')
    results_lines = []
    current_profit = 0.0

    # 遍历市场，保证报表顺序固定
    for market in MARKETS:
        result = simulate_trade()
        
        if result == "WIN":
            pnl = WIN_PAYOUT - BET_AMOUNT
            status = "🟢 WIN "
            hour_win += 1
        else:
            pnl = -BET_AMOUNT
            status = "🔴 LOSE"
            hour_lose += 1
        
        balance += pnl
        current_profit += pnl
        hour_profit += pnl
        
        # 格式化每一行报表内容
        results_lines.append(f"`{market:12}`: {status} ({pnl:+.2f}U)")

    cycle_count += 1
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    # --- 构建 5 分钟 Telegram 报表 ---
    report = f"🦞 *龙虾虚拟盘 | 5min 多市场报告*\n"
    report += f"⏰ 时间: `{now_time}`\n"
    report += "----------------------------\n"
    report += "\n".join(results_lines)
    report += "\n----------------------------\n"
    report += f"💰 当前余额: *{balance:.2f}U*\n"
    report += f"📈 累计 ROI: *{roi:.2f}%*"

    # 同时发送到日志和电报
    print(report)
    send_telegram(report)

    # --- 每 1 小时自动汇总 (12次为一周期) ---
    if cycle_count >= 12:
        total_trades = hour_win + hour_lose
        win_rate = (hour_win / total_trades * 100) if total_trades else 0
        
        summary = f"📊 *【1小时统计大报表】*\n"
        summary += f"----------------------------\n"
        summary += f"🧾 交易总数: {total_trades}\n"
        summary += f"✅ 胜数: {hour_win} | ❌ 负数: {hour_lose}\n"
        summary += f"🎯 实时胜率: *{win_rate:.2f}%*\n\n"
        summary += f"💵 本时段盈亏: *{hour_profit:+.2f}U*\n"
        summary += f"💼 最终账户余额: *{balance:.2f}U*\n"
        summary += f"----------------------------"
        
        send_telegram(summary)
        print(f"✅ 已发送小时总结报告")

        # 重置统计缓存
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0.0, 0

# ======================
# 5. 主程序启动入口
# ======================
async def main():
    # 启动确认
    start_msg = f"🚀 *龙虾模拟系统启动成功*\n市场: 7个并发监控\n初始: {INITIAL_BALANCE}U\n电报接收状态: 🟢 已连接"
    print(start_msg)
    send_telegram(start_msg)

    while True:
        start_loop = time.time()
        
        # 执行一轮扫描
        await run_trade_cycle()
        
        # 确保每轮严格间隔 300 秒 (5分钟)
        elapsed = time.time() - start_loop
        wait_time = max(0, 300 - elapsed)
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    # 彻底解决 NameError: 确保调用 main()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 系统已手动停止")
