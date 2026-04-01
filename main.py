import asyncio
import time
import logging
from datetime import datetime
import aiohttp
from py_polymarket_sdk import ClobClient

# ==========================================
# 🔑 1. 核心凭证 (直接在这里填入你的信息)
# ==========================================
TG_TOKEN = "8337472418:AAFu_X3_Dsgru-H04X0MRnuZ1efW0pZpbBc"
TG_CHAT_ID = "8206453731"

POLY_CONFIG = {
    "key": "这里填入_POLY_API_KEY",
    "secret": "这里填入_POLY_SECRET",
    "passphrase": "这里填入_POLY_PASSPHRASE",
    "private_key": "这里填入_你的钱包私钥_0x...", # 必须包含 0x 前缀
    "host": "https://clob.polymarket.com"
}

# ==========================================
# 🦞 2. 策略参数 (7币监测 + 最后1分反转)
# ==========================================
BET_AMOUNT = 1.0        # 每笔 1U
REVERSAL_WINDOW = 60    # 最后 60 秒触发反转
CHECK_INTERVAL = 10     # 每 10 秒扫描一次所有市场

# 7个币种监测 (Condition ID 需在 Polymarket 官网 5分钟盘实时获取)
MARKETS = {
    "BTC":  {"id": "这里填入_BTC_ID", "predict": "涨"},
    "ETH":  {"id": "这里填入_ETH_ID", "predict": "涨"},
    "XRP":  {"id": "这里填入_XRP_ID", "predict": "涨"},
    "BNB":  {"id": "这里填入_BNB_ID", "predict": "跌"},
    "DOGE": {"id": "这里填入_DOGE_ID", "predict": "涨"},
    "SOL":  {"id": "这里填入_SOL_ID", "predict": "涨"},
    "HYPE": {"id": "这里填入_HYPE_ID", "predict": "涨"}
}

# ==========================================
# 🤖 3. 机器人核心引擎
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LobsterPolyReal")

class LobsterPolyBot:
    def __init__(self):
        self.client = ClobClient(
            POLY_CONFIG["host"], 
            key=POLY_CONFIG["key"], 
            secret=POLY_CONFIG["secret"], 
            passphrase=POLY_CONFIG["passphrase"], 
            private_key=POLY_CONFIG["private_key"]
        )
        self.history = set()

    async def send_tg(self, msg):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
            except Exception as e:
                logger.error(f"TG 发送失败: {e}")

    async def get_balance(self):
        """实时获取 Polymarket 账户 USDC 余额"""
        try:
            resp = self.client.get_balance_allowance(asset_type="collateral")
            return float(resp.get("balance", 0))
        except: return 0.0

    async def run(self):
        # 初始化同步
        balance = await self.get_balance()
        logger.info(f"✅ 系统初始化成功 | 初始资金: {balance} USDC")
        await self.send_tg(f"🚀 *龙虾实盘已激活*\n当前资金: `{balance}` USDC\n模式: `7币反转实操` | 1U/笔")

        while True:
            for coin, cfg in MARKETS.items():
                # 跳过未填 ID 的占位符
                if "这里填入" in cfg['id']: continue 
                
                try:
                    # 获取该市场详情
                    m = self.client.get_market(cfg['id'])
                    # 获取截止时间戳
                    end_time = m.get('expiration_timestamp') or m.get('end_time')
                    if not end_time: continue
                    
                    rem_time = float(end_time) - time.time()

                    # 核心：最后 60 秒触发反转买入
                    if 0 < rem_time <= REVERSAL_WINDOW and cfg['id'] not in self.history:
                        # 【反转逻辑】：原预测“涨”则买“NO”，反之买“YES”
                        outcome = "NO" if cfg['predict'] == "涨" else "YES"
                        
                        logger.info(f"🔥 {coin} 进入反转窗口! 剩余 {int(rem_time)}s")
                        
                        # 执行 1U 市价单
                        order = self.client.create_order(
                            market_id=cfg['id'], 
                            amount=BET_AMOUNT, 
                            outcome=outcome, 
                            side="BUY", 
                            order_type="MARKET"
                        )
                        
                        if order.get("success") or order.get("orderID"):
                            self.history.add(cfg['id'])
                            await self.send_tg(f"✅ *反转下单成功*\n币种: `{coin}`\n方向: `{outcome}`\n剩余: `{int(rem_time)}s`")
                except Exception as e:
                    logger.debug(f"{coin} 扫描中: {e}")
            
            # 每 5 分钟（300秒）重置一次历史记录，针对 5 分钟盘循环
            if int(time.time()) % 300 < 10:
                self.history.clear()
                cur_bal = await self.get_balance()
                logger.info(f"周期同步 | 当前余额: {cur_bal} USDC")

            await asyncio.sleep(CHECK_INTERVAL) # 10 秒轮询一次

if __name__ == "__main__":
    bot = LobsterPolyBot()
    asyncio.run(bot.run())
