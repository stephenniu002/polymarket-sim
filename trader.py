import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON, GNOSIS_SAFE
from config import *

# 初始化实盘客户端
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PRIVATE_KEY,
    chain_id=POLYGON,
    signature_type=GNOSIS_SAFE,
    funder=POLY_ADDRESS,
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
)

def get_balance():
    try:
        resp = client.get_collateral_balance(POLY_ADDRESS)
        return float(resp.get("balance", 0))
    except:
        return 0.0

def execute_trade(symbol, side="UP", price=0.5, size=1):
    """
    symbol: BTC, ETH, SOL...
    side: UP 或 DOWN
    """
    token_id = MARKET_MAP.get(symbol, {}).get(side)
    if not token_id:
        logging.error(f"❌ 未找到 {symbol} 的 {side} Token ID")
        return None

    try:
        # 1. 创建订单对象
        order_args = client.create_order(
            price=price,
            size=size,
            side="buy", # 实盘逻辑：买入 Yes/No Token 都是 buy 操作
            token_id=token_id
        )
        # 2. 签名
        signed_order = client.sign_order(order_args)
        # 3. 广播下单
        resp = client.place_order(signed_order)
        
        if resp.get("success"):
            msg = f"🚀 实盘下单成功！\n资产: {symbol} ({side})\n价格: {price}\n数量: {size}\n单号: {resp.get('orderID')}"
            logging.info(msg)
            return resp
    except Exception as e:
        logging.error(f"❌ {symbol} 下单异常: {e}")
        return None
