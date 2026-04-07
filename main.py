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
    logger.info("🚀 [Lobster] 启动全兼容扫描模式...")
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    
    try:
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 1. 扫描市场
        markets_resp = client.get_markets()
        if isinstance(markets_resp, str):
            logger.error(f"❌ API 报错: {markets_resp}")
            return

        target_token_id = None
        market_name = ""

        # 2. 更加宽泛的匹配逻辑
        for m in markets_resp:
            if not isinstance(m, dict): continue
            
            # 综合检查标题和描述
            q_text = str(m.get('question', '')).lower()
            d_text = str(m.get('description', '')).lower()
            is_active = m.get('active') is True
            
            # 只要包含 BTC/Bitcoin 且活跃就锁定
            if ('btc' in q_text or 'bitcoin' in q_text or 'btc' in d_text) and is_active:
                tokens = m.get('tokens', [])
                if len(tokens) >= 2:
                    target_token_id = tokens[0]['token_id']
                    market_name = m.get('question')
                    logger.info(f"✅ 找到 BTC 市场: {market_name}")
                    break

        # 3. 如果依然没找到 BTC，就拿第一个活跃市场祭天（测试链路）
        if not target_token_id and markets_resp:
            for m in markets_resp:
                if m.get('active') and len(m.get('tokens', [])) >= 2:
                    target_token_id = m['tokens'][0]['token_id']
                    market_name = "[紧急备选]" + m.get('question', '未知市场')
                    logger.warning(f"⚠️ 未找到 BTC，改用备选市场: {market_name}")
                    break

        if not target_token_id:
            logger.error("❌ 全网未找到任何可交易的活跃市场")
            return

        # 4. 执行下单 (0.11U 低价测试)
        order = OrderArgs(price=0.11, size=1.0, side="BUY", token_id=target_token_id)
        logger.info(f"📡 正在下单: {market_name}...")
        
        resp = client.create_order(order)

        if isinstance(resp, str):
            send_tg_message(f"❌ 下单 API 拒收: `{resp}`")
        elif resp.get("success"):
            order_id = resp.get('orderID')
            send_tg_message(f"✅ *【下单成功】*\n市场: {market_name}\nID: `{order_id}`")
            logger.info(f"✅ 成功! ID: {order_id}")
        else:
            logger.warning(f"⚠️ 响应: {resp}")

    except Exception as e:
        logger.error(f"🔥 崩溃: {str(e)}")
        send_tg_message(f"🔥 崩溃: {str(e)}")

if __name__ == "__main__":
    run_lobster_final()
    time.sleep(10)
