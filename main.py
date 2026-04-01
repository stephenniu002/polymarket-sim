import asyncio
import os
import time
import logging
import requests
import aiohttp
from datetime import datetime
# 注意：请确保 requirements.txt 中是 py-clob-client
from clob_client.client import ClobClient 

# ==========================================
# 🔑 1. 核心凭证 (优先从 Railway 环境变量读取)
# ==========================================
TG_TOKEN = os.getenv("TG_TOKEN", "8526469896:AAF7oUK3TjEa0Z3KDnwMy7QYqho45MhY")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "57395837")

POLY_CONFIG = {
    "key": os.getenv("CLOB_API_KEY", "这里填入_API_KEY"),
    "secret": os.getenv("CLOB_SECRET", "这里填入_API_SECRET"),
    "passphrase": os.getenv("CLOB_PASSPHRASE", "这里填入_PASSPHRASE"),
    "private_key": os.getenv("PRIVATE_KEY", "这里填入_钱包私钥_0x..."), 
    "host": "https://clob.polymarket.com"
}

# ==========================================
# 📊 2. 7币监测配置
# ==========================================
RAW_EVENTS = {
    "ETH":  {"event_id": "1775053500", "predict": "涨"},
    "BTC":  {"event_id": "填入你的BTC数字", "predict": "涨"},
    "XRP":  {"event_id": "填入你的XRP数字", "predict": "涨"},
    "BNB":  {"event_id": "填入你的BNB数字", "predict": "跌"},
    "DOGE": {"event_id": "填入你的DOGE数字", "predict": "涨"},
    "SOL":  {"event_id": "填入你的SOL数字", "predict": "涨"},
    "HYPE": {"event_id": "填入你的HYPE数字", "predict": "涨"} # 修正了 key 名从 id 变为 event_id
}

BET_AMOUNT = 1.0        
REVERSAL_WINDOW = 60    
CHECK_INTERVAL = 10     

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LobsterPolyReal")

class LobsterPolyBot:
    def __init__(self):
        # 初始化客户端
        try:
            self.client = ClobClient(
                POLY_CONFIG["host"], 
                key=POLY_CONFIG["key"], 
                secret=POLY_CONFIG["secret"], 
                passphrase=POLY_CONFIG["passphrase"], 
                private_key=POLY_CONFIG["private_key"]
            )
            # 设置 L2 衍生品身份验证
            self.client.set_api_creds(POLY_CONFIG["key"], POLY_CONFIG["secret"], POLY_CONFIG["passphrase"])
        except Exception as e:
            logger.error(f"❌ 客户端初始化失败: {e}")
            
        self.history = set()
        self.real_markets = {}

    async def send_tg(self, msg):
        if "这里填入" in TG_TOKEN or not TG_TOKEN: 
            logger.warning("TG 配置缺失，仅本地打印日志")
            return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            try: 
                await session.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
            except Exception as e: 
                logger.error(f"TG 发送失败: {e}")

    def sync_condition_ids(self):
        """自动抓取 Event 对应的 Condition ID"""
        for coin, cfg in RAW_EVENTS.items():
            if "填入" in str(cfg['event_id']): continue
            try:
                url = f"https://gamma-api.polymarket.com/events/{cfg['event_id']}"
                resp = requests.get(url, timeout=10).json()
                markets = resp.get("markets", [])
                if markets:
                    # 2026 版建议使用 conditionId 或 market_token_id
                    c_id = markets[0].get("conditionId")
                    end_time = markets[0].get("endsAt") 
                    self.real_markets[coin] = {
                        "id": c_id, 
                        "predict": cfg['predict'],
                        "end_ts": datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp()
                    }
                    logger.info(f"✅ 已挂载 {coin} | ID: {c_id[:10]}...")
            except Exception as e:
                logger.error(f"❌ 抓取 {coin} ID 失败: {e}")

    async def get_balance(self):
        """获取真实 USDC 余额"""
        try:
            # 2026 SDK 修复：直接获取可用余额
            resp = self.client.get_balance() 
            # 这里的返回值通常是一个字典，包含多种资产，需提取 collateral
            return float(resp.get("balance", 0))
        except Exception as e:
            logger.debug(f"余额获取细节: {e}")
            return 0.0

    async def run(self):
        self.sync_condition_ids()
        balance = await self.get_balance()
        
        logger.info(f"🚀 系统启动 | 初始资金: {balance} USDC")
        await self.send_tg(f"🦞 *实盘启动成功*\n当前资金: `{balance}` USDC\n监测币种: `{len(self.real_markets)}个`")

        while True:
            now = time.time()
            for coin, data in self.real_markets.items():
                rem_time = data['end_ts'] - now

                if 0 < rem_time <= REVERSAL_WINDOW and data['id'] not in self.history:
                    outcome = "1" if data['predict'] == "跌" else "0" # 修正：SDK下单通常用 0(Yes) 1(No)
                    
                    try:
                        logger.info(f"🔥 {coin} 触发反转! 剩余 {int(rem_time)}s")
                        # 2026版市场价下单通常需要通过 create_market_order
                        order = self.client.create_order(
                            vmin_price=0.1, # 设定一个保底成交价
                            price=0.99, 
                            market_id=data['id'], 
                            amount=BET_AMOUNT, 
                            outcome=outcome, 
                            side="BUY"
                        )
                        if order.get("success"):
                            self.history.add(data['id'])
                            await self.send_tg(f"✅ *下单成功*\n币种: `{coin}`\n方向: `{outcome}`\n剩余时间: `{int(rem_time)}s`")
                    except Exception as e:
                        logger.error(f"下单失败: {e}")

            # 每 5 分钟刷新一次
            if int(now) % 300 < 15:
                self.sync_condition_ids()
                self.history.clear() 
                
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = LobsterPolyBot()
    asyncio.run(bot.run())
