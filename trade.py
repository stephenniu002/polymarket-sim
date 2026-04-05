import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===============================
# 核心修复：注入参数
# ===============================
def get_lobster_client():
    # 强制获取私钥，如果没有则报错提醒
    pk = os.getenv("PRIVATE_KEY")
    if not pk:
        logging.error("❌ 环境变量 PRIVATE_KEY 缺失！请检查 Railway 设置。")
    
    try:
        c = ClobClient(host="https://clob.polymarket.com")
    except:
        c = ClobClient()
    
    # 属性注入
    c.host = "https://clob.polymarket.com"
    c.api_key = os.getenv("POLY_API_KEY")
    c.api_secret = os.getenv("POLY_SECRET")
    c.api_passphrase = os.getenv("POLY_PASSPHRASE")
    c.private_key = pk
    c.chain_id = POLYGON
    return c

client = get_lobster_client()

# ===============================
# 函数定义 (必须叫 execute_trade)
# ===============================
def execute_trade(symbol, token_id, side, price, strength):
    try:
        logging.info(f"📤 信号确认: {symbol} | {side} | 价格: {price} | 强度: {strength}")
        
        # 你的交易逻辑（计算 size 等）
        size = 1.0 # 建议根据 strength 动态计算
        
        # 调用已经注入私钥的 client
        # resp = client.create_order(token_id=token_id, price=price, size=size, side="BUY")
        # logging.info(f"✅ 订单已发送: {resp}")
        
    except Exception as e:
        logging.error(f"❌ 下单执行失败: {e}")
