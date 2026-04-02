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

# 日志配置 - 调高级别以便调试
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("LobsterBot")

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

# 监控配置 (Event ID 需保持最新)
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
SIGNAL_WINDOW = 3600    # 修改：距离结束 1 小时内即触发 (方便测试)
MAX_CONSEC_LOSS = 3     # 连亏风控

# 全局状态
stats = {coin: {"trades": 0, "consec_loss": 0} for coin in COINS}
executed_ids = set()

class PolymarketBot:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self):
        if not CONFIG["PK"] or not CONFIG["API_KEY"]:
            logger.error("❌ 环境变量 PK 或 API_KEY 未配置！请检查 Railway Variables")
            return None
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
        if not CONFIG["TG_TOKEN"] or not CONFIG["CHAT_ID"]:
            logger.warning("⚠️ 未配置 TG_TOKEN 或 CHAT_ID，跳过消息发送")
            return
        
        # --- 彻底修复：Line 89 语法错误已消除 ---
        url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
        payload = {
            "chat_id": CONFIG["CHAT_ID"], 
            "text": f"🦞 【系统通知】\n{text}", 
            "parse_mode": "Markdown"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error(f"TG 发送失败，状态码: {resp.status}")
            except Exception as e:
                logger.error(f"TG 请求异常: {e}")

    async def execute_trade(self, coin, token_id):
        if stats[coin]["consec_loss"] >= MAX_CONSEC_LOSS:
            logger.warning(f"🛑 {coin} 达到连亏上限，停止交易")
            return False

        try:
            # 这里的 price=0.99 代表愿意以最高 0.99 价格买入 (几乎必成)
            order_args = OrderArgs(price=0.99, size=BET_AMOUNT, side="BUY", token_id=token_id)
            signed_order = self.client.create_order(order_args)
            resp = self.client.post_order(signed_order)

            if resp and resp.get("success"):
                stats[coin]["trades"] += 1
                await self.send_tg(f"✅ *下单成功* | {coin}\n订单ID: `{resp.get('orderID')}`")
                return True
            else:
                logger.error(f"❌ 下单拒绝: {resp}")
                await self.send_tg(f"❌ *下单失败* | {coin}\n原因: `{resp}`")
        except Exception as e:
            logger.error(f"⚠️ 交易执行异常: {e}")
        return False

    async def monitor_market(self, coin, info):
        logger.info(f"📡 启动 {coin} 监控 (ID: {info['id']})")
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    # 抓取市场信息
                    api_url = f"https://gamma-api.polymarket.com/events/{info['id']}"
                    async with session.get(api_url) as r:
                        if r.status != 200:
                            await asyncio.sleep(30)
                            continue
                        
                        data = await r.json()
                        if not data.get('markets'): continue
                        
                        market = data['markets'][0]
                        end_ts = datetime.fromisoformat(market['endsAt'].replace('Z', '+00:00')).timestamp()
                        token_ids = json.loads(market['clobTokenIds'])
                        time_left = end_ts - time.time()

                        # 触发逻辑
                        if 0 < time_left <= SIGNAL_WINDOW and info['id'] not in executed_ids:
                            logger.info(f"⚡ {coin} 进入结算窗口 (剩余 {int(time_left)}s)，准备执行")
                            # 根据 side 选择 Yes(0) 或 No(1)
                            target_token = token_ids[0] if info['side'] == "涨" else token_ids[1]
                            success = await self.execute_trade(coin, target_token)
                            if success:
                                executed_ids.add(info['id'])

            except Exception as e:
                logger.debug(f"轮询 {coin} 异常 (可能网络波动): {e}")
            
            await asyncio.sleep(15) # 15秒轮询一次

    async def start(self):
        logger.info("🚀 机器人正在启动...")
        if not self.client:
            return

        # 启动即发通知，确认电报连接正常
        await self.send_tg("🤖 *机器人已启动并成功连接 Polymarket API*")
        
        # 创建监控任务
        tasks = [self.monitor_market(c, i) for c, i in COINS.items()]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    bot = PolymarketBot()
    try:
        asyncio.run(bot.start())
    except Exception as e:
        logger.critical(f"程序崩溃: {e}")
