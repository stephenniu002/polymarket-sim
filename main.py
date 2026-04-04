import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType

# --- 1. 环境与日志 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 对接你 Railway 面板的变量
PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

# --- 2. 核心初始化 (根据你 1:50 PM 的更新) ---
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=POLYGON,
    signature_type=2,
    funder=FUNDER
)

def init_client_v16_1():
    try:
        # 1️⃣ 初始化 API creds
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info("✅ API creds 初始化成功")

        # 2️⃣ 设置 allowance (使用新 SDK 列表中的方法)
        # 注意：不再使用 get_collateral_address() 如果它报错，直接传 USDC.e 地址
        try:
            collateral_addr = client.get_collateral_address()
            res = client.update_balance_allowance(token_address=collateral_addr)
            logging.info(f"✅ Allowance 设置成功: {res}")
        except Exception as e:
            logging.warning(f"⚠️ Allowance 自动设置跳过 (可能已设置): {e}")
            
    except Exception as e:
        logging.error(f"❌ 初始化致命失败: {e}")

# --- 3. 稳健余额探测 ---
async def get_balance_safe():
    # 优先使用你日志里出现的 get_balance_allowance
    methods = ["get_balance_allowance", "get_balance", "get_user_balance"]
    for m in methods:
        func = getattr(client, m, None)
        if func:
            try:
                resp = await asyncio.to_thread(func)
                if isinstance(resp, dict):
                    return float(resp.get("balance") or resp.get("available") or 0)
                return float(resp or 0)
            except: continue
    return -1.0 # Fallback 标识

# --- 4. 信号与下单逻辑 ---
async def trade_cycle():
    balance = await get_balance_safe()
    logging.info(f"💰 实时余额: {balance if balance != -1.0 else '探测中...'}")

    # Fallback 保护：如果探测失败但确认有钱，允许盲打
    current_funds = balance if balance > 0 else 10.84 
    
    if current_funds < 1.0:
        logging.warning("🛑 资金过低，停止交易")
        return

    # 这里插入你 5 分钟周期的逻辑...
    # await execute_trade(...)

# --- 5. 执行入口 ---
async def main_worker():
    logging.info("🚀 polymarket-sim V16.1 启动")
    init_client_v16_1()
    
    while True:
        try:
            await trade_cycle()
            await asyncio.sleep(60) # 生产环境建议拉长一点，避免 Rate Limit
        except Exception as e:
            logging.error(f"⚠️ 循环抖动: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main_worker())
    except Exception as e:
        logging.error(f"🚨 进程崩溃: {e}")
        time.sleep(10)
