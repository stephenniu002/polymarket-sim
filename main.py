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

def run_lobster_brute_force():
    logger.info("🚀 [Lobster] 启动暴力成交测试版...")
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    
    try:
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 1. 直接获取最新的活跃抽样市场
        markets = client.get_markets()
        if not isinstance(markets, list):
            logger.error(f"❌ API 响应异常: {markets}")
            return

        # 2. 暴力寻找第一个可以下单的市场
        target_token = None
        target_name = ""
        
        for m in markets:
            if not isinstance(m, dict) or not m.get('active'):
                continue
            
            # 兼容不同版本的 token 提取逻辑
            tokens = m.get('tokens')
            if isinstance(tokens, list) and len(tokens) >= 2:
                # 尝试拿 YES Token (通常是第一个)
                token_data = tokens[0]
                if isinstance(token_data, dict) and token_data.get('token_id'):
                    target_token = token_data.get('token_id')
                    target_name = m.get('question', '未知市场')
                    break

        if not target_token:
            # 最后的倔强：手动注入一个目前极大概率活跃的 BTC 市场 Token ID
            # 这是 BTC Price Above $75,000 (April) 的一个活跃 Token
            target_token = "2160570535948011270222047814234033054170853757422116260846067756701831818224"
            target_name = "[强制注入] BTC 活跃市场"

        # 3. 构造 1U 测试单 (价格 0.11 确保大概率能挂单成功)
        order = OrderArgs(
            price=0.11,
            size=1.0,
            side="BUY",
            token_id=target_token
        )

        logger.info(f"📡 正在尝试对市场 [{target_name}] 下单...")
        resp = client.create_order(order)

        # 4. 结果处理
        if isinstance(resp, dict) and resp.get("success"):
            order_id = resp.get('orderID')
            msg = f"✅ *【下单成功！】*\n市场: {target_name}\nID: `{order_id}`"
            logger.info(msg)
            send_tg_message(msg)
        else:
            err = f"⚠️ 下单未直接成功，响应: `{resp}`"
            logger.warning(err)
            # 如果是鉴权问题，电报会收到具体的报错
            send_tg_message(err)

    except Exception as e:
        error_str = f"🔥 运行时崩溃: {str(e)}"
        logger.error(error_str)
        send_tg_message(error_str)

if __name__ == "__main__":
    run_lobster_brute_force()
    time.sleep(10)
