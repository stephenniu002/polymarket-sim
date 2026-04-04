import os
import asyncio
import logging
import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 配置 ---
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", 60))
REPORT_INTERVAL = 300
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")
POLY_ADDRESS = os.getenv("POLY_ADDRESS")

# --- Telegram 推送 ---
async def tg_notify(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        logging.error(f"TG 通知失败: {e}")

# --- 初始化客户端 ---
def get_client():
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=os.getenv("POLY_PRIVATE_KEY"),
            chain_id=POLYGON,
            signature_type=2,
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
        logging.error(f"❌ 客户端初始化失败: {e}")
        return None

client = get_client()

# --- 核心业务逻辑 (使用 asyncio.to_thread 包装同步 SDK) ---

async def get_balance():
    """获取实盘余额：使用正确的 get_collateral_balance"""
    if not client: return 0.0
    try:
        # 使用 to_thread 异步执行同步方法
        resp = await asyncio.to_thread(client.get_collateral_balance, POLY_ADDRESS)
        # 兼容字典返回格式
        balance = round(float(resp.get("balance", 0)), 2)
        return balance
    except Exception as e:
        logging.error(f"❌ 余额查询异常: {e}")
        return 0.0

async def get_live_token(asset):
    """动态获取最新的 Token ID"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 10}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                valid = [m for m in data if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
                if valid:
                    m = max(valid, key=lambda x: float(x.get("volume", 0)))
                    return m.get("clobTokenIds")[0], m.get("question")
    except: return None, None

async def execute_trade(token_id, asset_name):
    """实盘下单"""
    if not client: return "❌ 客户端未就绪"
    try:
        # 依次异步执行同步的下单步骤
        order_args = await asyncio.to_thread(client.create_order, price=0.5, size=ORDER_SIZE, side="buy", token_id=str(token_id))
        signed = await asyncio.to_thread(client.sign_order, order_args)
        resp = await asyncio.to_thread(client.place_order, signed)
        
        if resp.get("success"):
            return f"✅ {asset_name} 下单成功"
        return f"⚠️ {asset_name} 响应异常: {resp}"
    except Exception as e:
        return f"❌ {asset_name} 下单报错: {e}"

# --- 循环流程 ---

async def process_round():
    balance = await get_balance()
    logging.info(f"💰 [实盘状态] 账户余额: {balance} USDC")
    
    if balance < ORDER_SIZE:
        return [f"⚠️ 余额 ({balance}) 低于下单量 {ORDER_SIZE}，本轮跳过"]

    results = []
    for asset in ASSETS:
        tid, q = await get_live_token(asset)
        if tid:
            logging.info(f"📡 监控中: {q}")
            # 实盘测试下单（如需纯监控请注释下两行）
            # res = await execute_trade(tid, asset)
            # results.append(res)
            await asyncio.sleep(1) 
    return results

async def periodic_report():
    """5分钟一次的 Telegram 余额汇报"""
    while True:
        await asyncio.sleep(REPORT_INTERVAL)
        balance = await get_balance()
        await tg_notify(f"📊 【龙虾定时汇报】\n当前余额: {balance} USDC\n系统监控中... 🦞")

async def main_loop():
    logging.info("🚀 龙虾实盘系统 V4.8 启动...")
    await tg_notify("🚀 龙虾实盘系统 V4.8 (余额修正版) 已上线！")
    
    asyncio.create_task(periodic_report())
    
    while True:
        try:
            results = await process_round()
            if results:
                await tg_notify("🔄 本轮巡检结果:\n" + "\n".join(results))
            
            await asyncio.sleep(LOOP_INTERVAL)
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
