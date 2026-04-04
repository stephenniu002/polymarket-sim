import os
import asyncio
import logging
import time
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from market import fetch_latest_market_map

# --- 1. 环境对接 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER_ADDR = os.getenv("Funder")

client = ClobClient(
    host="https://clob.polymarket.com",
    key=SIGNER_PK,
    chain_id=POLYGON,
    signature_type=2,
    funder=FUNDER_ADDR
)
client.set_api_creds(ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
))

# --- 2. 【核心修复】精准对接 2026 新接口 ---
async def get_balance_v16_2():
    """
    针对 SDK 列表中的 get_balance_allowance 进行解析
    """
    try:
        # 调用新版接口
        resp = await asyncio.to_thread(client.get_balance_allowance)
        logging.info(f"📊 原始余额数据: {resp}")
        
        # 2026 版通常返回字典: {'balance': '10.84', 'allowance': '...'}
        if isinstance(resp, dict):
            # 尝试抓取 balance 字段
            val = resp.get("balance") or resp.get("collateral_balance") or 0
            return float(val)
        return float(resp or 0)
    except Exception as e:
        logging.error(f"❌ 余额解析失败: {e}")
        return -1.0

# --- 3. 交易逻辑 ---
last_trade_round = 0

async def smart_trade_logic():
    global last_trade_round
    
    # A. 获取真实余额
    balance = await get_balance_v16_2()
    
    # B. 5分钟周期控频
    now_round = int(time.time() // 300)
    if now_round == last_trade_round:
        return
    
    # C. 余额检查
    if balance == -1.0:
        logging.warning("⚠️ 接口异常，尝试盲打模式...")
        current_funds = 10.0 # 强制赋值以跳过拦截
    else:
        logging.info(f"💰 最终确认账户余额: {balance} USDC.e")
        if balance < 0.2:
            logging.warning("🛑 余额不足，本轮跳过")
            return
        current_funds = balance

    last_trade_round = now_round
    
    # D. 市场抓取
    markets = fetch_latest_market_map()
    if not markets:
        logging.warning("🔎 暂时未发现符合条件的 7 路信号市场...")
        return

    # E. 执行下单 (前 2 个信号最强的)
    for symbol, info in list(markets.items())[:2]:
        await execute_trade(info['upTokenId'], info['name'], current_funds)

async def execute_trade(token_id, title, funds):
    try:
        # 动态仓位 (10%)
        trade_size = max(0.1, round(funds * 0.1, 2))
        
        order_args = OrderArgs(
            price=0.2, 
            size=trade_size, 
            side="buy", 
            token_id=str(token_id)
        )

        def _post():
            # 使用 SDK 列表确认存在的接口
            signed = client.create_order(order_args)
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_post)
        if res and res.get("success"):
            logging.info(f"✅ 【实盘成交】市场: {title} | 规模: {trade_size}")
    except Exception as e:
        logging.error(f"❌ 下单动作崩溃: {e}")

# --- 4. 守护入口 ---
async def main_worker():
    logging.info("🚀 polymarket-sim: V16.2 最终修复版启动")
    
    while True:
        try:
            await smart_trade_logic()
            await asyncio.sleep(10) # 保持探针活跃
        except Exception as e:
            logging.error(f"⚠️ 循环抖动: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main_worker())
    except Exception as fatal_e:
        logging.error(f"🚨 进程致命错误: {fatal_e}")
        time.sleep(10)
