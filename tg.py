import os
import requests
import logging

# 直接读取 Railway 界面上你配置好的变量
TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    """通用的 TG 发送函数，不再依赖 config.py"""
    if not TOKEN or not CHAT_ID:
        logging.warning("⚠️ TG 配置缺失（TG_TOKEN 或 TELEGRAM_CHAT_ID），消息未发送")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            logging.error(f"❌ TG 发送失败: {resp.text}")
    except Exception as e:
        logging.error(f"❌ TG 连接异常: {e}")
