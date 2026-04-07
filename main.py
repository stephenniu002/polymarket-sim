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
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        logger.info("📲 电报通知已发出")
    except Exception as e:
        logger.error(f"❌ 电报发送失败: {e}")

def run_lobster_final():
    logger.info("🚀 [Lobster] 启动自动搜索 + 电报版...")
    
    # 获取私钥 (兼容两个可能的变量名)
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    if not PK:
        logger.error("❌ 未找到 PRIVATE_KEY")
        return

    try:
        # 初始化 0.34.6 客户端
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # --- 自动搜索活跃市场 ---
        logger.info("🔍 正在扫描 CLOB 活跃市场以匹配 BTC...")
        resp_markets = client.get_markets()
        
        # 防崩：检查返回是否为错误字符串
        if isinstance(resp_markets, str):
            error_info = f"❌ API 返回错误字符串: `{resp_markets}`"
            logger.error(error_info)
            send_tg_message(error_info)
            return

        target_token_id = None
        market_name = ""

        # 遍历寻找包含 BTC 或 Bitcoin 的活跃市场
        for m in resp_markets:
            if not isinstance(m, dict): continue
            title = m.get('question', '').lower()
            if ('btc' in title or 'bitcoin' in title) and m.get('active'):
                tokens = m.get('tokens', [])
                if len(tokens) >= 2:
                    target_token_id = tokens[0]['token_id'] # 通常 0 是 YES
                    market_name = m.get('question')
                    break
        
        if not target_token_id:
            logger.warning("❌ 未找到可下单的活跃 BTC 市场")
            return

        # --- 执行下单 ---
        # 使用 0.11U 低价尝试 1.0U 挂单测试
        order = OrderArgs(
            price=0.11, 
            size=1.0, 
            side="BUY", 
            token_id=target_token_id
        )

        logger.info(f"🎯 锁定目标: {market_name}")
        logger.info(f"📡 发送订单 (1.0U)...")
        
        resp = client.create_order(order)

        # 下单响应处理
        if isinstance(resp, str):
            logger.error(f"❌ 下单 API 报错: {resp}")
            send_tg_message(f"❌ 下单失败: `{resp}`")
        elif resp.get("success"):
            order_id = resp.get('orderID')
            success_text = f"✅ *【Polymarket 下单成功】*\n\n📈 市场: {market_name}\n📜 ID: `{order_id}`"
            logger.info(f"✅ 成功! ID: {order_id}")
            send_tg_message(success_text)
        else:
            logger.warning(f"⚠️ 响应异常: {resp}")

    except Exception as e:
        err_msg = f"🔥 运行时崩溃: {str(e)}"
        logger.error(err_msg)
        send_tg_message(err_msg)

if __name__ == "__main__":
    run_lobster_final()
    time.sleep(10)
