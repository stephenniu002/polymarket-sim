import os
import logging
import time
import json
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

def run_lobster_final_defense():
    logger.info("🚀 [Lobster] 启动深度解析防御版...")
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    
    try:
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # 1. 扫描市场
        markets_resp = client.get_markets()
        
        # 如果 resp 直接是字符串，说明 API 报错
        if isinstance(markets_resp, str):
            logger.error(f"⚠️ API 返回了错误文本: {markets_resp}")
            send_tg_message(f"⚠️ API 报错: `{markets_resp}`")
            return

        target_token_id = None
        market_name = ""

        # 2. 深度防御循环
        for m in markets_resp:
            # --- 核心修正：如果 m 是字符串，尝试将其解析为字典 ---
            current_market = m
            if isinstance(m, str):
                try:
                    current_market = json.loads(m)
                except:
                    continue # 解析失败则跳过

            # 确保现在拿到的 current_market 是字典
            if not isinstance(current_market, dict):
                continue
            
            q_text = str(current_market.get('question', '')).lower()
            is_active = current_market.get('active') is True
            
            # 匹配 BTC 或 Bitcoin
            if ('btc' in q_text or 'bitcoin' in q_text) and is_active:
                tokens = current_market.get('tokens', [])
                if isinstance(tokens, list) and len(tokens) >= 2:
                    first_token = tokens[0]
                    # 处理 token 也是字符串的情况
                    if isinstance(first_token, str):
                        try: first_token = json.loads(first_token)
                        except: continue
                    
                    if isinstance(first_token, dict):
                        target_token_id = first_token.get('token_id')
                        market_name = current_market.get('question')
                        break

        # 3. 兜底方案：如果找不到 BTC，找任意活跃市场
        if not target_token_id and isinstance(markets_resp, list):
            for m in markets_resp:
                curr = json.loads(m) if isinstance(m, str) else m
                if isinstance(curr, dict) and curr.get('active'):
                    tks = curr.get('tokens', [])
                    if isinstance(tks, list) and len(tks) >= 2:
                        target_token_id = tks[0].get('token_id') if isinstance(tks[0], dict) else None
                        market_name = "[测试]" + str(curr.get('question', '未知'))
                        if target_token_id: break

        if not target_token_id:
            logger.error("❌ 无法从 API 响应中提取有效的 Token ID")
            return

        # 4. 执行下单 (0.11U 低价)
        order = OrderArgs(price=0.11, size=1.0, side="BUY", token_id=target_token_id)
        logger.info(f"🎯 目标锁定: {market_name} | 正在下单...")
        
        resp = client.create_order(order)

        # 下单结果也做同样防御
        final_resp = json.loads(resp) if isinstance(resp, str) else resp
        if isinstance(final_resp, dict) and final_resp.get("success"):
            order_id = final_resp.get('orderID')
            send_tg_message(f"✅ *【下单成功】*\n市场: {market_name}\nID: `{order_id}`")
            logger.info(f"✅ 成功! ID: {order_id}")
        else:
            logger.warning(f"⚠️ 下单响应: {final_resp}")
            send_tg_message(f"⚠️ 下单响应异常: `{final_resp}`")

    except Exception as e:
        logger.error(f"🔥 最终防御崩溃: {str(e)}")
        send_tg_message(f"🔥 崩溃: {str(e)}")

if __name__ == "__main__":
    run_lobster_final_defense()
    time.sleep(10)
