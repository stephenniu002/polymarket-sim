import os
import asyncio
import logging
import time
from typing import Dict

# 假设你使用的是 py-polymarket-client 库
# 请确保你的环境变量中已设置：PK, API_KEY, API_SECRET, API_PASSPHRASE
from py_polymarket_client import ClobClient, OrderArgs, OrderType

# ================= 配置区 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 示例市场 ID (请务必替换为你实际要交易的 Token ID)
MARKETS = {
    "BTC-High": {"UP": "21742450893073934336504295323901415510006760017135962002521191060010041285427"},
    "ETH-High": {"UP": "11152450893073934336504295323901415510006760017135962002521191060010041285427"}
}

# 初始化 Client (建议放在全局或通过函数获取)
# 这里的参数根据你的库版本可能需要微调
client = ClobClient(
    host="https://clob.polymarket.com",
    private_key=os.getenv("PK"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
    api_passphrase=os.getenv("API_PASSPHRASE")
)

# ================= 初始化引擎 =================
def init_engine():
    try:
        logging.info("🔧 V17.2 启动：标准初始化模式...")
        # 获取或验证 API 凭据
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        
        try:
            # 必须步骤：授权 L2 允许使用 USDC
            client.update_balance_allowance()
        except Exception as e:
            logging.warning(f"⚠️ Allowance 跳过或已存在: {e}")
            
        logging.info("✅ 引擎初始化完成，交易链路已打通")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# ================= 获取余额 =================
async def get_balance():
    try:
        # Polymarket SDK 的 get_balance 通常需要地址，或从 client 内部获取
        # 使用 to_thread 避免阻塞事件循环
        res = await asyncio.to_thread(client.get_balance)
        
        # 兼容处理：有些版本返回字典 {'balance': '10.5'}, 有些直接返回数字
        if isinstance(res, dict):
            return float(res.get("balance", 0))
        return float(res) if res else 0.0
    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return 0.0

# ================= 获取价格 =================
def get_price(token_id):
    try:
        ob = client.get_order_book(token_id)
        bids = ob.bids if hasattr(ob, 'bids') else ob.get("bids", [])
        asks = ob.asks if hasattr(ob, 'asks') else ob.get("asks", [])
        
        if not bids or not asks:
            return 0.5  # 默认中间价
            
        # 取买一和卖一的均价
        bid_price = float(bids[0].price if hasattr(bids[0], 'price') else bids[0][0])
        ask_price = float(asks[0].price if hasattr(asks[0], 'price') else asks[0][0])
        return round((bid_price + ask_price) / 2, 3)
    except Exception:
        return 0.5

# ================= 执行下单 =================
async def execute(token, name, balance):
    try:
        # 策略：每次使用余额的 10%，最小 1 USDC
        size = max(1.0, round(balance * 0.1, 2))
        price = get_price(token)
        
        logging.info(f"🔍 尝试下单: {name} | 价格: {price} | 数量: {size}")
        
        order = OrderArgs(
            price=price,
            size=size,
            side="BUY", 
            token_id=str(token)
        )
        
        def _do_post():
            signed_order = client.create_order(order)
            return client.post_order(signed_order)

        res = await asyncio.to_thread(_do_post)
        
        # 检查返回结果是否包含成功标识
        if res and isinstance(res, dict) and (res.get("success") or res.get("status") == "OK"):
            logging.info(f"🎯 【交易成功】{name} | 订单ID: {res.get('orderID')}")
        else:
            logging.warning(f"❌ 【下单拒绝】API 返回: {res}")
            
    except Exception as e:
        logging.error(f"❌ 交易执行异常: {e}")

# ================= 核心循环 =================
async def step():
    balance = await get_balance()
    logging.info(f"💰 当前账户余额: {balance} USDC")
    
    if balance < 1.0:
        logging.warning("⚠️ 余额不足 1 USDC，无法执行策略")
        return

    for coin, tokens in MARKETS.items():
        token_id = tokens["UP"]
        await execute(token_id, coin, balance)
        # 短暂休眠防止频率限制
        await asyncio.sleep(1)

async def main():
    if not init_engine():
        logging.critical("🛑 初始化失败，程序退出")
        return
        
    while True:
        try:
            await step()
            logging.info("💤 等待 5 分钟进行下一次轮询...")
            await asyncio.sleep(300) 
        except Exception as e:
            logging.error(f"💥 系统循环异常: {e}")
            await asyncio.sleep(10)

# ================= 程序入口 =================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 程序由用户手动关闭")
