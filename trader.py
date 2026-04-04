import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
# 注意：删除了 GNOSIS_SAFE 的导入，防止 ImportError 导致崩溃
from config import *

# --- 实盘关键参数：签名模式 ---
# 0 = EOA (普通钱包), 1 = POLY_PROXY (旧版代理), 2 = GNOSIS_SAFE (官网标准代理)
# 针对你在官网充值的 0x365B... 账户，必须使用 2
SIGNATURE_TYPE_FIXED = 2 

# 初始化实盘客户端
try:
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=PRIVATE_KEY,
        chain_id=POLYGON,
        signature_type=SIGNATURE_TYPE_FIXED,  # 👈 直接使用数字 2，绕过 SDK 版本差异
        funder=POLY_ADDRESS,                 # 你的充值地址 0x365B...
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )
    logging.info("✅ 交易引擎初始化成功 (Mode: GNOSIS_SAFE)")
except Exception as e:
    logging.error(f"❌ 交易引擎初始化失败: {e}")
    client = None

def get_balance():
    """获取 Polymarket 协议内的可用余额"""
    if not client: return 0.0
    try:
        # 查询充值地址在协议中的余额
        resp = client.get_collateral_balance(POLY_ADDRESS)
        bal = resp.get("balance", 0)
        return round(float(bal), 2)
    except Exception as e:
        logging.error(f"⚠️ 余额查询异常: {e}")
        return 0.0

def execute_trade(symbol, side="UP", price=0.5, size=1):
    """
    执行下单逻辑
    symbol: BTC, ETH, SOL, HYPE, DOGE, BNB
    side: UP (看涨) 或 DOWN (看跌)
    """
    if not client:
        logging.error("❌ 下单失败: 客户端未初始化")
        return None

    # 从 config.py 的 MARKET_MAP 中提取你刚才录入的 Token ID
    token_id = MARKET_MAP.get(symbol, {}).get(side)
    if not token_id:
        logging.error(f"❌ 找不到资产 ID: {symbol} - {side}")
        return None

    try:
        # 1. 创建订单 (自动处理 EIP-712 结构)
        order_args = client.create_order(
            price=float(price),
            size=float(size),
            side="buy",  # 在 Polymarket 中，买入预测 Token 统称为 buy
            token_id=str(token_id)
        )
        
        # 2. 签名 (使用你的主钱包私钥对订单哈希进行签名)
        signed_order = client.sign_order(order_args)
        
        # 3. 广播到 CLOB 撮合引擎
        resp = client.place_order(signed_order)
        
        if resp.get("success"):
            msg = f"🚀 实盘下单成功！\n资产: {symbol} ({side})\n价格: {price}\n数量: {size}\n单号: {resp.get('orderID')}"
            logging.info(msg)
            # 这里可以调用你的 tg.send_message(msg) 发送战报
            return resp
        else:
            logging.warning(f"⚠️ 下单被拒绝: {resp}")
            return resp

    except Exception as e:
        logging.error(f"❌ {symbol} 交易执行异常: {e}")
        return None
