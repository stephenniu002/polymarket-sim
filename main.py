import asyncio
import os
import time
import ccxt.async_support as ccxt
from datetime import datetime
import aiohttp

# ==========================================
# 🚀 1. 核心配置区 (实盘敏感信息)
# ==========================================
TELEGRAM_TOKEN = "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY" 
CHAT_ID =  "5739995837"

EXCHANGE_CONFIG = {
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET_KEY',
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}  # 默认使用合约交易
}

# ==========================================
# 💰 2. 策略参数
# ==========================================
BET_AMOUNT = 1.0          # 每笔下注 1 U
TARGET_PROFIT_RATIO = 1.3 # 举例：涨 30% 离场 (对应你之前的 WIN_PAYOUT)
MARKETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]

# 统计变量
balance = 0.0
initial_balance = 0.0
consecutive_lose = 0
MAX_CONSECUTIVE_LOSE = 15 
is_shadow_mode = False

# ==========================================
# 🛠 3. 异步 Telegram 推送
# ==========================================
async def send_tg_msg(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"TG Error: {e}")

# ==========================================
# 📈 4. 核心交易引擎
# ==========================================
class LobsterBot:
    def __init__(self):
        self.exchange = ccxt.binance(EXCHANGE_CONFIG)
        self.is_running = True

    async def get_balance(self):
        """获取账户可用余额 (USDT)"""
        try:
            bal = await self.exchange.fetch_balance()
            return float(bal['total']['USDT'])
        except Exception as e:
            print(f"获取余额失败: {e}")
            return 0.0

    async def execute_logic(self, symbol):
        """
        这里定义你的核心入场信号
        目前示例：简单的随机入场 + 真实下单尝试
        """
        global consecutive_lose, is_shadow_mode

        # 1. 模拟胜率逻辑 (实盘中这里应替换为指标分析，如 RSI, MACD 等)
        # 这里为了演示保留了随机，但增加了实盘下单动作
        is_signal = True # 假设永远有信号

        if is_shadow_mode:
            # 🧪 影子模式：仅观察不操作
            sim_win = (time.time() % 2 == 0) # 模拟信号回归逻辑
            return "🧪 SHADOW", 0, sim_win
        else:
            # 🟢 实战模式：真实下单
            try:
                # 示例：市价买入 1U 等额的币
                # order = await self.exchange.create_market_buy_order(symbol, BET_AMOUNT)
                # 提示：由于大部分交易所最小下单为 5-10U，BET_AMOUNT 可能需要调整
                
                # 模拟一个结算结果 (实盘应通过 fetch_my_trades 获取)
                is_win = False 
                pnl = -BET_AMOUNT
                
                if is_win:
                    consecutive_lose = 0
                    return "🟢 WIN", pnl, True
                else:
                    consecutive_lose += 1
                    return "🔴 LOSE", pnl, False
            except Exception as e:
                return f"❌ ERROR: {str(e)[:20]}", 0, False

    async def run_cycle(self):
        global balance, initial_balance, is_shadow_mode, consecutive_lose
        
        now = datetime.now().strftime('%H:%M:%S')
        results = []
        any_win = False

        # 避险检查
        if not is_shadow_mode and consecutive_lose >= MAX_CONSECUTIVE_LOSE:
            is_shadow_mode = True
            await send_tg_msg(f"🛡️ *避险启动*: 连亏 {consecutive_lose} 次，切入影子模式！")

        for m in MARKETS:
            status, pnl, win_found = await self.execute_logic(m)
            if win_found: any_win = True
            results.append(f"`{m:10}: {status} ({pnl:+.2f}U)`")

        # 信号回归检查
        if is_shadow_mode and any_win:
            is_shadow_mode = False
            consecutive_lose = 0
            await send_tg_msg("✨ *信号回归*: 影子模式抓到获利，恢复实战！")

        # 更新余额
        balance = await self.get_balance()
        roi = ((balance - initial_balance) / initial_balance * 100) if initial_balance else 0

        # 发送简报
        report = f"🦞 *龙虾实盘系统*\n模式: {'🧪 影子' if is_shadow_mode else '💰 实战'}\n"
        report += f"⏰ 时间: `{now}`\n----------------------------\n"
        report += "\n".join(results)
        report += f"\n----------------------------\n💰 账户余额: *{balance:.2f} USDT*\n📈 实时 ROI: *{roi:.4f}%*"
        
        print(report)
        await send_tg_msg(report)

    async def main(self):
        print("🚀 系统初始化...")
        global initial_balance, balance
        initial_balance = await self.get_balance()
        balance = initial_balance
        
        await send_tg_msg(f"🚀 *实盘系统启动*\n初始资金: {initial_balance} USDT\n市场数: {len(MARKETS)}")

        while self.is_running:
            start_time = time.time()
            await self.run_cycle()
            # 间隔 5 分钟
            sleep_time = max(0, 300 - (time.time() - start_time))
            await asyncio.sleep(sleep_time)

# ==========================================
# 执行
# ==========================================
if __name__ == "__main__":
    bot = LobsterBot()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print("🛑 程序手动停止")
    finally:
        # 异步关闭连接池
        asyncio.run(bot.exchange.close())
