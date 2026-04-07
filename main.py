import os
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

# 1. 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_tg_message(text):
    """发送电报通知"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("⚠️ 未配置 TG_TOKEN 或 TELEGRAM_CHAT_ID，跳过通知。")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        logger.info("📲 电报通知已发出")
    except Exception as e:
        logger.error(f"❌ 电报发送失败: {e}")

def run_lobster_final():
    logger.info("🚀 [Lobster 龙虾] 启动全自动搜索 + 电报通知模式...")

    # 2. 变量加载
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    if not PK:
        msg = "❌ 错误：未找到 PRIVATE_KEY，请检查 Railway 变量！"
        logger.error(msg)
        send_tg_message(msg)
        return

    try:
        # 3. 初始化 0.34.6 客户端
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 4. 动态获取活跃 BTC 市场
        logger.info("🔍 正在扫描 Polymarket 活跃市场...")
        markets = client.get_markets()
        
        target_token_id = None
        market_name = "未知 BTC 市场"

        # 遍历寻找包含 BTC/Bitcoin 的活跃市场
        for m in markets:
            title = m.get('question', '').lower()
            if ('bitcoin' in title or 'btc' in title) and m.get('active'):
                tokens = m.get('tokens', [])
                if len(tokens) >= 2:
                    target_token_id = tokens[0]['token_id'] # YES Token
                    market_name = m.get('question')
                    break
        
        if not target_token_id:
            logger.error("❌ 未找到可交易的 BTC 市场")
            return

        # 5. 构建 OrderArgs 对象 (0.34.6 必需)
        # 价格 0.10, 数量 1.0U
        order = OrderArgs(
            price=0.10, 
            size=1.0, 
            side="BUY", 
            token_id=target_token_id
        )

        logger.info(f"🎯 目标锁定: {market_name}")
        logger.info(f"📡 正在提交订单 (1.0U)...")

        # 6. 执行真实下单
        resp = client.create_order(order)

        # 7. 结果处理与电报通知
        if isinstance(resp, str):
            error_msg = f"❌ API 错误: {resp}"
            logger.error(error_msg)
            send_tg_message(error_msg)
        elif resp.get("success"):
            order_id = resp.get('orderID')
            success_msg = (
                f"✅ *【Polymarket 下单成功】*\n\n"
                f"📈 *市场*: {market_name}\n"
                f"💰 *金额*: 1.0 U\n"
                f"📜 *订单ID*: `{order_id}`\n"
                f"🚀 *部署平台*: Railway"
            )
            logger.info(f"✅ 下单成功! ID: {order_id}")
            send_tg_message(success_msg)
        else:
            fail_msg = f"⚠️ 下单未成功: {resp}"
            logger.warning(fail_msg)
            send_tg_message(fail_msg)

    except Exception as e:
        err_text = f"🔥 运行时崩溃: {str(e)}"
        logger.error(err_text)
        send_tg_message(err_text)

if __name__ == "__main__":
    run_lobster_final()
    time.sleep(10)
