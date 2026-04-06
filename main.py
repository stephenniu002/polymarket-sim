import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs

# ================= 1. 基础配置 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取测试 Token ID (BTC Price Above/Below)
BTC_TOKEN_ID = os.getenv("TEST_TOKEN_ID", "21742450893073934336504295323901415510006760017135962002521191060010041285427")

# ================= 2. Telegram 通知功能 =================
def send_tg_msg(message):
    """发送消息到 Telegram"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": f"🤖 [Polymarket-Sim]\n{message}"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Telegram 发送失败: {e}")

# ================= 3. 客户端初始化 (已适配 0.34.6) =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("PRIVATE_KEY"),  # 对应你的 Railway 变量
    chain_id=137
)

try:
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))
    logger.info("🔑 API 凭证载入成功")
except Exception as e:
    logger.error(f"❌ 凭证载入失败: {e}")

# ================= 4. 核心逻辑 =================
async def get_balance():
    try:
        res = await asyncio.to_thread(client.get_balance)
        balance = float(res.get("balance", 0)) if isinstance(res, dict) else float(res)
        logger.info(f"💰 当前余额: {balance} USDC")
        return balance
    except Exception as e:
        logger.error(f"❌ 余额获取失败: {e}")
        return 0.0

async def test_btc_order():
    balance = await get_balance()
    if balance < 1.0:
        send_tg_msg(f"⚠️ 余额不足 ({balance} USDC)，跳过下单测试。")
        return

    # 这里为了演示简单，固定一个极低价买单
    # 如果要动态获取价格，可以使用 get_market_price
    price = 0.5 
    size = float(os.getenv("ORDER_SIZE", "1.0"))
    
    order_args = OrderArgs(
        price=price,
        size=size,
        side="BUY",
        token_id=BTC_TOKEN_ID
    )

    try:
        logger.info(f"🚀 尝试下单 BTC | 价格: {price} | 数量: {size}")
        resp = await asyncio.to_thread(client.post_order, order_args)
        
        if resp and (resp.get("success") or resp.get("status") in ["OK", "success"]):
            msg = f"✅ 下单成功!\n订单ID: {resp.get('orderID')}\n金额: {size} USDC"
            logger.info(msg)
            send_tg_msg(msg)
        else:
            err_msg = f"❌ 下单被拒: {resp}"
            logger.error(err_msg)
            send_tg_msg(err_msg)
    except Exception as e:
        logger.error(f"💥 运行崩溃: {e}")
        send_tg_msg(f"💥 运行崩溃: {str(e)}")

# ================= 5. 启动入口 =================
async def main():
    logger.info("🛠️ 启动测试任务...")
    
    # 第一次运行建议激活 USDC 授权 (Allowance)
    try:
        # 如果是新私钥，必须运行下面这行
        # await asyncio.to_thread(client.update_balance_allowance)
        pass
    except:
        pass

    await test_btc_order()
    
    logger.info("🏁 任务完成，容器进入持续运行状态...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
