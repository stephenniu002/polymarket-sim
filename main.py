import os
import asyncio
import logging
import requests
import sys
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs

# ================= 1. 强力日志与通知 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🤖 [Polymarket-Sim]\n{msg}"}, timeout=5)
        except: pass

# ================= 2. 核心功能 =================

async def main():
    logger.info("🚀 启动 Polymarket 批量下单修复版...")
    
    # 变量读取
    pk = os.getenv("PRIVATE_KEY")
    token_ids_raw = os.getenv("TEST_TOKEN_ID", "")
    order_size = float(os.getenv("ORDER_SIZE", "1.0"))

    # 1. 基础初始化
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=pk,
        chain_id=137
    )

    # 2. 注入凭证
    try:
        client.set_api_creds(ApiCreds(
            api_key=os.getenv("POLY_API_KEY"),
            api_secret=os.getenv("POLY_SECRET"),
            api_passphrase=os.getenv("POLY_PASSPHRASE")
        ))
        logger.info("🔑 API 凭证载入成功")
    except Exception as e:
        logger.error(f"❌ 凭证注入失败: {e}")

    # 3. 尝试查询状态 (使用兼容模式)
    try:
        logger.info("📡 尝试同步账户状态...")
        # 针对 0.34.6，如果 get_balance 没了，通常用 get_user_allowance
        # 或者直接查看 client.get_ok() 确认连接
        try:
            resp = await asyncio.to_thread(client.get_ok)
            logger.info(f"✅ 节点连接状态: {resp}")
        except:
            logger.warning("⚠️ 无法获取节点状态，将直接尝试下单")

    except Exception as e:
        logger.warning(f"⚠️ 状态检查跳过: {e}")

    # 4. 批量执行下单
    # 确保解析逗号分隔的 Token
    token_list = [t.strip() for t in token_ids_raw.split(",") if len(t.strip()) > 10]
    
    if not token_list:
        logger.error("❌ TEST_TOKEN_ID 为空，请在 Railway 设置。")
        return

    logger.info(f"🏹 准备为 {len(token_list)} 个方向下单...")

    for t_id in token_list:
        try:
            logger.info(f"正在下单 Token: {t_id[-8:]}...")
            
            # 构造订单
            order_args = OrderArgs(
                price=0.5, 
                size=order_size,
                side="BUY",
                token_id=t_id
            )
            
            # post_order 是 0.34.6 的核心下单方法
            resp = await asyncio.to_thread(client.post_order, order_args)
            
            if resp.get("success") or resp.get("status") in ["OK", "success"]:
                msg = f"✅ 下单成功!\nToken: ..{t_id[-6:]}\n金额: {order_size} USDC"
                logger.info(msg)
                send_tg(msg)
            else:
                msg = f"❌ 下单失败 (..{t_id[-6:]}): {resp}"
                logger.warning(msg)
                send_tg(msg)
                
        except Exception as e:
            err_msg = f"💥 下单异常: {str(e)}"
            logger.error(err_msg)
            send_tg(err_msg)
            
        await asyncio.sleep(1.5) # 频率保护

    logger.info("🏁 初始化任务处理完毕。")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
