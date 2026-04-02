import os
import sys
import subprocess
import time

# --- 阶段 1: 强制路径与自动修复环境 ---
venv_path = "/app/.venv/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

try:
    from clob_client.client import ClobClient
    from clob_client.clob_types import OrderArgs
except ImportError:
    print("⚠️ 检测到环境缺失，正在执行强制安装并覆盖...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "--upgrade", "--target", venv_path, 
        "py-clob-client==0.34.6", "aiohttp", "python-dotenv", "eth-account"
    ])
    print("✅ 安装完成，正在强制重启程序以激活环境...")
    # 核心：重启进程，清理 Python 的导入缓存
    os.execv(sys.executable, ['python'] + sys.argv)

# --- 阶段 2: 正常导入交易库 ---
import asyncio
import json
import logging
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# --- 阶段 3: 核心配置 ---
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

# --- 阶段 4: Telegram 报告逻辑 ---
async def send_tg_msg(text):
    url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
    payload = {"chat_id": CONFIG['CHAT_ID'], "text": text, "parse_mode": "Markdown"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"TG 发送失败: {e}")

# --- 阶段 5: 尾盘扫描与下单逻辑 ---
async def run_bot():
    account = Account.from_key(CONFIG["PK"])
    client = ClobClient(CONFIG["CLOB
