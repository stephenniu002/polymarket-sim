import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ==========================================
# 🚀 1. 核心配置区
# ==========================================
TELEGRAM_TOKEN = "TELEGRAM_TOKEN") 
CHAT_ID = CHAT_ID"
# ==========================================
# 💰 真实盘
# ==========================================
INITIAL_BALANCE = 600.0
balance = INITIAL_BALANCE
BET_AMOUNT = 1.0
WIN_PAYOUT = 100.0
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE", "SOL", "HYPE"]

# 统计全局变量
hour_win, hour_lose, hour_profit = 0, 0, 0.0
cycle_count = 0
consecutive_lose = 0
MAX_CONSECUTIVE_LOSE = 20  # 连亏 20 次触发影子模式

# 🛡️ 避险系统状态
is_shadow_mode = False

# ==========================================
# 🛠 3. Telegram 推送
# ==========================================
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ TG 连接失败: {e}")

# ==========================================
# 📈 4. 核心交易逻辑 (支持影子避险)
# ==========================================
async def run_trade_cycle():
    global balance, hour_win, hour_lose, hour_profit, cycle_count, consecutive_lose, is_shadow_mode
    
    now_time = datetime.now().strftime('%H:%M:%S')
    results_lines = []
    round_win_found = False

    # 检查风险状态
    if not is_shadow_mode and consecutive_lose >= MAX_CONSECUTIVE_LOSE:
        is_shadow_mode = True
        send_telegram(f"🛡️ *避险启动*: 连亏达 {consecutive_lose} 次，切入影子模式观察！")

    for market in MARKETS:
        # 模拟胜率 (3.1%)
        is_win = random.random() < 0.031

        if is_shadow_mode:
            # 🧪 影子模式：不扣钱，只记录
            pnl = 0 
            status = "🧪 SIM_WIN" if is_win else "🧪 SIM_LOSE"
            if is_win: round_win_found = True
        else:
            # 🟢 实战模式：真实结算
            if is_win:
                pnl = WIN_PAYOUT - BET_AMOUNT
                status = "🟢 WIN "
                hour_win += 1
                consecutive_lose = 0
                round_win_found = True
            else:
                pnl = -BET_AMOUNT
                status = "🔴 LOSE"
                hour_lose += 1
                consecutive_lose += 1
            
            balance += pnl
            hour_profit += pnl

        results_lines.append(f"`{market:12}: {status} ({pnl:+.2f}U)`")

    # 逻辑：影子模式下只要抓到一个 WIN，代表运气回归，切回实战
    if is_shadow_mode and round_win_found:
        is_shadow_mode = False
        consecutive_lose = 0
        send_telegram(f"✨ *信号回归*: 影子模式抓到 WIN，恢复实战下注！")

    cycle_count += 1
    roi = ((balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100

    # 5分钟报告
    mode_tag = "🧪 [影子观察]" if is_shadow_mode else "💰 [实战运行]"
    report = f"🦞 *龙虾虚拟盘 | 5min 简报*\n"
    report += f"状态: {mode_tag}\n"
    report += f"⏰ 时间: `{now_time}`\n"
    report += "----------------------------\n"
    report += "\n".join(results_lines)
    report += "\n\n----------------------------\n"
    report += f"💰 当前余额: *{balance:.2f}U*\n"
    report += f"📈 累计 ROI: *{roi:.4f}%*"

    print(report)
    send_telegram(report)

    # 📊 每小时统计总结 (12 轮)
    if cycle_count >= 12:
        total = hour_win + hour_lose
        win_rate = (hour_win / total * 100) if total else 0
        summary = (
            f"📊 *══ 一小时大结 ══*\n"
            f"✅ 胜/负: `{hour_win} / {hour_lose}`\n"
            f"🎯 胜率: `{win_rate:.2f}%`\n"
            f"💵 盈亏: `{hour_profit:+.2f}U`\n"
            f"💼 余额: `{balance:.2f}U`"
        )
        send_telegram(summary)
        # 重置统计，开启下一个小时
        hour_win, hour_lose, hour_profit, cycle_count = 0, 0, 0.0, 0

# ==========================================
# 🏁 5. 主程序入口
# ==========================================
async def main():
    start_msg = (
        f"🚀 *龙虾模拟系统启动成功*\n"
        f"----------------------------\n"
        f"市场: {len(MARKETS)} 个并发监控\n"
        f"初始资金: {INITIAL_BALANCE}U\n"
        f"避险阈值: 连亏 {MAX_CONSECUTIVE_LOSE} 轮"
    )
    print(start_msg)
    send_telegram(start_msg)

    while True:
        start_loop_time = time.time()
        await run_trade_cycle()
        # 精确 5 分钟 (300秒)
        await asyncio.sleep(max(0, 300 - (time.time() - start_loop_time)))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 程序停止")
