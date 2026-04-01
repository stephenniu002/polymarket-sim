import asyncio
import os
import time
import logging
import requests
import aiohttp
from py_polymarket_sdk import ClobClient

# ==========================================
# 🔑 1. 核心凭证 (请务必填入你的真实信息)
# ==========================================
# 建议在 Railway Variables 填入，或者直接在这里硬编码替换引号内容
TG_TOKEN = "8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY"
TG_CHAT_ID = "5739995837"

POLY_CONFIG = {
    "key": "这里填入_API_KEY",
    "secret": "这里填入_API_SECRET",
    "passphrase": "这里填入_PASSPHRASE",
    "private_key": "这里填入_钱包私钥_0x...", 
    "host": "https://clob.polymarket.com"
}

# ==========================================
# 📊 2. 7币监测配置 (Event ID 是链接末尾的数字)
# ==========================================
RAW_EVENTS = {
    "ETH":  {"event_id": "1775053500", "predict": "涨"},
    "BTC":  {"event_id": "填入你的BTC数字", "predict": "涨"},
    "XRP":  {"event_id": "填入你的XRP数字", "predict": "涨"},
    "BNB":  {"event_id": "填入你的BNB数字", "predict": "跌"},
    "DOGE": {"event_id": "填入你的DOGE数字", "predict": "涨"},
    "SOL":  {"event_id": "填入你的SOL数字", "predict": "涨"},
    "HYPE": {"id": "填入你的HYPE数字", "predict": "涨"}
}

BET_AMOUNT = 1.0        # 每笔 1U
REVERSAL_WINDOW = 60    # 最后 60 秒触发反转
CHECK_INTERVAL = 10     # 每 10 秒轮询一次

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
        self.real_markets = {}

    async def send_tg(self, msg):
        if "这里填入" in TG_TOKEN: return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            try: await session.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
            except: pass

    def sync_condition_ids(self):
        """自动抓取 Event 对应的 Condition ID"""
        for coin, cfg in RAW_EVENTS.items():
            if "填入" in cfg['event_id']: continue
            try:
                # 访问 Gamma API 获取市场详情
                url = f"https://gamma-api.polymarket.com/events/{cfg['event_id']}"
                resp = requests.get(url, timeout=10).json()
                markets = resp.get("markets", [])
                if markets:
                    c_id = markets[0].get("conditionId")
                    end_time = markets[0].get("endsAt") # ISO格式时间
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
            resp = self.client.get_balance_allowance(asset_type="collateral")
            return float(resp.get("balance", 0))
        except: return 0.0

    async def run(self):
        self.sync_condition_ids()
        balance = await self.get_balance()
        
        logger.info(f"🚀 系统启动 | 初始资金: {balance} USDC")
        await self.send_tg(f"🦞 *实盘启动成功*\n当前资金: `{balance}` USDC\n监测币种: `{len(self.real_markets)}个`")

        while True:
            for coin, data in self.real_markets.items():
                rem_time = data['end_ts'] - time.time()

                # 核心：最后 60 秒触发反转
                if 0 < rem_time <= REVERSAL_WINDOW and data['id'] not in self.history:
                    # 原预测涨 -> 反转买 NO；原预测跌 -> 反转买 YES
                    outcome = "NO" if data['predict'] == "涨" else "YES"
                    
                    try:
                        logger.info(f"🔥 {coin} 触发反转! 剩余 {int(rem_time)}s")
                        order = self.client.create_order(
                            market_id=data['id'], 
                            amount=BET_AMOUNT, 
                            outcome=outcome, 
                            side="BUY", 
                            order_type="MARKET"
                        )
                        if order.get("success") or order.get("orderID"):
                            self.history.add(data['id'])
                            await self.send_tg(f"✅ *下单成功*\n币种: `{coin}`\n方向: `{outcome}`\n剩余时间: `{int(rem_time)}s`")
                    except Exception as e:
                        logger.error(f"下单失败: {e}")

            # 每 5 分钟尝试刷新一次 Condition ID (针对循环开盘的 5min 盘)
            if int(time.time()) % 300 < 15:
                self.sync_condition_ids()
                self.history.clear() # 清理上一轮成交记录
                
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = LobsterPolyBot()
    asyncio.run(bot.run())
