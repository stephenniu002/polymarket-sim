import os
import asyncio
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType # 必须导入 OrderType
from market import fetch_latest_market_map # 确保 market.py 在同级目录

# --- 1. 基础配置与日志 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(msg):
    if TG_TOKEN and TG_CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_CHAT_ID, "text": f"🦞 V12 实盘日志:\n{msg}"}, timeout=5)
    except: pass

# --- 2. 客户端初始化 (2026 规范) ---
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

client = ClobClient(
    host="https://clob.polymarket.com",
    key=SIGNER_PK,
    chain_id=POLYGON,
    signature_type=2, # 2 代表使用 Funder(Proxy) 身份
    funder=FUNDER
)

client.set_api_creds(ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
))

# --- 3. 稳健余额审计 ---
async def get_balance_safe():
    try:
        # 0.34.6 版首选方法
        resp = await asyncio.to_thread(client.get_collateral_balance)
        logging.info(f"🔍 原始余额返回: {resp}")
        
        # 兼容处理：SDK 可能返回字符串或字典
        if isinstance(resp, dict):
            return float(resp.get("balance", 0) or resp.get("available", 0))
        return float(resp or 0)
    except Exception as e:
        logging.error(f"❌ 余额审计失败: {e}")
        return 0.0

# --- 4. 2026 新版下单逻辑 ---
async def place_sniping_order(token_id, title):
    """
    以 0.2 USDC 尝试捡漏下单
    """
    try:
        # A. 构造参数 (必须使用 OrderArgs 对象)
        order_args = OrderArgs(
            price=0.2,
            size=1.0,
            side="buy",
            token_id=str(token_id)
        )

        def _do_post():
            # B. 在 0.34.6 版中，create_order 已内置签名
            signed_order = client.create_order(order_args)
            # C. 使用 post_order 并指定 OrderType.GTC
            return client.post_order(signed_order, OrderType.GTC)

        res = await asyncio.to_thread(_do_post)
        
        if res and res.get("success"):
            msg = f"✅ 下单指令已确认！\n市场: {title}\n价格: 0.2 | 数量: 1.0"
            logging.info(msg)
            send_tg(msg)
        else:
            logging.warning(f"📥 下单反馈（非成功）: {res}")
            
    except Exception as e:
        err_msg = str(e)
        logging.error(f"❌ 下单过程崩溃: {err_msg}")
        send_tg(f"❌ 下单崩溃: {err_msg}")

# --- 5. 主程序入口 ---
async def main():
    logging.info("🚀 龙虾 V12 实盘引擎启动...")
    send_tg("系统上线：开始 0.2 USDC 7路捡漏循环")

    while True:
        try:
            # 1. 动态刷新 7 路猎物名单
            markets = fetch_latest_market_map()
            balance = await get_balance_safe()
            
            logging.info(f"📊 当前余额: {balance} USDC | 监控中: {list(markets.keys())}")

            if balance < 0.2:
                logging.warning("⚠️ 余额不足以支撑 0.2 的捡漏单，跳过此轮")
            else:
                # 2. 遍历市场进行捡漏挂单
                for symbol, info in markets.items():
                    # 这里可以加入你的 OrderFlow 逻辑，
