import os
import asyncio
import logging

# ================= 1. 导入与兼容性处理 (已修正) =================
try:
    # 针对 py-clob-client 0.34.6 的正确导入路径
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
    # 注意：0.34.6 中 side 通常直接用字符串 "BUY"/"SELL"，不再强制从 OrderType 导入
except ImportError:
    logging.error("❌ 缺少 py-clob-client 库。请检查 requirements.txt 是否包含 py-clob-client==0.34.6")
    raise

# ================= 2. 基础配置 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 比特币测试 Token ID
BTC_TOKEN_ID = "21742450893073934336504295323901415510006760017135962002521191060010041285427" 

# 初始化客户端 (参数名适配 0.34.6)
# 注意：私钥参数名在不同版本间可能有差异，通常为 private_key 或 key
client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("PK"), 
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    api_passphrase=os.getenv("API_PASSPHRASE"),
    chain_id=137  # Polygon Mainnet
)

# ================= 3. 核心功能 =================

async def get_balance():
    """获取账户 USDC 余额"""
    try:
        # 0.34.6 版本的 get_balance 通常返回包含 balance 字段的字典
        res = await asyncio.to_thread(client.get_balance)
        balance = float(res.get("balance", 0)) if isinstance(res, dict) else float(res)
        logging.info(f"💰 账户余额: {balance} USDC")
        return balance
    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return 0.0

def get_market_price(token_id):
    """获取买卖盘中间价"""
    try:
        ob = client.get_order_book(token_id)
        # 适配返回格式
        bids = ob.bids if hasattr(ob, 'bids') else ob.get("bids", [])
        asks = ob.asks if hasattr(ob, 'asks') else ob.get("asks", [])
        
        if not bids or not asks:
            return 0.5  
        
        bid_top = float(bids[0].price if hasattr(bids[0], 'price') else bids[0][0])
        ask_top = float(asks[0].price if hasattr(asks[0], 'price') else asks[0][0])
        return round((bid_top + ask_top) / 2, 3)
    except Exception as e:
        logging.warning(f"获取价格失败，使用默认值: {e}")
        return 0.5

async def test_btc_order():
    """专门测试比特币下单的函数"""
    balance = await get_balance()
    
    if balance < 1.0:
        logging.warning("⚠️ 余额不足 1 USDC，无法下单测试。")
        return

    price = get_market_price(BTC_TOKEN_ID)
    size = 1.0  
    
    logging.info(f"🚀 准备下单 BTC | 价格: {price} | 数量: {size}")

    # 构造订单参数
    order_args = OrderArgs(
        price=price,
        size=size,
        side="BUY",
        token_id=BTC_TOKEN_ID
    )

    try:
        # 0.34.6 的标准流程：创建并直接 post (或者先 sign 再 post)
        # 这里使用最直接的 post_order，它会自动处理签名
        resp = await asyncio.to_thread(client.post_order, order_args)
        
        if resp and (resp.get("success") or resp.get("status") in ["OK", "success"]):
            logging.info(f"✅ 【比特币下单成功！】订单 ID: {resp.get('orderID')}")
        else:
            logging.error(f"❌ 【下单被拒绝】详情: {resp}")
    except Exception as e:
        logging.error(f"💥 下单过程崩溃: {e}")

# ================= 4. 启动逻辑 =================

async def main():
    logging.info("🛠️ 开始执行比特币下单压力测试...")
    
    # 验证环境变量
    if not os.getenv("PK"):
        logging.error("❌ 缺少环境变量 PK (私钥)，请在 Railway 后台设置。")
        return

    # 初始化：更新授权
    try:
        # 0.34.6 中，如果已经有 API Key，通常不需要再 derive
        logging.info("正在验证授权环境...")
        await asyncio.to_thread(client.get_api_keys) 
        logging.info("✅ 授权环境准备就绪")
    except Exception as e:
        logging.warning(f"⚠️ 授权验证异常 (可能尚未初始化): {e}")

    # 执行单次下单测试
    await test_btc_order()
    
    logging.info("🏁 测试任务结束，程序持续运行中...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
