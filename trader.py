import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON, ETH  # POLYGON/ETH/其它链

logging.basicConfig(level=logging.INFO)

SIGNATURE_TYPE_PROXY = 2  # 使用代理钱包

def get_client():
    """
    初始化 ClobClient（0.34.6 版本兼容写法）
    """
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),    # 私钥
        funder=os.getenv("POLY_ADDRESS"),     # 钱包地址
        chain_id=POLYGON,
        signature_type=SIGNATURE_TYPE_PROXY
    )

    # ✅ 通过 set_api_creds 注入 API Key/Secret/Passphrase
    client.set_api_creds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )
    return client

client = get_client()

def get_balance():
    try:
        resp = client.get_collateral_balance(os.getenv("POLY_ADDRESS"))
        balance = round(float(resp.get("balance", 0)), 2)
        logging.info(f"💰 当前账户余额: {balance} USDC")
        return balance
    except Exception as e:
        logging.error(f"❌ 查询余额失败: {e}")
        return 0.0

def execute_trade(token_id, price=0.5, size=1.0, side="buy"):
    try:
        order_args = client.create_order(
            token_id=str(token_id),
            price=float(price),
            size=float(size),
            side=side
        )
        signed_order = client.sign_order(order_args)
        result = client.place_order(signed_order)
        logging.info(f"✅ 下单成功: {result}")
        return result
    except Exception as e:
        logging.error(f"❌ 下单失败: {e}")
        return None

def fetch_latest_token_id(symbol: str):
    """
    动态抓取市场最新 token_id
    symbol: "BTC", "ETH", "SOL" ...
    """
    try:
        markets = client.get_markets()
        for m in markets:
            if m["symbol"] == symbol:
                return m["token_id"]
        logging.warning(f"⚠️ 未找到 {symbol} 市场")
        return None
    except Exception as e:
        logging.error(f"❌ 获取 token_id 失败: {e}")
        return None
