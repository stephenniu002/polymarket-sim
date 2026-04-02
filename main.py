import asyncio
import os
import time
import logging
import requests
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

# 核心库导入
try:
    from clob_client.client import ClobClient
    from clob_client.clob_types import OrderArgs
except ImportError:
    print("❌ 错误: 请确保 requirements.txt 中包含 py-clob-client")

# 加载环境变量
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LobsterBot")

# ==========================================
# 🔑 1. 配置参数 (从 Railway Variables 读取)
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

# 监测的目标事件 ID (需要去 Polymarket 官网获取真实的数字 ID)
# 示例 ID 仅供参考，请替换为你关注的 7 个币种 Event ID
MONITOR_EVENTS = {
    "BTC": {"event_id": "12345", "predict": "涨"},
    "ETH": {"event_id": "67890", "predict": "涨"},
    "SOL": {"event_id": "11223", "predict": "涨"},
    "XRP": {"event_id": "44556", "predict": "跌"},
    "DOGE": {"event_id": "77889", "predict": "涨"},
    "BNB": {"event_id": "99001", "predict": "涨"},
    "HYPE": {"event_id": "22334", "predict": "涨"}
}

BET_AMOUNT = 1.0        # 每单下单金额 (USDC)
WINDOW_SECONDS = 60    # 倒计时多少秒触发下单
CHECK_INTERVAL = 10     # 轮询频率 (秒)

class PolymarketBot:
    def __init__(self):
        self.client = self._init_client()
        self.active_markets = {}
        self.executed_history = set()

    def _init_client(self):
        """初始化 Polymarket CLOB 客户端"""
        try:
            if not CONFIG["PK"] or not CONFIG["API_KEY"]:
                logger.error("❌ 环境变量缺失，请检查 Railway Variables")
                return None
            
            client = ClobClient(
                host=CONFIG["POLY_HOST"],
                key=CONFIG["PK"],
                chain_id=CONFIG["CHAIN_ID"],
                api_key=CONFIG["API_KEY"],
                api_secret=CONFIG["API_SECRET"],
                api_passphrase=CONFIG["API_PASSPHRASE"]
            )
            logger.info("🟢 Polymarket 客户端鉴权成功")
            return client
        except Exception as e:
            logger.error(f"❌ 客户端初始化失败: {e}")
            return None

    async def send_tg(self, text):
        """发送 Telegram 消息"""
        if not CONFIG["TG_TOKEN"] or not CONFIG["CHAT_ID"]:
            return
        url = f"
