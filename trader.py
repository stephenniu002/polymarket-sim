import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# 直接定义 2 代表 Gnosis Safe (Polymarket 官网标准)
# 这样就不会报 ImportError 了
SIGNATURE_TYPE_PROXY = 2 

def get_client():
    return ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),
        chain_id=POLYGON,
        signature_type=SIGNATURE_TYPE_PROXY, 
        funder=os.getenv("POLY_ADDRESS"), 
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )

client = get_client()

def get_balance():
    try:
        resp = client.get_collateral_balance(os.getenv("POLY_ADDRESS"))
        return round(float(resp.get("balance", 0)), 2)
    except Exception as e:
        logging.error(f"❌ 余额查询失败: {e}")
        return 0.0

def execute_trade(token_id, price=0.5, size=1.0):
    """
    接收动态抓取的 token_id 进行下单
    """
    try:
        order_args = client.create_order(
            price=float(price),
            size=float(size),
            side="buy",
            token_id=str(token_id)
        )
        signed_order = client.sign_order(order_args)
        return client.place_order(signed_order)
    except Exception as e:
        logging.error(f"❌ 交易异常: {e}")
        return None
