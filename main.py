import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ==========================================
# 🚀 1. 核心配置区
# ==========================================
# 优先读取环境变量，读取不到则使用硬编码的备用值
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY"
CHAT_ID = os.getenv("CHAT_ID") or "5739995837"

# ==========================================
# 💰 2. 模拟盘参数
# ==========================================
INITIAL_BALANCE = 1000000.0
balance = INITIAL_BALANCE
BET_AMOUNT = 10.01
WIN_PAYOUT = 1000.0
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE-0.3-YES", "SOL", "HYPE"]

# 统计全局变量
hour_win = 0
hour_lose = 0
hour_profit = 0.0
cycle_count = 0
consecutive_lose = 0
MAX_CONSECUTIVE_LOSE = 20 # 调高一点，因为一轮有7个市场

# ==========================================
# 🛠 3. Telegram 推送函数
# ==========================================
def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or "在这里" in TELEGRAM_TOKEN or not CHAT_ID:
        print(f"🛑 [未配置] 无法发送电报。待发内容:\n{msg}")
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
        # 模拟胜率
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

        # 加上反引号保证对齐且不触发 Markdown 错误
        results_lines.append(f"`{market:12}: {status} ({pnl:+.2f}U)`")

    cycle_count += 1
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    report = f"🦞 *龙虾虚拟盘 | 5min 多市场报告*\n"
    report += f"⏰ 时间: `{now_time}`\n"
    report += "----------------------------\n"
    report += "\n".join(results_lines)
    report += "\n\n----------------------------\n"
    report += f"💰 当前余额: *{balance:.2f}U*\n"
    report += f"📈 累计 ROI: *{roi:.4f}%*"

    print(report)
    send_telegram(report)

    # 每小时统计
    if cycle_count >= 12:
        total = hour_win + hour_lose
        win_rate = (hour_win / total * 100) if total else 0
        summary = f"📊 *【1小时统计大报表】*\n"
        summary += f"----------------------------\n"
        summary += f"✅ 胜/负: {hour_win} / {hour_lose}\n"
        summary += f"🎯 胜率: *{win_rate:.2f}%*\n"
        summary += f"💵 盈亏: *{hour_profit:+.2f}U*\n"
        summary += f"💼 余额: *{balance:.2f}U*"
        send_telegram(summary)
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0.0, 0

    if consecutive_lose >= MAX_CONSECUTIVE_LOSE:
        warn_msg = f"⚠️ *风险提示*: 连续亏损已达 {consecutive_lose} 次！"
        send_telegram(warn_msg)
        consecutive_lose = 0

# ==========================================
# 🏁 5. 主程序入口
# ==========================================
async def main():
    # 彻底检查变量是否拿到
    is_ok = TELEGRAM_TOKEN and len(TELEGRAM_TOKEN) > 20
    status_icon = "🟢 已连接" if is_ok else "🔴 未配置"

    start_msg = (
        f"🚀 *龙虾模拟系统启动成功*\n"
        f"----------------------------\n"
        f"市场: {len(MARKETS)} 个并发监控\n"
        f"初始资金: {INITIAL_BALANCE}U\n"
        f"电报状态: {status_icon}"
    )
    print(start_msg)
    send_telegram(start_msg)

    while True:
        start_loop_time = time.time()
        await run_trade_cycle()
        await asyncio.sleep(max(0, 300 - (time.time() - start_loop_time)))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 程序停止")
