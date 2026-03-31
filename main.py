import asyncio
import random
import requests
import time
import os
from datetime import datetime

# ======================
# 1. 环境变量配置
# ======================
# 请确保在 Railway 的 Variables 页面配置了这两个 key
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ======================
# 2. 交易参数配置
# ======================
BET_AMOUNT = 10       # 每单下注 10U
INTERVAL = 300        # 5分钟轮询一次
INITIAL_BALANCE = 10000.0
balance = INITIAL_BALANCE

# 监控的市场列表 (7个)
MARKETS = ["BTC", "ETH", "XRP", "BNB", "DOGE", "SOL", "HYPE"]

# 统计数据
hour_win = 0
hour_lose = 0
hour_profit = 0.0
cycle_count = 0  # 计数器，到12次(1小时)触发汇报

# ======================
# 3. 功能函数
# ======================
def send_telegram(msg):
    """发送消息到 Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print(f"⚠️ 未配置 TG 变量: {msg}")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"❌ TG 发送失败: {e}")

def simulate_trade():
    """模拟交易结果：3.2% 胜率 (对应 Polymarket 极端反转胜率)"""
    return "WIN" if random.random() < 0.032 else "LOSE"

def trade_one_market(market):
    """执行单个市场的模拟逻辑"""
    global balance, hour_win, hour_lose, hour_profit

    result = simulate_trade()

    if result == "WIN":
        # 假设赔率 100 倍 (10U 变 1000U)，净利 990U
        profit = 990.0
        hour_win += 1
    else:
        # 亏损掉本金 10U
        profit = -10.0
        hour_lose += 1

    balance += profit
    hour_profit += profit

    return f"{market}: {result} ({'+' if profit > 0 else ''}{profit}U)"

# ======================
# 4. 核心循环任务
# ======================
async def run_trade_cycle():
    """每 5 分钟跑一次的全币种扫描"""
    global cycle_count, hour_win, hour_lose, hour_profit

    results_text = []
    
    # 7个市场并发模拟
    for m in MARKETS:
        res = trade_one_market(m)
        results_text.append(res)

    cycle_count += 1
    
    # --- 5分钟实时简报 ---
    now_str = datetime.now().strftime('%H:%M:%S')
    report_5m = f"🦞 *5分钟多市场报告*\n⏰ {now_str}\n\n"
    report_5m += "\n".join(results_text)
    report_5m += f"\n\n💰 当前余额: {balance:.2f}U"
    
    send_telegram(report_5m)
    print(f"[{now_str}] 5分钟报表已发送")

    # --- 每 1 小时大总结 (12次循环) ---
    if cycle_count >= 12:
        total_trades = hour_win + hour_lose
        win_rate = (hour_win / total_trades * 100) if total_trades else 0
        
        report_1h = f"""
📊 *【1小时战报汇总】*
------------------------
🧾 交易总数: {total_trades}
✅ 胜: {hour_win} | ❌ 负: {hour_lose}
🎯 实时胜率: {win_rate:.2f}%

💵 本时段盈亏: {hour_profit:+.2f}U
💼 账户总余额: {balance:.2f}U
------------------------
        """
        send_telegram(report_1h)
        
        # 重置小时统计
        hour_win = 0
        hour_lose = 0
        hour_profit = 0.0
        cycle_count = 0

async def main():
    """主程序入口"""
    start_msg = "🚀 *龙虾模拟系统 V2 启动*\n7市场并发扫描中...\n初始资金: 10000U"
    print(start_msg)
    send_telegram(start_msg)

    while True:
        start_time = time.time()
        
        # 执行一轮交易
        await run_trade_cycle()
        
        # 精确等待 5 分钟 (扣除执行代码的时间)
        wait_time = max(0, INTERVAL - (time.time() - start_time))
        await asyncio.sleep(wait_time)

# ======================
# 5. 标准 Python 启动入口
# ======================
if __name__ == "__main__":
    # 这里的函数名 main() 必须和上面 async def main() 对应
    asyncio.run(main()
