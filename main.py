import asyncio
import os
import time
import logging
from datetime import datetime
import aiohttp
import ccxt.async_support as ccxt
from dotenv import load_dotenv

# 加载本地 .env (Railway 部署时会读取其 Variables 界面配置)
load_dotenv()

# ==========================================
# 🛡️ 1. 配置与安全区 (从环境变量读取)
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LobsterBot")

TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# 交易所配置 (支持 Polymarket 的 Clob 或 Binance)
EXCHANGE_CONFIG = {
    'apiKey': os.getenv("EXCHANGE_API_KEY"),
    'secret': os.getenv("EXCHANGE_SECRET"),
    'password': os.getenv("EXCHANGE_PASS"), # 部分交易所需要
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
}

# 策略参数
BET_AMOUNT = 10.0  # 实盘建议 > 10U 避开交易所限制
MAX_LOSE_STREAK = 15
MARKETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# ==========================================
# 📡 2. 通讯引擎
# ==========================================
async def send_tg_msg(msg: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.warning("TG 配置缺失，仅本地打印日志")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    logger.error(f"TG 发送失败: {resp.status}")
        except Exception as e:
            logger.error(f"TG 连接异常: {e}")

# ==========================================
# 🦞 3. 实盘机器人核心
# ==========================================
class LobsterBot:
    def __init__(self):
        self.exchange = ccxt.binance(EXCHANGE_CONFIG)
        self.is_running = True
        self.is_shadow_mode = False
        self.consecutive_lose = 0
        self.initial_balance = 0.0

    async def init_session(self):
        """初始化：检查 API 有效性并获取初始余额"""
        try:
            balance_data = await self.exchange.fetch_balance()
            self.initial_balance = float(balance_data['total'].get('USDT', 0))
            logger.info(f"✅ 系统初始化成功 | 初始资金: {self.initial_balance} USDT")
            await send_tg_msg(f"🚀 *实盘系统已上线 (Railway)*\n初始资金: `{self.initial_balance}` USDT")
            return True
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False

    async def get_current_price(self, symbol):
        """获取真实市场价格"""
        ticker = await self.exchange.fetch_ticker(symbol)
        return ticker['last']

    async def execute_trade_logic(self, symbol):
        """核心交易逻辑：实战与影子的分水岭"""
        # --- 这里替换为你真正的策略判定 (RSI/MACD等) ---
        # 简单示例：影子模式下模拟判定，实战模式下真实下单
        
        if self.is_shadow_mode:
            # 🧪 影子模式：模拟逻辑 (此处可接入真实行情判断)
            # 假设影子模式下，我们观察 5 分钟后的价格变动
            sim_win = (time.time() % 2 == 0) # 暂代
            return "🧪 SHADOW", 0, sim_win
        else:
            # 🟢 实战模式：真实下单
            try:
                # 真实的下单代码 (取消注释前请确保余额充足)
                # amount = BET_AMOUNT / await self.get_current_price(symbol)
                # order = await self.exchange.create_market_buy_order(symbol, amount)
                
                # 模拟结算逻辑 (实战中需通过 fetch_order 轮询结果)
                is_win = False 
                pnl = -BET_AMOUNT
                
                if not is_win:
                    self.consecutive_lose += 1
                else:
                    self.consecutive_lose = 0
                    
                return "🔴 LOSE" if not is_win else "🟢 WIN", pnl, is_win
            except Exception as e:
                logger.error(f"下单异常: {e}")
                return "❌ ERROR", 0, False

    async def run_cycle(self):
        """单次运行循环"""
        # 1. 风险对冲检查
        if not self.is_shadow_mode and self.consecutive_lose >= MAX_LOSE_STREAK:
            self.is_shadow_mode = True
            await send_tg_msg(f"🛡️ *避险强制启动*\n连亏 {self.consecutive_lose} 次，切入影子模式。")

        results = []
        any_win = False

        # 2. 遍历市场执行
        for symbol in MARKETS:
            status, pnl, win_found = await self.execute_trade_logic(symbol)
            if win_found: any_win = True
            results.append(f"`{symbol:10}: {status} ({pnl:+.2f}U)`")

        # 3. 信号回归逻辑
        if self.is_shadow_mode and any_win:
            self.is_shadow_mode = False
            self.consecutive_lose = 0
            await send_tg_msg("✨ *信号回归*: 影子模式抓到潜在获利，恢复实战！")

        # 4. 数据汇总与报告
        try:
            bal_data = await self.exchange.fetch_balance()
            current_bal = float(bal_data['total'].get('USDT', 0))
            roi = ((current_bal - self.initial_balance) / self.initial_balance * 100) if self.initial_balance else 0
            
            report = (f"🦞 *龙虾实战简报*\n"
                      f"模式: {'🧪 影子' if self.is_shadow_mode else '💰 实战'}\n"
                      f"----------------------------\n" + 
                      "\n".join(results) + 
                      f"\n----------------------------\n"
                      f"💰 当前余额: *{current_bal:.2f} USDT*\n"
                      f"📈 累计 ROI: *{roi:.4f}%*")
            
            await send_tg_msg(report)
            logger.info("Cycle completed and report sent.")
        except Exception as e:
            logger.error(f"报告生成失败: {e}")

    async def start(self):
        if not await self.init_session():
            return

        while self.is_running:
            start_time = time.time()
            await self.run_cycle()
            # 5 分钟周期，扣除程序执行时间
            wait_time = max(10, 300 - (time.time() - start_time))
            await asyncio.sleep(wait_time)

# ==========================================
# 🏁 4. 入口点
# ==========================================
if __name__ == "__main__":
    bot = LobsterBot()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        logger.info("用户停止机器人")
    finally:
        loop.run_until_complete(bot.exchange.close())
