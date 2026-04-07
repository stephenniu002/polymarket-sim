import os
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_tg_message(text):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def run_lobster_final():
    logger.info("🚀 [Lobster] 启动类型安全版...")
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    
    try:
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # --- 核心修正：对 get_markets 结果进行类型检查 ---
        markets_resp = client.get_markets()
        
        if isinstance(markets_resp, str):
            error_msg = f"❌ API 返回了错误字符串而非列表: `{markets_resp}`。请检查 API Key 或频率限制。"
            logger.error(error_msg)
            send_tg_message(error_msg)
            return

        # 确保它是列表且不为空
        if not isinstance(markets_resp, list):
            logger.error(f"❌ 预期返回列表，实际得到: {type(markets_resp)}")
            return

        target_token_id = None
        market_name = ""

        for m in markets_resp:
            # 再次确认 m 是字典
            if not isinstance(m, dict): continue
            
            title = m.get('question', '').lower()
            if ('bitcoin' in title or 'btc' in title) and m.get('active'):
                tokens = m.get('tokens', [])
                if len(tokens) >= 2:
                    target_token_id = tokens[0]['token_id']
                    market_name = m.get('question')
                    break
        
        if not target_token_id:
            logger.error("❌ 未找到活跃 BTC 市场")
            return

        # 实例化 OrderArgs 确保属性存在
        order = OrderArgs(price=0.10, size=1.0, side="BUY", token_id=target_token_id)
        
        logger.info(f"🎯 锁定: {market_name} | 正在下单...")
        resp = client.create_order(order)

        # 对下单结果也进行字符串判断
        if isinstance(resp, str):
            logger.error(f"❌ 下单失败，API 返回: {resp}")
            send_tg_message(f"❌ 下单失败: `{resp}`")
        elif resp.get("success"):
            order_id = resp.get('orderID')
            send_tg_message(f"✅ *下单成功*\n市场: {market_name}\nID: `{order_id}`")
            logger.info(f"✅ 成功! ID: {order_id}")
        else:
            logger.warning(f"⚠️ 响应异常: {resp}")

    except Exception as e:
        err_text = f"🔥 运行时崩溃: {str(e)}"
        logger.error(err_text)
        send_tg_message(err_text)

if __name__ == "__main__":
    run_lobster_final()
    time.sleep(10)
