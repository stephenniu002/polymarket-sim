import os
import asyncio
import logging
import aiohttp
import time
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account
# 尝试导入，如果失败会直接抛出错误让 Railway 停止
from clob_client.client import ClobClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

CONFIG = {
    "PK": os.getenv("PK"),
    "TG_TOKEN": os.getenv("TG_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "CLOB_ENDPOINT": "https://clob.polymarket.com",
    "CHAIN_ID": 137,
    "SYMBOLS": {
        "BTC": "16688", "ETH": "16689", "SOL": "16690"
    }
}

async def send_tg_msg(text):
    url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
    payload = {"chat_id": CONFIG['CHAT_ID'], "text": text, "parse_mode": "Markdown"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"TG 发送失败: {e}")

async def run_bot():
    try:
        client = ClobClient(CONFIG["CLOB_ENDPOINT"], key=CONFIG["PK"], chain_id=CONFIG["CHAIN_ID"])
        await send_tg_msg("🚀 **Polymarket 实盘机器人启动成功**")
        
        while True:
            # 你的核心逻辑...
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"异常: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())
