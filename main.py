import asyncio
import os
import time
import logging
import requests
import aiohttp
from datetime import datetime
# 确保 requirements.txt 中是 py-clob-client
from clob_client.client import ClobClient
from clob_client.clob_types import OrderArgs

# ==========================================
# 🔑 1. 核心凭证 (优先从 Railway 环境变量读取)
# ==========================================
TG_TOKEN = os.getenv("TG_TOKEN", "你的TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "你的ID")

POLY_CONFIG = {
    "key": os.getenv("CLOB_API_KEY", "这里填入_API_KEY"),
    "secret": os.getenv("CLOB_SECRET", "这里填入_API_SECRET"),
    "passphrase": os.getenv("CLOB_PASSPHRASE", "这里填入_PASSPHRASE"),
    "private_key": os.getenv("PRIVATE_KEY", "这里填入_钱包私钥_0x..."), 
    "host": "https://clob.polymarket.com",
    "chain_id": 137  # Polygon Mainnet
}

# ==========================================
# 📊 2. 7币监测配置 (请替换为真实的 Event ID)
# ==========================================
RAW_EVENTS = {
    "ETH":  {"event_id": "1775053500", "predict": "涨"},
    "BTC":  {"event_id": "这里填入ID", "predict": "涨"},
    "XRP":  {"event_id": "这里填入ID", "predict": "涨"},
    "BNB":  {"event_id": "这里填入ID", "predict": "跌"},
    "DOGE": {"event_id": "这里填入ID", "predict": "涨"},
    "SOL":  {"event_id": "这里填入ID", "predict": "涨"},
    "HYPE": {"event_id": "这里填入ID", "predict": "涨"} 
}

BET_AMOUNT = 1.0        # 下单金额 (USDC)
REVERSAL_WINDOW = 60    # 倒计时 60 秒触发
CHECK_INTERVAL = 10     # 轮询间隔

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("LobsterPolyReal")

class LobsterPolyBot:
    def __init__(self):
        try:
            # 2026 SDK 修正：初始化时 private_key 对应参数名为 key
            self.client = ClobClient(
                host=POLY_CONFIG["host"], 
                key=POLY_CONFIG["private_key"], # 这里是 L1 签名用的私钥
                chain_id=POLY_CONFIG["chain_id"],
                api_key=POLY_CONFIG["key"],     # 这里的 key 是 API Key
                api_secret=POLY_CONFIG["secret"],
                api_passphrase=POLY_CONFIG["passphrase"]
            )
            logger.info("🟢 客户端初始化并鉴权成功")
        except Exception as e:
            logger.error(f"❌ 客户端初始化失败: {e}")
            self.client = None
            
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
        """自动从 Gamma API 抓取 Condition ID 和 对应 Token ID"""
        for coin, cfg in RAW_EVENTS.items():
            if "填入" in str(cfg['event_id']): continue
            try:
                url = f"https://gamma-api.polymarket.com/events/{cfg['event_id']}"
                resp = requests.get(url, timeout=10).json()
                markets = resp.get("markets", [])
                if markets:
                    # 提取 Token ID (Yes/No)
                    # 2026 规范：clobTokenIds 列表 [Yes_Token_ID, No_Token_ID]
                    token_ids = json.loads(markets[0].get("clobTokenIds", "[]"))
                    end_time = markets[0].get("endsAt") 
                    
                    self.real_markets[coin] = {
                        "token_ids": token_ids
