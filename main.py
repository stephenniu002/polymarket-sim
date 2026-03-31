import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ==========================================
# 🚀 1. 核心配置区
# ==========================================
# Railway 或本地环境变量配置
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY"
CHAT_ID = os.getenv("CHAT_ID") or "5739995837"

# ==========================================
# 💰 2. 模拟盘参数
# ==========================================
INITIAL_BALANCE = 1000000.0  # 初始 100万 U
balance = INITIAL_BALANCE
BET_AMOUNT = 10.01           # 包含滑点/手续费
WIN_PAYOUT = 1000.0          # 模拟百倍爆点
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE-0.3-YES", "SOL", "HYPE"]

# 统计全局变量
hour_win = 0
hour_lose = 0
hour_profit = 0.0
cycle_count = 0

# 连续亏损保护阈值（可选）
MAX_CONSECUTIVE_LOSE = 10
consecutive_lose = 0

# ==========================================
# 🛠 3. Telegram 推送函数
# ==========================================
def send_telegram(msg: str):
    """发送 Telegram 消息，如果未配置会打印到日志"""
    if not TELEGRAM_TOKEN or "在这里" in TELEGRAM_TOKEN or not CHAT_ID:
        print(f"🛑 [未配置] 无法发送电报，请检查环境变量或代码。")
        print(f"📄 待发内容:\n{msg}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ TG 发送异常: {response.text}")
    except Exception as e:
        print(f"❌ TG 网络连接失败: {e}")

# ==========================================
# 📈 4. 核心交易逻辑
# ==========================================
async def run_trade_cycle():
    global balance, hour_win, hour_lose, hour_profit, cycle_count, consecutive_lose
    now_time = datetime.now().strftime('%H:%M:%S')
    results_lines = []
    current_profit = 0.0

    for market in MARKETS:
        # 模拟 3.1% 胜率
        is_win = random.random() < 0.031

        if is_win:
            pnl = WIN_PAYOUT - BET_AMOUNT
            status = "🟢 WIN "
            hour_win += 1
            consecutive_lose = 0
        else:
            pnl = -BET_AMOUNT
            status = "🔴 LOSE"
            hour_lose += 1
            consecutive_lose += 1

        balance += pnl
        current_profit += pnl
        hour_profit += pnl

        results_lines.append(f"{market:12}: {status} ({pnl:+.2f}U)")

    cycle_count += 1
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    # 构建报表
    report = f"🦞 *龙虾虚拟盘 | 5min 多市场报告*\n"
    report += f"⏰ 时间: `{now_time}`\n"
    report += "----------------------------\n"
    report += "\n".join(results_lines)
    report += "\n----------------------------\n"
    report += f"💰 当前余额: *{balance:.2f}U*\n"
    report += f"📈 累计 ROI: *{roi:.4f}%*"

    print(report)
    send_telegram(report)

    # 每 1 小时（12轮）发送统计汇总
    if cycle_count >= 12:
        total = hour_win + hour_lose
        win_rate = (hour_win / total * 100) if total else 0
        summary = f"📊 *【1小时统计大报表】*\n"
        summary += f"----------------------------\n"
        summary += f"✅ 胜/负: {hour_win} / {hour_lose}\n"
        summary += f"🎯 实时胜率: *{win_rate:.2f}%*\n"
        summary += f"💵 小时盈亏: *{hour_profit:+.2f}U*\n"
        summary += f"💼 最终余额: *{balance:.2f}U*"
        send_telegram(summary)

        # 重置小时计数
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0.0, 0

    # 连续亏损保护
    if consecutive_lose >= MAX_CONSECUTIVE_LOSE:
        warn_msg = f"⚠️ 连续亏损 {consecutive_lose} 次，建议暂停或降低下注！"
        print(warn_msg)
        send_telegram(warn_msg)
        consecutive_lose = 0  # 重置计数

# ==========================================
# 🏁 5. 主程序入口
# ==========================================
async def main():
    # 启动自检
    is_ok = TELEGRAM_TOKEN and "在这里" not in TELEGRAM_TOKEN
    status_icon = "🟢 已连接" if is_ok else "🔴 未配置"

    start_msg = (
        f"🚀 *龙虾模拟系统启动成功*\n"
        f"----------------------------\n"
        f"市场: {len(MARKETS)} 个并发监控\n"
        f"初始资金: {INITIAL_BALANCE}U\n"
        f"电报接收: {status_icon}"
    )
    print(start_msg)
    send_telegram(start_msg)

    # 无限循环，每 5 分钟执行一次
    while True:
        start_loop_time = time.time()
        await run_trade_cycle()
        elapsed = time.time() - start_loop_time
        await asyncio.sleep(max(0, 300 - elapsed))  # 严格 5 分钟间隔

