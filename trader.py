import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# 1. 这里的导入和签名定义保持不变
SIGNATURE_TYPE_PROXY = 2 

def get_client():
    # 注意：最新版 SDK 使用私钥和地址进行初始化
    # API 相关的 Key/Secret 是通过 client.create_api_key() 或后续设置的
    # 或者是作为构造函数中特定的 creds 传入
    
    # 适配 0.34.6 的最稳妥初始化方式：
    return ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),
        chain_id=POLYGON,
        signature_type=SIGNATURE_TYPE_PROXY,
        funder=os.getenv("POLY_ADDRESS")
        # ⚠️ 注意：这里删除了 api_key, api_secret, api_passphrase
        # 因为新版构造函数不再直接接收这些关键字参数
    )

client = get_client()

# 如果你需要使用 API 凭证来做下单等需要权限的操作，可以在这里注入
client.set_api_creds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
)

def get_balance():
    try:
        # 获取实盘可用余额 (针对你的 0x365B... 地址)
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
