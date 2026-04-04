import os
import asyncio
import logging
import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 核心配置 ---
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", 60))
POLY_ADDRESS = os.getenv("POLY_ADDRESS")
SIGNATURE_TYPE = 2 

async def tg_notify(message):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    except: pass

def get_client():
    try:
        # 注意：0.34.6 版本的初始化参数顺序非常严格
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=os.getenv("POLY_PRIVATE_KEY"),
            chain_id=POLYGON,
            signature_type=SIGNATURE_TYPE,
            funder=POLY_ADDRESS
        )
        creds = ApiCreds(
            api_key=os.getenv("POLY_API_KEY"),
            api_secret=os.getenv("POLY_SECRET"),
            api_passphrase=os.getenv("POLY_PASSPHRASE")
        )
        client.set_api_creds(creds)
        logging.info("✅ Polymarket 客户端初始化成功")
        return client
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return None

client = get_client()

async def get_balance():
    """获取实盘余额：使用 0.34.6 版唯一存在的 get_collateral_balance"""
    if not client: return 0.0
    try:
        # ⚠️ 关键修正：不再调用不存在的 get_token_balance 或 get_balance
        # 使用 to_thread 包装同步调用，防止卡死
        resp = await asyncio.to_thread(client.get_collateral_balance)
        
        if isinstance(resp, dict):
            val = resp.get("balance", 0)
            return round(float(val), 2)
        return round(float(resp), 2)
    except Exception as e:
        logging.error(f"❌ 余额查询路径崩溃: {e}")
        return 0.0

async def get_live_target(asset):
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 5}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                valid = [m for m in data if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
                if valid:
                    m = max(valid, key=lambda x: float(x.get("volume", 0)))
                    return m.get("clobTokenIds")[0], m.get("question")
    except: return None, None

async def process_round():
    balance = await get_balance()
    logging.info(f"💰 [实盘状态] 账户余额: {balance} USDC")
    
    if balance < 1.0:
        logging.warning("⚠️ 余额读取为 0 或过低，请检查 POLY_ADDRESS 是否为代理钱包地址")
        return

    for asset in ASSETS:
        tid, q = await get_live_target(asset)
        if tid:
            logging.info(f"📡 监测中: {q}")
        await asyncio.sleep(1)

async def main_loop():
    logging.info("🚀 龙虾实盘系统 V5.1 (对齐补丁) 启动")
    await tg_notify("🚀 龙虾实盘系统 V5.1 (余额修复) 已上线！")
    
    while True:
        try:
            await process_round()
            await asyncio.sleep(LOOP_INTERVAL)
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
