import asyncio
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from py_polymarket_sdk import ClobClient
import aiohttp

load_dotenv()

# ==========================================
# ⚙️ 1. 实战配置 (请在 Railway Variables 填好)
# ==========================================
POLY_CONFIG = {
    "key": os.getenv("POLY_API_KEY"),
    "secret": os.getenv("POLY_SECRET"),
    "passphrase": os.getenv("POLY_PASSPHRASE"),
    "private_key": os.getenv("POLY_PRIVATE_KEY"),
    "host": "https://clob.polymarket.com"
}

# 策略参数
BET_AMOUNT = 1.0          # 每笔 1U
SHADOW_THRESHOLD = 3      # 连亏 3 次即切入影子模式 (避险)
REVERSAL_TIME = 60        # 倒计时 60 秒触发“反转买入”

# 7个目标币种 (需手动更新对应的 Condition ID)
MARKETS = {
    "BTC":  {"id": "0x1...", "base_dir": "涨"},
    "ETH":  {"id": "0x2...", "base_dir": "涨"},
    "XRP":  {"id": "0x3...", "base_dir": "涨"},
    "BNB":  {"id": "0x4...", "base_dir": "跌"},
    "DOGE": {"id": "0x5...", "base_dir": "涨"},
    "SOL":  {"id": "0x6...", "base_dir": "涨"},
    "HYPE": {"id": "0x7...", "base_dir": "涨"}
}

class LobsterRealBot:
    def __init__(self):
        self.client = ClobClient(
            POLY_CONFIG["host"], 
            key=POLY_CONFIG["key"], 
            secret=POLY_CONFIG["secret"], 
            passphrase=POLY_CONFIG["passphrase"], 
            private_key=POLY_CONFIG["private_key"]
        )
        self.is_shadow = False  # 初始为实战模式
        self.lose_streak = 0
        self.history = {}       # 记录本轮是否已下单

    async def send_tg(self, text):
        url = f"https://api.telegram.org/bot{os.getenv('TG_TOKEN')}/sendMessage"
        payload = {"chat_id": os.getenv("TG_CHAT_ID"), "text": text, "parse_mode": "Markdown"}
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)

    async def get_market_status(self, market_id):
        """获取倒计时和当前胜率"""
        market = self.client.get_market(market_id)
        # 简化逻辑：返回剩余秒数和当前 Yes 价格
        return market.get('end_time_remaining'), market.get('cur_price')

    async def execute_trade(self, coin, market_id, direction):
        """执行下单逻辑"""
        if self.is_shadow:
            return f"🧪 [影子观察] 预测 {direction}"
        
        try:
            # 执行反转买入 (如果是“涨”的反转，就买 NO)
            outcome = "NO" if direction == "涨" else "YES"
            # 这里的下单函数需根据 Polymarket SDK 最新文档调用
            resp = self.client.create_order(
                market_id=market_id,
                amount=BET_AMOUNT,
                outcome=outcome,
                side="BUY"
            )
            return f"💰 [实战下单] {outcome} 成功"
        except Exception as e:
            return f"❌ 失败: {str(e)[:20]}"

    async def run(self):
        print("🚀 龙虾实战系统已在 Railway (欧洲节点) 启动")
        await self.send_tg("🦞 *龙虾实战启动*\n模式: `💰 实战运行` | 初始: `1.0U/笔`")

        while True:
            results = []
            for coin, cfg in MARKETS.items():
                rem_time, price = await self.get_market_status(cfg['id'])
                
                # 核心逻辑：最后 1 分钟反转
                if rem_time and 0 < rem_time <= REVERSAL_TIME:
                    if cfg['id'] not in self.history:
                        status = await self.execute_trade(coin, cfg['id'], cfg['base_dir'])
                        results.append(f"`{coin:5}`: {status}")
                        self.history[cfg['id']] = True
                
                # 模拟盘的“避险”逻辑：如果连亏则切换
                if self.lose_streak >= SHADOW_THRESHOLD:
                    self.is_shadow = True

            if results:
                report = f"📊 *实时成交简报*\n" + "\n".join(results)
                await self.send_tg(report)
            
            # 清理历史 (每 5 分钟清一次，防止重复下单)
            if int(time.time()) % 300 < 10: self.history = {}
            
            await asyncio.sleep(10) # 高频轮询倒计时

if __name__ == "__main__":
    bot = LobsterRealBot()
    asyncio.run(bot.start())
