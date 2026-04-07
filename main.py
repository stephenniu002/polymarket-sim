import os
import logging
import time
from py_clob_client.client import ClobClient
# 核心修正：在 0.34.6 中，OrderArgs 位于 clob_types
from py_clob_client.clob_types import OrderArgs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_real_trade():
    logger.info("🚀 [Lobster 实战] 尝试 0.34.6 对象对齐版...")

    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    if not PK:
        logger.error("❌ 未找到 PRIVATE_KEY")
        return

    try:
        # 初始化客户端
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # BTC YES Token ID
        btc_yes_token = "19504533038661601614761427845353594073359048386377758376510344406121408103328"

        # 核心修正：创建一个真正的 OrderArgs 对象，解决 'dict' has no attribute 报错
        order = OrderArgs(
            price=0.99,
            size=1.0,
            side="BUY",
            token_id=btc_yes_token
        )

        logger.info(f"📡 正在发送 OrderArgs 对象下单...")

        # 执行下单
        resp = client.create_order(order)

        if isinstance(resp, str):
            logger.error(f"❌ API 错误: {resp}")
        elif resp.get("success"):
            logger.info(f"✅ 【下单成功！】 订单 ID: {resp.get('orderID')}")
        else:
            logger.warning(f"⚠️ 下单响应: {resp}")

    except Exception as e:
        logger.error(f"🔥 运行时错误: {str(e)}")

if __name__ == "__main__":
    run_real_trade()
    time.sleep(10)
