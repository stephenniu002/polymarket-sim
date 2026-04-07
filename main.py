import os
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

# 1. 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_tg_message(text):
    """通过 Telegram Bot 发送实时通知"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        logger.info("📲 电报通知已成功发出")
    except Exception as e:
        logger.error(f"❌ 电报发送失败: {e}")

def run_lobster_dynamic():
    logger.info("🚀 [Lobster 龙虾] 启动自动搜索下单模式...")
    
    # 自动适配私钥名
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    if not PK:
        logger.error("❌ 未在 Railway Variables 中找到 PRIVATE_KEY")
        return

    try:
        # 2. 初始化 0.34.6 客户端
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 3. 动态扫描活跃市场 (防范 404 错误)
        logger.info("🔍 正在扫描 Polymarket CLOB 以寻找活跃的 BTC 市场...")
        resp_markets = client.get_markets()
        
        # 稳健性检查：如果是报错字符串则终止
        if isinstance(resp_markets, str):
            error_info = f"❌ API 返回了错误字符串: `{resp_markets}` (请检查 API 权限)"
            logger.error(error_info)
            send_tg_message(error_info)
            return

        target_token_id = None
        market_name = ""

        # 遍历所有市场，寻找包含 "BTC" 或 "Bitcoin" 的活跃市场
        for m in resp_markets:
            if not isinstance(m, dict): continue
            title = m.get('question', '').lower()
            if ('btc' in title or 'bitcoin' in title) and m.get('active'):
                tokens = m.get('tokens', [])
                if len(tokens) >= 2:
                    target_token_id = tokens[0]['token_id'] # 这里的 0 通常是 YES Token
                    market_name = m.get('question')
                    break
        
        if not target_token_id:
            logger.warning("⚠️ 当前 CLOB 中没有活跃的 BTC 市场可供交易")
            return

        # 4. 构建下单对象 (使用 OrderArgs 对齐 SDK 内部逻辑)
        # 价格设为 0.11U，挂单 1.0U，确保能够成功发送请求
        order = OrderArgs(
            price=0.11, 
            size=1.0, 
            side="BUY", 
            token_id=target_token_id
        )

        logger.info(f"🎯 锁定目标: {market_name}")
        logger.info(f"📡 提交实战订单 (1.0U) 到 Polygon...")
        
        resp = client.create_order(order)

        # 5. 下单响应处理与电报同步
        if isinstance(resp, str):
            logger.error(f"❌ 下单失败: {resp}")
            send_tg_message(f"❌ 下单失败: `{resp}`")
        elif resp.get("success"):
            order_id = resp.get('orderID')
            success_text = (
                f"✅ *【Polymarket 下单成功】*\n\n"
                f"📈 市场: {market_name}\n"
                f"📜 订单 ID: `{order_id}`\n"
                f"🤖 平台: Railway (Lobster 系统)"
            )
            logger.info(f"✅ 下单成功! ID: {order_id}")
            send_tg_message(success_text)
        else:
            logger.warning(f"⚠️ 响应不明确: {resp}")

    except Exception as e:
        err_msg = f"🔥 运行时遭遇致命崩溃: {str(e)}"
        logger.error(err_msg)
        send_tg_message(err_msg)

if __name__ == "__main__":
    run_lobster_dynamic()
    # 强制留出 10 秒处理日志和请求
    time.sleep(10)
