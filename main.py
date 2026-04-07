import os
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_tg_message(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def run_lobster_real_deal():
    logger.info("🚀 [Lobster] 启动 2026 实战注入模式...")
    # 自动适配私钥环境变量
    PK = os.getenv("FOX_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
    
    if not PK:
        logger.error("❌ 未找到私钥，请检查 Railway Variables")
        return

    try:
        # 初始化 0.34.6 客户端
        client = ClobClient("https://clob.polymarket
