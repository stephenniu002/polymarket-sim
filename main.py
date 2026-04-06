import os
import asyncio
import logging

# ================= 1. 导入与兼容性处理 =================
try:
    from py_polymarket_client import ClobClient, OrderArgs, OrderType
except ImportError:
    logging.error("❌ 缺少 py-polymarket-client 库。请在 requirements.txt 中添加并重新部署。")
    # 如果库没装上，程序无法运行，这里直接抛出以便在日志查看
    raise

# ================= 2. 基础配置 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 比特币测试 Token ID (请确保这是你想要操作的具体价格合约 ID)
# 示例：BTC Price Above $70,000 (Yes) 的 Token ID
BTC_TOKEN_ID = "21742450893073934336504295323901415510006760017135962002521191060010041285427" 

# 从环境变量获取配置（确保你在云端 Settings 填了这些）
client = ClobClient(
    host="https://clob.polymarket.com",
    private_key=os.getenv("PK"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    api_passphrase=os.getenv("API_PASSPHRASE")
)

# ================= 3. 核心功能 =================

async def get_balance():
    """获取账户 USDC 余额"""
    try:
        # 获取当前 client 关联地址的余额
        res = await asyncio.to_thread(client.get_balance)
        balance = float(res.get("balance", 0)) if isinstance(res, dict) else float(res)
        logging.info(f"💰 账户余额: {balance} USDC")
        return balance
    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return 0.0

def get_market_price(token_id):
    """获取买卖盘中间价，防止乱出价"""
    try:
        ob = client.get_order_book(token_id)
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        if not bids or not asks:
            return 0.5  # 默认中间价
        bid_top = float(bids[0][0])
        ask_top = float(asks[0][0])
        return round((bid_top + ask_top) / 2, 3)
    except:
        return 0.5

async def test_btc_order():
    """专门测试比特币下单的函数"""
    balance = await get_balance()
    
    if balance < 1.0:
        logging.warning("⚠️ 余额不足 1 USDC，无法下单测试。")
        return

    price = get_market_price(BTC_TOKEN_ID)
    size = 1.0  # 测试单固定 1 USDC，降低风险
    
    logging.info(f"🚀 准备下单 BTC | 价格: {price} | 数量: {size}")

    order = OrderArgs(
        price=price,
        size=size,
        side="BUY",
        token_id=BTC_TOKEN_ID
    )

    try:
        # 1. 创建并签名
        signed_order = await asyncio.to_thread(client.create_order, order)
        # 2. 提交到市场
        resp = await asyncio.to_thread(client.post_order, signed_order)
        
        if resp and (resp.get("success") or resp.get("status") == "OK"):
            logging.info(f"✅ 【比特币下单成功！】订单 ID: {resp.get('orderID')}")
        else:
            logging.error(f"❌ 【下单被拒绝】详情: {resp}")
    except Exception as e:
        logging.error(f"💥 下单过程崩溃: {e}")

# ================= 4. 启动逻辑 =================

async def main():
    logging.info("🛠️ 开始执行比特币下单压力测试...")
    
    # 初始化：更新授权
    try:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        client.update_balance_allowance()
        logging.info("✅ 授权环境准备就绪")
    except Exception as e:
        logging.warning(f"⚠️ 授权初始化异常 (可能已授权): {e}")

    # 执行单次下单测试
    await test_btc_order()
    
    logging.info("🏁 测试任务结束，程序挂起防止容器退出。")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
