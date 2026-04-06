import os
import asyncio
import logging
import requests
import sys
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 1. 日志与通知 =================
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
    logger.info("🚀 启动 Polymarket 极简兼容版 (v0.34.6)...")
    
    # 环境变量读取
    pk = os.getenv("PRIVATE_KEY")
    token_ids_raw = os.getenv("TEST_TOKEN_ID", "")
    order_size = float(os.getenv("ORDER_SIZE", "1.0"))

    # 1. 初始化客户端
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
        logger.error(f"❌ 凭证载入失败: {e}")

    # 3. 解析 Token 列表
    token_list = [t.strip() for t in token_ids_raw.split(",") if len(t.strip()) > 10]
    
    if not token_list:
        logger.error("❌ TEST_TOKEN_ID 为空，请在 Railway 设置。")
        return

    logger.info(f"🏹 准备下单，目标数量: {len(token_list)} 个方向...")

    for t_id in token_list:
        try:
            logger.info(f"正在处理 Token: {t_id[-8:]}")
            
            # 关键修复：直接使用字典而不是 OrderArgs 对象
            # 这样可以避开 py-clob-client 内部对 .dict() 的错误调用
            order_params = {
                "price": 0.5,
                "size": order_size,
                "side": "BUY",
                "token_id": t_id
            }
            
            # 使用 post_order 提交字典
            resp = await asyncio.to_thread(client.post_order, order_params)
            
            if resp.get("success") or resp.get("status") in ["OK", "success"]:
                success_msg = f"✅ 下单成功!\nToken: ..{t_id[-6:]}\n价格: 0.5 | 数量: {order_size}"
                logger.info(success_msg)
                send_tg(success_msg)
            else:
                # 记录拒绝原因，方便排查
                error_detail = resp.get("error") or resp.get("message") or resp
                fail_msg = f"❌ 下单拒绝 (..{t_id[-6:]}): {error_detail}"
                logger.warning(fail_msg)
                send_tg(fail_msg)
                
        except Exception as e:
            err_msg = f"💥 下单逻辑故障 (..{t_id[-4:]}): {str(e)}"
            logger.error(err_msg)
            send_tg(err_msg)
            
        await asyncio.sleep(2) # 增加延迟，防止触发频率限制

    logger.info("🏁 本轮初始化下单任务结束。")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
