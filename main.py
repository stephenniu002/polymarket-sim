import os
import asyncio
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from market import fetch_latest_market_map # 确保根目录有此文件

# --- 1. 基础配置与 TG 播报 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(msg):
    if TG_TOKEN and TG_CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_CHAT_ID, "text": f"🦞 龙虾 V15 实盘:\n{msg}"}, timeout=5)
        except Exception as e:
            logging.error(f"TG 发送失败: {e}")

# --- 2. 客户端初始化 (适配 2026 规范) ---
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

# 初始化时直接绑定 Funder (Proxy) 身份
client = ClobClient(
    host="https://clob.polymarket.com",
    key=SIGNER_PK,
    chain_id=POLYGON,
    signature_type=2, 
    funder=FUNDER
)

client.set_api_creds(ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
))

# --- 3. 稳健余额审计 (解决 0.0 问题) ---
async def get_balance_safe():
    try:
        # 获取 USDC.e 余额 (Polymarket 合约抵押品)
        resp = await asyncio.to_thread(client.get_collateral_balance)
        logging.info(f"🔍 余额审计返回: {resp}")
        
        if isinstance(resp, dict):
            return float(resp.get("balance", 0) or resp.get("available", 0))
        return float(resp or 0.0)
    except Exception as e:
        logging.error(f"❌ 余额读取失败: {e}")
        return 0.0

# --- 4. 2026 新版下单指令 (移除 sign_order / place_order) ---
async def execute_trade(token_id, title, price=0.2):
    """
    使用新版 post_order 接口进行捡漏挂单
    """
    try:
        # A. 构造参数对象
        order_args = OrderArgs(
            price=float(price),
            size=1.0,  # 每次买 1 份
            side="buy",
            token_id=str(token_id)
        )

        def _do_post():
            # 💡 核心修复：新版 SDK 下，create_order 内部已包含自动签名
            signed_order = client.create_order(order_args)
            # 💡 核心修复：用 post_order 并指定订单类型 (GTC: 永久有效直至成交)
            return client.post_order(signed_order, OrderType.GTC)

        res = await asyncio.to_thread(_do_post)
        
        if res and res.get("success"):
            msg = f"🎯 下单成功！\n市场: {title}\n价格: {price} USDC\nID: {res.get('orderID')}"
            logging.info(msg)
            send_tg(msg)
            return True
        else:
            logging.warning(f"📥 下单被拒: {res.get('errorMsg') or res}")
            return False
            
    except Exception as e:
        err_str = str(e)
        logging.error(f"❌ 下单逻辑崩溃: {err_str}")
        return False

# --- 5. 主程序逻辑 ---
async def main():
    logging.info("🚀 龙虾 V15 实盘引擎就绪")
    send_tg("系统启动：正在进行 7 路币种捡漏扫描...")
    
    last_report_time = time.time()

    while True:
        try:
            # 1. 刷新余额（确认 USDC.e 是否到账）
            balance = await get_balance_safe()
            logging.info(f"💰 当前账户余额: {balance} USDC.e")

            if balance < 0.1: # 降低门槛，方便测试
                logging.warning("🛑 余额不足，等待充值或结算中...")
                await asyncio.sleep(60)
                continue

            # 2. 动态获取 7 路猎物名单 (调用 market.py)
            market_map = fetch_latest_market_map()
            if not market_map:
                logging.warning("📡 正在重新锁定市场...")
                await asyncio.sleep(10)
                continue

            # 3. 遍历市场，尝试 0.2 捡漏下单
            for symbol, info in market_map.items():
                token_id = info["upTokenId"]
                title = info["name"]
                
                logging.info(f"🔎 扫描中: {symbol} | {title}")
                
                # 执行下单
                await execute_trade(token_id, title)
                
                # 频率控制：每单之间停顿一下
                await asyncio.sleep(2)

            # 4. 每 15 分钟报一次平安
            if time.time() - last_report_time > 900:
                send_tg(f"📊 定时报告\n当前余额: {balance} USDC.e\n扫描状态: 正常")
                last_report_time = time.time()

        except Exception as e:
            logging.error(f"🆘 循环异常: {e}")
            await asyncio.sleep(10)
        
        logging.info("💤 扫描轮次结束，60秒后重启...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"FATAL: {e}")
        time.sleep(10)