# ==========================================
# 🔹 启动脚本
# ==========================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 程序已手动停止")import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ==========================================
# 🚀 1. 核心配置区
# ==========================================
# Railway 或本地环境变量配置
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY"
CHAT_ID = os.getenv("CHAT_ID") or "5739995837"

# ==========================================
# 💰 2. 模拟盘参数
# ==========================================
INITIAL_BALANCE = 1000000.0  # 初始 100万 U
balance = INITIAL_BALANCE
BET_AMOUNT = 10.01           # 包含滑点/手续费
WIN_PAYOUT = 1000.0          # 模拟百倍爆点
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE-0.3-YES", "SOL", "HYPE"]

# 统计全局变量
hour_win = 0
hour_lose = 0
hour_profit = 0.0
cycle_count = 0

# 连续亏损保护阈值（可选）
MAX_CONSECUTIVE_LOSE = 10
consecutive_lose = 0

# ==========================================
# 🛠 3. Telegram 推送函数
# ==========================================
def send_telegram(msg: str):
    """发送 Telegram 消息，如果未配置会打印到日志"""
    if not TELEGRAM_TOKEN or "在这里" in TELEGRAM_TOKEN or not CHAT_ID:
        print(f"🛑 [未配置] 无法发送电报，请检查环境变量或代码。")
        print(f"📄 待发内容:\n{msg}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ TG 发送异常: {response.text}")
    except Exception as e:
        print(f"❌ TG 网络连接失败: {e}")

# ==========================================
# 📈 4. 核心交易逻辑
# ==========================================
async def run_trade_cycle():
    global balance, hour_win, hour_lose, hour_profit, cycle_count, consecutive_lose
    now_time = datetime.now().strftime('%H:%M:%S')
    results_lines = []
    current_profit = 0.0

    for market in MARKETS:
        # 模拟 3.1% 胜率
        is_win = random.random() < 0.031

        if is_win:
            pnl = WIN_PAYOUT - BET_AMOUNT
            status = "🟢 WIN "
            hour_win += 1
            consecutive_lose = 0
        else:
            pnl = -BET_AMOUNT
            status = "🔴 LOSE"
            hour_lose += 1
            consecutive_lose += 1

        balance += pnl
        current_profit += pnl
        hour_profit += pnl

        results_lines.append(f"{market:12}: {status} ({pnl:+.2f}U)")

    cycle_count += 1
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    # 构建报表
    report = f"🦞 *龙虾虚拟盘 | 5min 多市场报告*\n"
    report += f"⏰ 时间: `{now_time}`\n"
    report += "----------------------------\n"
    report += "\n".join(results_lines)
    report += "\n----------------------------\n"
    report += f"💰 当前余额: *{balance:.2f}U*\n"
    report += f"📈 累计 ROI: *{roi:.4f}%*"

    print(report)
    send_telegram(report)

    # 每 1 小时（12轮）发送统计汇总
    if cycle_count >= 12:
        total = hour_win + hour_lose
        win_rate = (hour_win / total * 100) if total else 0
        summary = f"📊 *【1小时统计大报表】*\n"
        summary += f"----------------------------\n"
        summary += f"✅ 胜/负: {hour_win} / {hour_lose}\n"
        summary += f"🎯 实时胜率: *{win_rate:.2f}%*\n"
        summary += f"💵 小时盈亏: *{hour_profit:+.2f}U*\n"
        summary += f"💼 最终余额: *{balance:.2f}U*"
        send_telegram(summary)

        # 重置小时计数
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0.0, 0

    # 连续亏损保护
    if consecutive_lose >= MAX_CONSECUTIVE_LOSE:
        warn_msg = f"⚠️ 连续亏损 {consecutive_lose} 次，建议暂停或降低下注！"
        print(warn_msg)
        send_telegram(warn_msg)
        consecutive_lose = 0  # 重置计数

# ==========================================
# 🏁 5. 主程序入口
# ==========================================
async def main():
    # 启动自检
    is_ok = TELEGRAM_TOKEN and "在这里" not in TELEGRAM_TOKEN
    status_icon = "🟢 已连接" if is_ok else "🔴 未配置"

    start_msg = (
        f"🚀 *龙虾模拟系统启动成功*\n"
        f"----------------------------\n"
        f"市场: {len(MARKETS)} 个并发监控\n"
        f"初始资金: {INITIAL_BALANCE}U\n"
        f"电报接收: {status_icon}"
    )
    print(start_msg)
    send_telegram(start_msg)

    # 无限循环，每 5 分钟执行一次
    while True:
        start_loop_time = time.time()
        await run_trade_cycle()
        elapsed = time.time() - start_loop_time
        await asyncio.sleep(max(0, 300 - elapsed))  # 严格 5 分钟间隔

# ==========================================
# 🔹 启动脚本
# ==========================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 程序已手动停止")
