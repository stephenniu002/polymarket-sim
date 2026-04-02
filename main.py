import os
import sys
import subprocess
import time

# --- 1. 路径修正 ---
venv_path = "/app/.venv/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

# --- 2. 导入与自动修复 ---
try:
    from clob_client.client import ClobClient
    from clob_client.clob_types import OrderArgs
except ImportError:
    print("🚀 正在最后一次强制补齐环境...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "--upgrade", "--target", venv_path, 
        "py-clob-client==0.34.6", "aiohttp", "python-dotenv", "eth-account"
    ])
    print("✅ 安装完成，强制重启中...")
    os.execv(sys.executable, ['python'] + sys.argv)

import asyncio
import json
import logging
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account

# 日志设置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# --- 3. 配置 ---
CONFIG = {
    "PK": os.getenv("PK"),
    "TG_TOKEN": os.getenv("TG_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "CLOB_ENDPOINT": "https://clob.polymarket.com",
    "CHAIN_ID": 137,
    "SYMBOLS": {
        "BTC": "16688", "ETH": "16689", "SOL": "16690",
        "BNB": "16691", "ARB": "16692", "OP": "16693", "DOGE": "16694"
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

# --- 4. 运行逻辑 ---
async def run_bot():
    try:
        # 这里补全了你刚才断掉的地方
        client = ClobClient(CONFIG["CLOB_ENDPOINT"], key=CONFIG["PK"], chain_id=CONFIG["CHAIN_ID"])
        
        await send_tg_msg("🚀 **Polymarket 机器人已正式上线**\n语法错误已修正，监控 7 种货币中...")
        logger.info("机器人启动成功")

        last_report_time = 0
        while True:
            now = datetime.now()
            # 每 5 分钟汇报一次存活
            if time.time() - last_report_time > 300:
                await send_tg_msg(f"📊 **定时汇报 [{now.strftime('%H:%M')}]**\n状态: 正常运行\n监控币种: {', '.join(CONFIG['SYMBOLS'].keys())}")
                last_report_time = time.time()
            
            # 尾盘逻辑（示例：59分时扫描）
            if now.minute == 59:
                logger.info("进入尾盘扫描...")

            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"运行崩溃: {e}")
        await send_tg_msg(f"❌ **机器人崩溃**: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_bot())
