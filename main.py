import os
import logging
import time
from py_clob_client.client import ClobClient

# 1. 基础日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_real_trade():
    logger.info("🚀 启动 Lobster 龙虾交易系统 - Railway 实战版")

    # 2. 从环境变量获取私钥 (确保 Railway Variables 中有 FOX_PRIVATE_KEY)
    PK = os.getenv("FOX_PRIVATE_KEY")
    if not PK:
        logger.error("❌ 未找到 FOX_PRIVATE_KEY 环境变量，请在 Railway 中配置！")
        return

    try:
        # 3. 初始化客户端 (0.34.6 版本 chain_id 设为 137 代表 Polygon)
        # 这里的 host 必须是生产环境地址
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 4. 锁定 BTC 目标市场 (基于你提供的 Condition ID 对应的 YES Token)
        # BTC YES Token ID: 19504533038661601614761427845353594073359048386377758376510344406121408103328
        target_token = "19504533038661601614761427845353594073359048386377758376510344406121408103328"

        # 5. 构建下单参数 (直接使用字典，彻底解决 ModuleNotFoundError)
        # 注意：price 为 0.99 几乎保证在买入侧成交测试，size 为 1 代表 1U
        order_params = {
            "price": 0.99,
            "size": 1.0,
            "side": "BUY",
            "token_id": target_token
        }

        logger.info(f"📡 正在向 Polymarket 发送真实订单: {order_params}")

        # 6. 执行下单
        resp = client.create_order(order_params)

        # 7. 结果解析与安全防护
        if isinstance(resp, str):
            logger.error(f"❌ API 拒绝了请求或鉴权失败: {resp}")
        elif resp.get("success"):
            logger.info(f"✅ 【交易成功】 订单已提交！订单ID: {resp.get('orderID')}")
        else:
            logger.warning(f"⚠️ 下单响应异常: {resp}")

    except Exception as e:
        logger.error(f"🔥 运行时发生致命错误: {str(e)}")

if __name__ == "__main__":
    # 执行一次真实下单
    run_real_trade()
    
    # 防止容器立刻退出导致日志刷不出来
    logger.info("⏳ 任务执行完毕，等待 10 秒后退出...")
    time.sleep(10)
