import os
import asyncio
import logging
import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 1:1 对齐 Railway 变量 ---
POLY_ADDRESS = os.getenv("POLY_ADDRESS")
POLY_PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
POLY_API_KEY = os.getenv("POLY_API_KEY")
POLY_PASSPHRASE = os.getenv("POLY_PASSPHRASE")
POLY_SECRET = os.getenv("POLY_SECRET")

# ⚠️ 注意这里：你截图里是小写的 signature_type
SIG_TYPE = int(os.getenv("signature_type", 2)) 

# ⚠️ 注意这里：你截图里分别是 TELEGRAM_CHAT_ID 和 TG_TOKEN
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 业务参数
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
LOOP_INTERVAL = 60 

async def tg_notify(message):
    if not TG_TOKEN or not TG_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": TG_CHAT_ID, "text": message}, timeout=10)
    except: pass

def get_client():
    try:
        # 使用 Railway 注入的变量初始化
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=POLY_PRIVATE_KEY,
            chain_id=POLYGON,
            signature_type=SIG_TYPE,
            funder=POLY_ADDRESS
        )
        creds = ApiCreds(
            api_key=POLY_API_KEY,
            api_secret=POLY_SECRET,
            api_passphrase=POLY_PASSPHRASE
        )
        client.set_api_creds(creds)
        logging.info("✅ Polymarket 客户端初始化成功")
        return client
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return None

client = get_client()

async def get_balance():
    """获取实盘余额：使用 0.34.6 版存在的 get_collateral_balance"""
    if not client: return 0.0
    try:
        # 使用你确认有效的 get_collateral_balance
        # 通过 asyncio.to_thread 包装防止阻塞
        resp = await asyncio.to_thread(client.get_collateral_balance)
        
        if isinstance(resp, dict):
            val = resp.get("balance", 0)
            return round(float(val), 2)
        return round(float(resp), 2)
    except Exception as e:
        logging.error(f"❌ 余额查询路径异常: {e}")
        return 0.0

async def get_live_target(asset):
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 5}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                valid = [m for m in data if asset.lower() in m.get("question", "").lower() 
                         and "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
                if valid:
                    m = max(valid, key=lambda x: float(x.get("volume", 0)))
                    return m.get("clobTokenIds")[0], m.get("question")
    except: return None, None

async def process_round():
    balance = await get_balance()
    logging.info(f"💰 [实盘巡检] 余额: {balance} USDC")
    
    # 如果余额显示为 0，给个明确的警告日志
    if balance <= 0:
        logging.warning(f"⚠️ 余额为 0，请确认 POLY_ADDRESS ({POLY_ADDRESS}) 是否正确")

    for asset in ASSETS:
        tid, q = await get_live_target(asset)
        if tid:
            logging.info(f"📡 监测中: {q}")
        await asyncio.sleep(1)

async def main_loop():
    logging.info("🚀 龙虾实盘 V5.2 (变量对齐版) 启动")
    await tg_notify("🚀 龙虾实盘 V5.2 已上线！正在同步 0x365B... 余额")
    
    while True:
        try:
            await process_round()
            await asyncio.sleep(LOOP_INTERVAL)
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
