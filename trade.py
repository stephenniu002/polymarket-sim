import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===============================
# 1. 身份注入 (0xd962...CB24)
# ===============================
def get_lobster_client():
    # 核心：从 Railway 环境变量读取私钥
    pk = os.getenv("PRIVATE_KEY")
    
    if not pk:
        logging.error("❌ 环境变量 PRIVATE_KEY 缺失！请在 Railway Variables 中添加。")
        return None

    if not pk.startswith("0x"):
        pk = "0x" + pk

    try:
        # 初始化 Polymarket 客户端
        c = ClobClient(
            host="https://clob.polymarket.com",
            api_key=os.getenv("POLY_API_KEY"),
            api_secret=os.getenv("POLY_SECRET"),
            api_passphrase=os.getenv("POLY_PASSPHRASE"),
            chain_id=POLYGON,
            private_key=pk
        )
        return c
    except Exception as e:
        logging.error(f"❌ CLOB 客户端初始化失败: {e}")
        return None

client = get_lobster_client()

# ===============================
# 2. 导出 execute_trade 函数
# ===============================
def execute_trade(symbol, token_id, side, price, strength):
    """龙虾火控系统 - 实战执行"""
    if not client:
        logging.error("⚠️ 交易取消: 客户端未就绪 (检查 PRIVATE_KEY)")
        return

    try:
        # 基于 5.993 USDC 的动态仓位逻辑
        # 强度 strength 越高，下单越多
        base_size = 1.0
        order_size = round(base_size * (1 + float(strength)), 2)

        logging.info(f"📤 [TRADE] 准备下单: {symbol} | {side} | 数量: {order_size} | 价格: {price}")

        # --- ⚠️ 真实下单开关 ---
        # order = client.create_order(token_id=token_id, price=float(price), size=float(order_size), side="BUY")
        # res = client.post_order(order)
        # logging.info(f"✅ 下单回执: {res}")
        
    except Exception as e:
        logging.error(f"❌ 交易执行异常: {e}")
