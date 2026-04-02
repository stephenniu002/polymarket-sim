import asyncio
import os
import time
import logging
import requests
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

# 核心库导入 (确保 requirements.txt 中包含 py-clob-client)
try:
    from clob_client.client import ClobClient
    from clob_client.clob_types import OrderArgs
except ImportError:
    print("❌ 运行环境缺失 py-clob-client，请检查 Railway 构建日志")

# 加载环境变量
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LobsterReal")

# ==========================================
# 🔑 1. 配置参数 (请在 Railway Variables 填入)
# ==========================================
CONFIG = {
    "PK": os.getenv("PK"), # 钱包私钥，必须 0x 开头
    "API_KEY": os.getenv("POLY_API_KEY"),
    "API_SECRET": os.getenv("POLY_SECRET"),
    "API_PASSPHRASE": os.getenv("POLY_PASSPHRASE"),
    "TG_TOKEN": os.getenv("TELEGRAM_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "POLY_HOST": "https://clob.polymarket.com",
    "CHAIN_ID": 137
}

# 监测的目标事件 ID (请去 Polymarket 官网获取真实的数字 ID 填入)
MONITOR_EVENTS = {
    "BTC":  {"event_id": "填入数字", "predict": "涨"},
    "ETH":  {"event_id": "填入数字", "predict": "涨"},
    "SOL":  {"event_id": "填入数字", "predict": "涨"},
    "XRP":  {"event_id": "填入数字", "predict": "涨"},
    "DOGE": {"event_id": "填入数字", "predict": "涨"},
    "BNB":  {"event_id": "填入数字", "predict": "跌"},
    "HYPE": {"event_id": "填入数字", "predict": "涨"}
}

BET_AMOUNT = 1.0        # 每单下单金额 (USDC)
WINDOW_SECONDS = 60     # 倒计时 60 秒内触发
CHECK_INTERVAL = 10     # 轮询频率 (秒)

class PolymarketRealBot:
    def __init__(self):
        self.client = self._init_client()
        self.active_markets = {}
        self.executed_history = set()

    def _init_client(self):
        """初始化 Polymarket 实盘客户端"""
        try:
            if not CONFIG["PK"] or not CONFIG["API_KEY"]:
                logger.error("❌ 环境变量缺失，请在 Railway Variables 填入 PK/API_KEY 等")
                return None
            
            # 2026 SDK 规范：key 为 L1 私钥，api_key 等为 L2 凭据
            client = ClobClient(
                host=CONFIG["POLY_HOST"],
                key=CONFIG["PK"],
                chain_id=CONFIG["CHAIN_ID"],
                api_key=CONFIG["API_KEY"],
                api_secret=CONFIG["API_SECRET"],
                api_passphrase=CONFIG["API_PASSPHRASE"]
            )
            logger.info("🟢 Polymarket 实盘鉴权连接成功")
            return client
        except Exception as e:
            logger.error(f"❌ 客户端初始化失败: {e}")
            return None

    async def send_tg(self, text):
        """发送 Telegram 消息 (已修复断行语法错误)"""
        if not CONFIG["TG_TOKEN"] or not CONFIG["CHAT_ID"]:
            return
        
        # 修正：确保 URL 在一行内，不产生 SyntaxError
        url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
        payload = {
            "chat_id": CONFIG["CHAT_ID"], 
            "text": f"🤖 {text}", 
            "parse_mode": "Markdown"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(url, json=payload, timeout=10)
            except Exception as e:
                logger.error(f"TG 通知发送失败: {e}")

    def refresh_markets(self):
        """同步 7 币种的市场 Token 数据"""
        logger.info("🔄 正在同步市场数据...")
        for coin, info in MONITOR_EVENTS.items():
            eid = info["event_id"]
            if not eid or "填入" in str(eid): 
                continue
            
            try:
                # 获取事件详情
                url = f"https://gamma-api.polymarket.com/events/{eid}"
                resp = requests.get(url, timeout=15).json()
                markets = resp.get("markets", [])
                if not markets: continue

                # 获取 Token ID (Yes/No)
                raw_tokens = markets[0].get("clobTokenIds", "[]")
                token_ids = json.loads(raw_tokens)
                
                if len(token_ids) >= 2:
                    end_time_str = markets[0].get("endsAt")
                    # 时间转换
                    end_ts = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')).timestamp()
                    
                    self.active_markets[coin] = {
                        "yes_token": token_ids[0],
                        "no_token": token_ids[1],
                        "predict": info["predict"],
                        "end_ts": end_ts,
                        "event_id": eid
                    }
                    logger.info(f"✅ 挂载成功: {coin} | ID: {eid}")
            except Exception as e:
                logger.error(f"❌ 同步 {coin} (ID: {eid}) 失败: {e}")

    async def run(self):
        """核心主循环"""
        if not self.client: 
            logger.error("🛑 客户端未就绪，停止运行")
            return
        
        self.refresh_markets()
        await self.send_tg("🚀 *Polymarket 实盘监控已启动*\n状态：正在轮询 7 币种尾部信号")

        while True:
            now = time.time()
            
            for coin, mkt in self.active_markets.items():
                time_left = mkt["end_ts"] - now
                
                # 触发逻辑：进入倒计时窗口且未交易过
                if 0 < time_left <= WINDOW_SECONDS and mkt["event_id"] not in self.executed_history:
                    # 确定买入目标 (涨买Yes, 跌买No)
                    target_token = mkt["yes_token"] if mkt["predict"] == "涨" else mkt["no_token"]
                    
                    logger.info(f"🔥 {coin} 触发倒计时信号! 剩余 {int(time_left)}s，执行下单...")
                    
                    try:
                        # 2026 SDK 下单封装
                        order_args = OrderArgs(
                            price=0.99, # 接近 1.0 的价格确保成交
                            size=BET_AMOUNT,
                            side="BUY",
                            token_id=target_token
                        )
                        signed_order = self.client.create_order(order_args)
                        resp = self.client.post_order(signed_order)
                        
                        if resp.get("success"):
                            self.executed_history.add(mkt["event_id"])
                            await self.send_tg(f"✅ *实盘下单成功*\n币种: `{coin}`\n方向: `{mkt['predict']}`\n订单ID: `{resp.get('orderID')}`")
                        else:
                            logger.error(f"❌ 下单拒绝: {resp}")
                    except Exception as e:
                        logger.error(f"❌ 交易系统崩溃: {e}")

            # 每 10 分钟自动重刷一次市场数据 (防止 ID 过期)
            if int(now) % 600 < CHECK_INTERVAL:
                self.refresh_markets()

            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    bot = PolymarketRealBot()
    asyncio.run(bot.run())
