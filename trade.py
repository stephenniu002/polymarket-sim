import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_lobster_client():
    # 极简初始化
    try:
        c = ClobClient(host="https://clob.polymarket.com")
    except:
        c = ClobClient()
    
    # 手动属性注入 (绕过构造函数检查)
    c.host = "https://clob.polymarket.com"
    c.key = os.getenv("POLY_API_KEY")
    c.api_key = os.getenv("POLY_API_KEY")
    c.secret = os.getenv("POLY_SECRET")
    c.api_secret = os.getenv("POLY_SECRET")
    c.passphrase = os.getenv("POLY_PASSPHRASE")
    c.api_passphrase = os.getenv("POLY_PASSPHRASE")
    c.private_key = os.getenv("PRIVATE_KEY")
    c.chain_id = POLYGON
    return c

client = get_lobster_client()

def execute_trade(symbol, token_id, side, price, strength):
    if not client:
        logging.error("❌ 机器人尚未就绪")
        return
    try:
        logging.info(f"📤 [TRADE] {symbol} 信号捕获 | side: {side} | 价格: {price}")
        # 这里可以使用你的 0xd962 地址执行下单逻辑
    except Exception as e:
        logging.error(f"❌ 交易执行异常: {e}")
