import asyncio
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
from py_polymarket_sdk import ClobClient

# 1. 基础配置与日志
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LobsterPolyReal")

# 2. 环境变量读取 (必须在 Railway Variables 填好)
POLY_CONFIG = {
    "key": os.getenv("POLY_API_KEY"),
    "secret": os.getenv("POLY_SECRET"),
    "passphrase": os.getenv("POLY_PASSPHRASE"),
    "private_key": os.getenv("POLY_PRIVATE_KEY"),
    "host": "https://clob.polymarket.com"
}

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# 3. 策略参数：7个币种监测
BET_AMOUNT = 1.0        # 每笔 1U
REVERSAL_WINDOW = 65    # 最后 65 秒进入“反转准备”
CHECK_INTERVAL = 10     # 每 10 秒扫描一次所有市场

# 目标市场配置 (Condition ID 需要你根据 Polymarket 官网填入)
MARKETS = {
    "BTC":  {"id": "0x1...", "original": "涨"},
    "ETH":  {"id": "0x2...", "original": "涨"},
    "XRP":  {"id": "0x3...", "original": "涨"},
    "BNB":  {"id": "0x4...", "original": "跌"},
    "DOGE": {"id": "0x5...", "original": "涨"},
    "SOL":  {"id": "0x6...", "original": "涨"},
    "HYPE": {"id": "0x7...", "original": "涨"}
}

class LobsterPolyBot:
    def __init__(self):
        self.client = ClobClient(
            POLY_CONFIG["host"], 
            key=POLY_CONFIG["key"], 
            secret=POLY_CONFIG["secret"], 
            passphrase=POLY_CONFIG["passphrase"], 
            private_key=POLY_CONFIG["private_key"]
        )
        self.history = set()  # 防止同一周期重复下单

    async def send_tg(self, msg):
        if not TG_TOKEN: return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
            except: pass

    async def get_real_balance(self):
        """获取 Polymarket 账户真实的 USDC 余额"""
        try:
            resp = self.client.get_balance_allowance(asset_type="collateral")
            return float(resp.get("balance", 0))
        except: return 0.0

    async def execute_reversal_trade(self, coin, market_id, original_dir):
        """执行最后 1 分钟反转逻辑"""
        try:
            # 获取市场倒计时
            market_data = self.client.get_market(market_id)
            end_time = market_data.get('expiration_timestamp')
            rem_time = end_time - time.time()

            # 只有在最后 65 秒且未交易过时触发
            if 0 < rem_time <= REVERSAL_WINDOW and market_id not in self.history:
                # 反转：原预测“涨”则买“NO”，原预测“跌”则买“YES”
                outcome = "NO" if original_dir == "涨" else "YES"
                
                logger.info(f"🔥 {coin} 触发反转! 剩余 {int(rem_time)}s | 购买: {outcome}")
                
                # 执行市价单买入
                order = self.client.create_order(
                    market_id=market_id,
                    amount=BET_AMOUNT,
                    outcome=outcome,
                    side="BUY",
                    order_type="MARKET"
                )
                
                if order.get("success"):
                    self.history.add(market_id)
                    await self.send_tg(f"✅ *反转下单成功*\n币种: `{coin}`\n方向: `{outcome}`\n剩余时间: `{int(rem_time)}s`")
                    return True
        except Exception as e:
            logger.error(f"{coin} 执行出错: {e}")
        return False

    async def run(self):
        balance = await self.get_real_balance()
        logger.info(f"✅ 初始化成功 | 实时资金: {balance} USDC")
        await self.send_tg(f"🚀 *龙虾实盘已激活*\n当前资金: `{balance}` USDC\n监控币种: `7个` | 策略: `最后1分反转`")

        while True:
            # 每 10 秒轮询一次所有币种的倒计时
            for coin, cfg in MARKETS.items():
                await self.execute_reversal_trade(coin, cfg['id'], cfg['original'])
            
            # 每小时清理一次历史记录，防止内存堆积，并确保新周期的 Condition ID 能被识别
            if int(time.time()) % 3600 < 10:
                self.history.clear()
                new_bal = await self.get_real_balance()
                await self.send_tg(f"ℹ️ *小时巡检*\n当前余额: `{new_bal}` USDC")

            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = LobsterPolyBot()
    asyncio.run(bot.run())
