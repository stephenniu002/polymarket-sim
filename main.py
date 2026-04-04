import os
import asyncio
import logging
import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 核心常量配置 ---
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
# Polygon 链上的 USDC 合约地址
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" 
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", 60))
REPORT_INTERVAL = 300
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# --- Telegram 推送逻辑 ---
async def tg_notify(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        logging.error(f"TG 推送异常: {e}")

# --- 初始化 SDK 客户端 (适配 0.34.6) ---
def get_client():
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=os.getenv("POLY_PRIVATE_KEY"),
            chain_id=POLYGON,
            signature_type=2, # Gnosis Safe 代理模式
            funder=os.getenv("POLY_ADDRESS")
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
        logging.error(f"❌ 客户端初始化崩溃: {e}")
        return None

client = get_client()

# --- 异步运行同步 SDK 方法的包装器 ---
async def run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# --- 核心业务逻辑 ---

async def get_balance():
    """获取 0x365B... 账户的 USDC 余额"""
    if not client: return 0.0
    try:
        # ⚠️ 关键点：0.34.6 弃用了 get_collateral_balance，改用 get_token_balance
        resp = await run_sync(client.get_token_balance, USDC_ADDRESS)
        
        # 新版可能返回字典或纯数值字符串
        if isinstance(resp, dict):
            return round(float(resp.get("balance", 0)), 2)
        return round(float(resp), 2)
    except Exception as e:
        # 如果还是不行，尝试最后的备选方案 get_funder_balance
        try:
            resp = await run_sync(client.get_funder_balance)
            return round(float(resp), 2)
        except:
            logging.error(f"❌ 余额查询彻底失败: {e}")
            return 0.0

async def get_live_token(asset):
    """动态搜索最新 Token ID"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 10}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                valid = [m for m in data if asset.lower() in m.get("question", "").lower() 
                         and "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
                if valid:
                    m = max(valid, key=lambda x: float(x.get("volume", 0)))
                    return m.get("clobTokenIds")[0], m.get("question")
    except Exception as e:
        logging.error(f"❌ 扫描 {asset} 异常: {e}")
    return None, None

async def execute_trade(token_id, asset_name):
    """执行实盘下单"""
    if not client: return "❌ 客户端未就绪"
    try:
        # 下单流程
        order_args = await run_sync(client.create_order, price=0.5, size=ORDER_SIZE, side="buy", token_id=str(token_id))
        signed = await run_sync(client.sign_order, order_args)
        resp = await run_sync(client.place_order, signed)
        
        if resp.get("success"):
            return f"✅ {asset_name} 下单成功！"
        return f"⚠️ 下单异常: {resp}"
    except Exception as e:
        return f"❌ {asset_name} 报错: {e}"

# --- 主巡检流程 ---

async def process_round():
    balance = await get_balance()
    logging.info(f"💰 [实盘巡检] 余额: {balance} USDC")
    
    if balance < ORDER_SIZE:
        return [f"⚠️ 余额 ({balance}) 不足 {ORDER_SIZE}，本轮跳过"]

    results = []
    for asset in ASSETS:
        token_id, question = await get_live_token(asset)
        if token_id:
            logging.info(f"📡 监测中: {question}")
            # 实盘测试时开启：
            # res = await execute_trade(token_id, asset)
            # results.append(res)
            await asyncio.sleep(1)
    return results

async def main_loop():
    await tg_notify("🚀 龙虾实盘系统 V4.6 已上线！")
    while True:
        try:
            results = await process_round()
            if results:
                await tg_notify("🔄 巡检结果:\n" + "\n".join(results))
            await asyncio.sleep(LOOP_INTERVAL)
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
