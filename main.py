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
BET_AMOUNT = 1.0        # 每笔投入 1 USDC
REVERSAL_WINDOW = 60    # 最后 60 秒进入“反转买入”
CHECK_INTERVAL = 10     # 每 10 秒扫描一次所有市场

# 目标市场配置 (Condition ID 需要你根据 Polymarket 官网 5分钟盘实时更新)
MARKETS = {
    "BTC":  {"id": "0x1...", "predict": "涨"},
    "ETH":  {"id": "0x2...", "predict": "涨"},
    "XRP":  {"id": "0x3...", "predict": "涨"},
    "BNB":  {"id": "0x4...", "predict": "跌"},
    "DOGE": {"id": "0x5...", "predict": "涨"},
    "SOL":  {"id": "0x6...", "predict": "涨"},
    "HYPE": {"id": "0x7...", "predict": "涨"}
}

class LobsterPolyBot:
    def __init__(self):
        # 初始化 Polymarket 客户端
        self.client = ClobClient(
            POLY_CONFIG["host"], 
            key=POLY_CONFIG["key"], 
            secret=POLY_CONFIG["secret"], 
            passphrase=POLY_CONFIG["passphrase"], 
            private_key=POLY_CONFIG["private_key"]
        )
        self.history = set()  # 防止同一周期重复下单

    async def send_tg(self, msg):
        if not TG_TOKEN or not TG_CHAT_ID:
            logger.warning("TG 配置缺失，仅本地打印日志")
            return
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
            except Exception as e:
                logger.error(f"TG 发送失败: {e}")

    async def get_real_balance(self):
        """获取 Polymarket 账户真实的 USDC 余额"""
        try:
            resp = self.client.get_balance_allowance(asset_type="collateral")
            # Polymarket 使用 USDC (Polygon 链)
            return float(resp.get("balance", 0))
        except Exception as e:
            logger.error(f"余额获取失败: {e}")
            return 0.0

    async def execute_reversal_trade(self, coin, market_id, original_predict):
        """执行最后 1 分钟反转逻辑"""
        try:
            # 获取市场倒计时 (从 SDK 获取市场详情)
            market_data = self.client.get_market(market_id)
            # 部分 SDK 版本使用 expiration_timestamp 或 end_time
            end_time = market_data.get('expiration_timestamp') or market_data.get('end_time')
            
            if not end_time: return
            
            rem_time = float(end_time) - time.time()

            # 只有在最后 60 秒且该市场本周期未交易过时触发
            if 0 < rem_time <= REVERSAL_WINDOW and market_id not in self.history:
                # 【反转逻辑】：原预测“涨”则买“NO”，原预测“跌”则买“
