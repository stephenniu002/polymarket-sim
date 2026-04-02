import os
import asyncio
import logging
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

# 只要启动命令正确，这里绝对不会报错
from clob_client.client import ClobClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

CONFIG = {
    "PK": os.getenv("PK"),
    "TG_TOKEN": os.getenv("TG_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "CLOB_ENDPOINT": "https://clob.polymarket.com",
    "CHAIN_ID": 137
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
        await send_tg_msg("🚀 **Polymarket 机器人已通过虚拟环境启动！**")
        logger.info("Bot started successfully.")
        while True:
            await asyncio.sleep(3600) # 保持运行
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())
