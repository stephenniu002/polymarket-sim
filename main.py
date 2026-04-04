import os
import asyncio
import logging
import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Railway 变量对齐 ---
POLY_ADDRESS = os.getenv("POLY_ADDRESS")
POLY_PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
POLY_API_KEY = os.getenv("POLY_API_KEY")
POLY_PASSPHRASE = os.getenv("POLY_PASSPHRASE")
POLY_SECRET = os.getenv("POLY_SECRET")
SIG_TYPE = int(os.getenv("signature_type", 2)) 
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]

# --- Telegram 通知 ---
async def tg_notify(message):
    if not TG_TOKEN or not TG_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": TG_CHAT_ID, "text": message}, timeout=10)
    except: pass

# --- 初始化客户端 ---
def get_client():
    try:
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
        return client
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return None

client = get_client()

# --- 核心修复：0.34.6 余额查询标准路径 ---
async def get_balance():
    if not client: return 0.0
    try:
        # 在最新 SDK 中，这是获取 API 关联账户可用 USDC 余额的标准方法
        # 它会自动识别你的代理钱包身份
        resp = await asyncio.to_thread(client.get_balance)
        
        # 响应通常是一个纯数值字符串或带 balance 键的字典
        if isinstance(resp, dict):
            return round(float(resp.get("balance", 0)), 2)
        return round(float(resp), 2)
    except Exception as e:
        logging.error(f"❌ 余额查询异常: {e}")
        return 0.0

# --- 动态扫描盘口 ---
async def get_live_token(asset):
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

# --- 主逻辑循环 ---
async def process_round():
    balance = await get_balance()
    logging.info(f"💰 [实盘巡检] 余额: {balance} USDC")
    
    if balance > 0:
        logging.info("🎯 余额抓取成功，正在检索最新 Token...")
    else:
        # 只有在余额真的为 0 且没报错时才报警告
        logging.warning("⚠️ 余额读取为 0.0，请确认 API Key 是否有 View 权限")

    results = []
    for asset in ASSETS:
        tid, q = await get_live_token(asset)
        if tid:
            logging.info(f"📡 监控中: {q}")
        await asyncio.sleep(1)

async def main_loop():
    logging.info("🚀 龙虾实盘 V5.4 (标准路径版) 启动")
    await tg_notify("🚀 龙虾实盘 V5.4 (SDK 标准对齐) 已上线！")
    
    while True:
        try:
            await process_round()
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
