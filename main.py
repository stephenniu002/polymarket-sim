import asyncio
import os
import json
import logging
import time
import aiohttp
from datetime import datetime

# 核心实盘库
try:
    from clob_client.client import ClobClient
    from clob_client.clob_types import OrderArgs
except ImportError:
    print("❌ 运行环境缺失 py-clob-client，请检查 Railway 构建日志")

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LobsterRealTime")

# ======================
# 🔑 配置与环境变量
# ======================
CONFIG = {
    "PK": os.getenv("PK"), # 必须 0x 开头
    "API_KEY": os.getenv("POLY_API_KEY"),
    "API_SECRET": os.getenv("POLY_SECRET"),
    "API_PASSPHRASE": os.getenv("POLY_PASSPHRASE"),
    "TG_TOKEN": os.getenv("TELEGRAM_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "POLY_HOST": "https://clob.polymarket.com",
    "CHAIN_ID": 137
}

# 监控配置 (请替换为真实的 Event ID)
COINS = {
    "BTC":  {"id": "71342", "side": "涨"},
    "ETH":  {"id": "82451", "side": "涨"},
    "SOL":  {"id": "93560", "side": "涨"},
    "XRP":  {"id": "10471", "side": "涨"},
    "DOGE": {"id": "11582", "side": "涨"},
    "BNB":  {"id": "12693", "side": "跌"},
    "HYPE": {"id": "13704", "side": "涨"}
}

# 交易参数
BET_AMOUNT = 1.0        # 每单金额 (USDC)
SIGNAL_WINDOW = 30      # 尾部 30 秒触发
MAX_CONSEC_LOSS = 3     # 连亏风控

# 全局状态
stats = {coin: {"balance": 0.0, "consec_loss": 0, "trades": 0} for coin in COINS}
executed_ids = set()

# ======================
# 🤖 核心功能模块
# ======================

class PolymarketBot:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self):
        try:
            return ClobClient(
                host=CONFIG["POLY_HOST"],
                key=CONFIG["PK"],
                chain_id=CONFIG["CHAIN_ID"],
                api_key=CONFIG["API_KEY"],
                api_secret=CONFIG["API_SECRET"],
                api_passphrase=CONFIG["API_PASSPHRASE"]
            )
        except Exception as e:
            logger.error(f"❌ 鉴权初始化失败: {e}")
            return None

    async def send_tg(self, text):
        if not CONFIG["TG_TOKEN"]: return
        url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
        payload = {"chat_id": CONFIG["CHAT_ID"], "text": f"🦞 {text}", "parse_mode": "Markdown"}
        async with aiohttp.ClientSession() as session:
            try: await session.post(url, json=payload, timeout=10)
            except: pass

    async def execute_trade(self, coin, token_id):
        """自动签名并执行下单"""
        if stats[coin]["consec_loss"] >= MAX_CONSEC_LOSS:
            logger.warning(f"🛑 {coin} 连亏触发停手")
            return

        try:
            order_args = OrderArgs(price=0.99, size=BET_AMOUNT, side="BUY", token_id=token_id)
            signed_order = self.client.create_order(order_args)
            resp = self.client.post_order(signed_order)

            if resp.get("success"):
                stats[coin]["trades"] += 1
                await self.send_tg(f"✅ *下单成功* | {coin}\n订单ID: `{resp.get('orderID')}`")
                return True
            else:
                logger.error(f"❌ 下单失败: {resp}")
        except Exception as e:
            logger.error(f"⚠️ 交易异常: {e}")
        return False

    async def monitor_market(self, coin, info):
        """多币种并发监测逻辑"""
        while True:
            try:
                # 获取市场实时状态 (Gamma API)
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://gamma-api.polymarket.com/events/{info['id']}") as r:
                        data = await r.json()
                        market = data['markets'][0]
                        end_ts = datetime.fromisoformat(market['endsAt'].replace('Z', '+00:00')).timestamp()
                        token_ids = json.loads(market['clobTokenIds'])
                        
                        # 计算倒计时
                        time_left = end_ts - time.time()
                        
                        # 信号触发：进入尾部 30 秒且未交易过
                        if 0 < time_left <= SIGNAL_WINDOW and info['id'] not in executed_ids:
                            target_token = token_ids[0] if info['side'] == "涨" else token_ids[1]
                            success = await self.execute_trade(coin, target_token)
                            if success: executed_ids.add(info['id'])

            except Exception as e:
                logger.debug(f"轮询 {coin} 异常: {e}")
            await asyncio.sleep(10) # 轮询间隔

    async def periodic_report(self):
        """定时汇报模块"""
        while True:
            await asyncio.sleep(3600) # 每小时
            msg = "📊 *每小时结算报告*\n"
            for coin, data in stats.items():
                msg += f"• {coin}: 成交 {data['trades']} 次 | 连亏 {data['consec_loss']}\n"
            await self.send_tg(msg)

    async def start(self):
        if not self.client: return
        await self.send_tg("🚀 *Polymarket 实盘机器人已上线*\n多币种并行监控中...")
        
        # 并发启动所有币种监听和汇报任务
        tasks = [self.monitor_market(c, i) for c, i in COINS.items()]
        tasks.append(self.periodic_report())
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    bot = PolymarketBot()
    asyncio.run(bot.start())
