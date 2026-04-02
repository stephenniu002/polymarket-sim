import os
import sys

# --- 核心修复：强制锁定 Railway 虚拟环境路径 ---
# 无论 Railway 怎么变，我们把库可能在的地方都塞进搜索路径
possible_paths = [
    "/app/.venv/lib/python3.11/site-packages",
    "/app/.venv/lib/python3.12/site-packages",
    "/home/railway/.local/lib/python3.11/site-packages",
    os.path.join(os.getcwd(), ".venv/lib/python3.11/site-packages")
]

for path in possible_paths:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# 现在尝试导入，如果还是不行，说明构建有问题
try:
    from clob_client.client import ClobClient
    print("✅ 环境修复成功！成功导入 ClobClient")
except ImportError as e:
    print(f"❌ 依然找不到库。当前 sys.path: {sys.path}")
    raise e

import asyncio
import logging
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

# 日志与配置
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
        await send_tg_msg("🚀 **Polymarket 机器人已绕过环境限制成功启动**")
        logger.info("启动成功")
        
        while True:
            # 保持运行
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"运行时异常: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())
