import os
import asyncio
import logging
import aiohttp
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 环境变量读取 ---
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", 60))    # 每轮轮询间隔
REPORT_INTERVAL = 300                                  # 每 5 分钟汇报一次
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# --- Telegram 推送 ---
async def tg_notify(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10) as resp:
                if resp.status != 200:
                    logging.error(f"Telegram 推送失败: {await resp.text()}")
    except Exception as e:
        logging.error(f"Telegram 网络异常: {e}")

# --- 初始化客户端 (同步转异步包装) ---
def get_client():
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=os.getenv("POLY_PRIVATE_KEY"),
            chain_id=POLYGON,
            signature_type=2,
            funder=os.getenv("POLY_ADDRESS")
        )
        creds = ApiCreds(
            api_key=os.getenv("POLY_API_KEY"),
            api_secret=os.getenv("POLY_SECRET"),
            api_passphrase=os.getenv("POLY_PASSPHRASE")
        )
        client.set_api_creds(creds)
        return client
    except Exception as e:
        logging.error(f"❌ 客户端初始化失败: {e}")
        return None

client = get_client()

async def run_sync_func(func, *args, **kwargs):
    """将 SDK 的同步调用包装在线程池中运行，防止阻塞 asyncio"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# --- 核心业务函数 ---

async def get_balance():
    if not client: return 0.0
    try:
        resp = await run_sync_func(client.get_collateral_balance, os.getenv("POLY_ADDRESS"))
        return round(float(resp.get("balance", 0)), 2)
    except Exception as e:
        logging.error(f"❌ 查询余额失败: {e}")
        return 0.0

async def get_live_token(asset):
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 10}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                # 寻找包含 asset 名称且包含 above 的 Yes Token
                valid = [m for m in data if asset.lower() in m.get("question", "").lower() 
                         and "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
                if valid:
                    # 选成交量最大的
                    m = max(valid, key=lambda x: float(x.get("volume", 0)))
                    return m.get("clobTokenIds")[0], m.get("question")
    except Exception as e:
        logging.error(f"❌ 获取 {asset} token_id 异常: {e}")
    return None, None

async def execute_trade(token_id, asset_name, price=0.5, size=ORDER_SIZE):
    if not client: return "❌ 客户端未就绪"
    try:
        # 下单流程：创建 -> 签名 -> 发送
        order_args = await run_sync_func(client.create_order, price=price, size=size, side="buy", token_id=token_id)
        signed_order = await run_sync_func(client.sign_order, order_args)
        result = await run_sync_func(client.place_order, signed_order)
        
        msg = f"✅ {asset_name} 下单成功！\n💰 金额: {size} USDC\n🎯 目标: {token_id[:10]}..."
        logging.info(msg)
        return msg
    except Exception as e:
        msg = f"❌ {asset_name} 下单失败: {e}"
        logging.error(msg)
        return msg

# --- 任务循环 ---

async def process_round():
    balance = await get_balance()
    logging.info(f"💰 轮询检查 - 当前余额: {balance} USDC")
    
    if balance < ORDER_SIZE:
        return [f"⚠️ 余额 ({balance} USDC) 低于设定下单量 {ORDER_SIZE}，本轮跳过"]

    results = []
    # 这里我们采用并发抓取 Token，但顺序下单防止风控
    for asset in ASSETS:
        token_id, question = await get_live_token(asset)
        if token_id:
            logging.info(f"📡 发现目标: {question}")
            # 执行下单 (生产环境建议加信号判断，这里是全自动下单逻辑)
            res = await execute_trade(token_id, asset)
            results.append(res)
            await asyncio.sleep(1) # 下单间隔
        else:
            logging.warning(f"⚠️ {asset} 暂无活跃盘口")
    
    return results

async def periodic_report():
    while True:
        await asyncio.sleep(REPORT_INTERVAL)
        balance = await get_balance()
        await tg_notify(f"📊 【龙虾定时汇报】\n当前实盘余额: {balance} USDC\n系统运行正常 🦞")

async def main_loop():
    await tg_notify("🚀 龙虾实盘系统 V4.4 (全异步版) 启动")
    
    # 启动汇报协程
    asyncio.create_task(periodic_report())
    
    while True:
        try:
            results = await process_round()
            if results:
                # 过滤并合并通知
                full_msg = "\n".join(results)
                await tg_notify(f"🔄 本轮巡检结果:\n{full_msg}")
            
            logging.info(f"⏱ 轮询结束，等待 {LOOP_INTERVAL} 秒...")
            await asyncio.sleep(LOOP_INTERVAL)
        except Exception as e:
            logging.error(f"⚠️ 循环崩溃重新拉起: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 系统手动停止")
