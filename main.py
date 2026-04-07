import os
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs

# 1. 基础配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_tg_message(text):
    """电报实时推送"""
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except: pass

def run_lobster_final_strike():
    logger.info("🚀 [Lobster] 正在执行 2.39U 余额实战下单...")
    PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
    
    try:
        # 初始化客户端
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        
        # --- 步骤 1: 安全获取市场列表 ---
        markets_resp = client.get_markets()
        
        # 拦截常见的字符串报错 (如 "Unauthorized", "Forbidden")
        if isinstance(markets_resp, str):
            err_msg = f"❌ API 鉴权失败或受限: `{markets_resp}`\n请检查 API Key 权限！"
            logger.error(err_msg)
            send_tg_message(err_msg)
            return

        # 确保拿到的是列表
        if not isinstance(markets_resp, list):
            logger.error(f"❌ 预期 List，实际得到: {type(markets_resp)}")
            return

        target_token_id = None
        market_name = ""

        # --- 步骤 2: 遍历匹配 ---
        for m in markets_resp:
            if not isinstance(m, dict): continue
            
            q_text = str(m.get('question', '')).lower()
            # 锁定活跃的 BTC 市场
            if ('btc' in q_text or 'bitcoin' in q_text) and m.get('active') is True:
                tokens = m.get('tokens', [])
                if isinstance(tokens, list) and len(tokens) >= 2:
                    if isinstance(tokens[0], dict):
                        target_token_id = tokens[0].get('token_id')
                        market_name = m.get('question')
                        break

        # --- 步骤 3: 兜底逻辑 (找不到 BTC 就找任意活跃市场测试) ---
        if not target_token_id:
            logger.warning("⚠️ 未找到 BTC 市场，改用当前最热门活跃市场测试链路...")
            for m in markets_resp:
                if not isinstance(m, dict) or m.get('active') is not True: continue
                tokens = m.get('tokens', [])
                if isinstance(tokens, list) and len(tokens) >= 2:
                    target_token_id = tokens[0].get('token_id')
                    market_name = "[备选]" + str(m.get('question', '未知'))
                    break

        if not target_token_id:
            logger.error("❌ 全网未找到可下单市场")
            return

        # --- 步骤 4: 执行 1U 下单 (使用 0.11U 的价格确保成功) ---
        order = OrderArgs(price=0.11, size=1.0, side="BUY", token_id=target_token_id)
        logger.info(f"🎯 锁定: {market_name} | 正在提交 1.0U 订单...")
        
        resp = client.create_order(order)

        # 再次对下单结果做类型检查
        if isinstance(resp, str):
            logger.error(f"❌ 下单 API 拒收: {resp}")
            send_tg_message(f"❌ 下单失败: `{resp}`")
        elif isinstance(resp, dict) and resp.get("success"):
            order_id = resp.get('orderID')
            logger.info(f"✅ 下单成功! ID: {order_id}")
            send_tg_message(f"✅ *【下单成功】*\n📈 市场: {market_name}\n📜 订单ID: `{order_id}`")
        else:
            logger.warning(f"⚠️ 下单响应异常: {resp}")
            send_tg_message(f"⚠️ 响应不明确: `{resp}`")

    except Exception as e:
        error_str = f"🔥 运行时崩溃: {str(e)}"
        logger.error(error_str)
        send_tg_message(error_str)

if __name__ == "__main__":
    run_lobster_final_strike()
    time.sleep(10)
