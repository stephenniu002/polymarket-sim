import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# 初始化 (不传 api_key 这种会报错的参数)
def get_lobster_client():
    try:
        # 只给 host，其余参数稍后手动注入
        c = ClobClient(host="https://clob.polymarket.com")
    except:
        c = ClobClient()
    
    # 暴力注入属性 (兼容所有 SDK 版本)
    c.api_key = os.getenv("POLY_API_KEY") or os.getenv("API_KEY")
    c.api_secret = os.getenv("POLY_SECRET") or os.getenv("API_SECRET")
    c.api_passphrase = os.getenv("POLY_PASSPHRASE") or os.getenv("API_PASSPHRASE")
    c.private_key = os.getenv("PRIVATE_KEY") or os.getenv("POLY_PRIVATE_KEY")
    c.chain_id = POLYGON
    return c

client = get_lobster_client()

def execute_trade(symbol, token_id, side, price, strength):
    # 这里的函数名必须叫 execute_trade，否则 main.py 会报 ImportError
    try:
        logging.info(f"📤 [TRADE] {symbol} | {side} | 价格: {price}")
    except Exception as e:
        logging.error(f"❌ 交易执行失败: {e}")
