import os
import asyncio
import logging
import requests
import sys
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs

# ================= 1. 强制日志即时输出 =================
# 解决 Railway 日志空白的问题
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================= 2. Telegram 通知函数 =================
def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🤖 [Polymarket]\n{msg}"}, timeout=5)
        except:
            pass

# ================= 3. 核心逻辑 =================

async def main():
    logger.info("🚀 程序启动，正在初始化客户端...")
    
    # 从 Railway 变量读取（对应你截图中的变量名）
    pk = os.getenv("PRIVATE_KEY")
    api_key = os.getenv("POLY_API_KEY")
    api_secret = os.getenv("POLY_SECRET")
    api_passphrase = os.getenv("POLY_PASSPHRASE")
    token_id = os.getenv("TEST_TOKEN_ID")

    if not pk or not api_key:
        err = "❌ 缺少关键环境变量 (PRIVATE_KEY 或 POLY_API_KEY)"
        logger.error(err)
        send_tg(err)
        return

    try:
        # 初始化 ClobClient (适配 0.34.6)
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=pk,
            chain_id=137
        )
        
        # 注入 API 凭证
        client.set_api_creds(ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        ))
        
        logger.info("📡 正在查询余额...")
        # get_balance 在 0.34.6 中是同步调用，包装进 to_thread 防止阻塞
        resp = await asyncio.to_thread(client.get_balance)
        balance = resp.get("balance") if isinstance(resp, dict) else resp
        
        balance_msg = f"💰 当前账户余额: {balance} USDC"
        logger.info(balance_msg)
        send_tg(balance_msg)

        # 如果余额充足且有 Token ID，尝试下单测试
        if token_id and float(balance or 0) > 1.0:
            logger.info(f"🏹 准备下单测试 Token: {token_id[:10]}...")
            
            order_args = OrderArgs(
                price=0.5, # 测试用固定价格
                size=1.0,  # 测试用 1 USDC
                side="BUY",
                token_id=token_id
            )
            
            # 执行下单
            order_resp = await asyncio.to_thread(client.post_order, order_args)
            
            if order_resp.get("success") or order_resp.get("status") == "OK":
                success_msg = f"✅ 下单成功！订单ID: {order_resp.get('orderID')}"
                logger.info(success_msg)
                send_tg(success_msg)
            else:
                fail_msg = f"⚠️ 下单未成功: {order_resp}"
                logger.warning(fail_msg)
                send_tg(fail_msg)
        else:
            logger.warning("⏭️ 余额不足或未设置 TEST_TOKEN_ID，跳过下单步骤。")

    except Exception as e:
        error_msg = f"💥 程序运行崩溃: {str(e)}"
        logger.error(error_msg)
        send_tg(error_msg)

    # 防止容器退出，保持运行以便查看日志
    logger.info("🏁 任务结束，程序进入监听状态...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
