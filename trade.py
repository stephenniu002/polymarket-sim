import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_lobster_client():
    # 1. 创建空实例，不传任何可能导致崩溃的构造参数
    try:
        # 尝试只传 host，这是最稳的
        c = ClobClient(host="https://clob.polymarket.com")
    except:
        c = ClobClient()
    
    # 2. 手动强行注入属性 (无论 SDK 怎么变，这些内部属性是一致的)
    c.host = "https://clob.polymarket.com"
    c.key = os.getenv("POLY_API_KEY")           # 兼容旧版
    c.api_key = os.getenv("POLY_API_KEY")       # 兼容新版
    c.secret = os.getenv("POLY_SECRET")
    c.api_secret = os.getenv("POLY_SECRET")
    c.passphrase = os.getenv("POLY_PASSPHRASE")
    c.api_passphrase = os.getenv("POLY_PASSPHRASE")
    c.private_key = os.getenv("PRIVATE_KEY")
    c.chain_id = POLYGON
    return c

client = get_lobster_client()

def execute_trade(symbol, token_id, side, price, strength):
    """龙虾实战执行"""
    if not client:
        logging.error("❌ 客户端未就绪")
        return
    try:
        logging.info(f"📤 [LIVE] {symbol} | {side} | 价格: {price}")
        # 锁定你的 0xd962 地址执行
        # order = client.create_order(token_id=token_id, price=float(price), size=1.0, side="BUY")
        # logging.info(f"✅ 结果: {client.post_order(order)}")
    except Exception as e:
        logging.error(f"❌ 执行异常: {e}")
