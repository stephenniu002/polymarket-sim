import os
import logging
import time
from py_clob_client.client import ClobClient

# 1. 基础日志配置 - 调整为 INFO 级别以便在 Railway 看到核心过程
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_real_trade():
    logger.info("🚀 [Lobster 实战] 正在启动最终覆盖版...")

    # 2. 自动适配 Railway 变量名 (尝试读取所有可能的私钥 Key)
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    
    if not PK:
        logger.error("❌ 错误：Railway 变量中未找到 PRIVATE_KEY。请检查 Variables 面板！")
        return

    try:
        # 3. 初始化 0.34.6 客户端 (137 是 Polygon 链 ID)
        # 注意：这里直接硬编码生产环境 Host
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 4. 锁定目标：BTC YES Token ID (由你提供)
        # 此 Token 对应 BTC 价格预测市场的 "肯定" 结果
        btc_yes_token = "19504533038661601614761427845353594073359048386377758376510344406121408103328"

        # 5. 构建字典参数 (绕过所有 models/types 导入)
        # price=0.99 确保测试单能快速在买方成交
        order_params = {
            "price": 0.99,
            "size": 1.0,
            "side": "BUY",
            "token_id": btc_yes_token
        }

        logger.info(f"📡 准备向 CLOB 发送真实订单 (1.0U) -> Token: {btc_yes_token[:10]}...")

        # 6. 执行真实下单
        resp = client.create_order(order_params)

        # 7. 响应处理 (0.34.6 返回逻辑)
        if isinstance(resp, str):
            logger.error(f"❌ API 鉴权或网络错误: {resp}")
        elif resp.get("success"):
            logger.info("========================================")
            logger.info(f"✅ 【真实下单成功！】")
            logger.info(f"📜 订单 ID: {resp.get('orderID')}")
            logger.info("========================================")
        else:
            logger.warning(f"⚠️ 下单响应未成功: {resp}")

    except Exception as e:
        logger.error(f"🔥 运行时遭遇致命异常: {str(e)}")

if __name__ == "__main__":
    # 立即执行实盘操作
    run_real_trade()
    
    # 保持日志可见性
    logger.info("⏳ 任务结束，程序将在 10 秒后自动关闭。")
    time.sleep(10)
