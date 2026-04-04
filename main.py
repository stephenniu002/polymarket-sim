import os
import asyncio
import logging
import aiohttp
import time
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# 基础日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 核心常量配置 ---
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # Polygon USDC 合约
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", 60))
REPORT_INTERVAL = 300
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# --- Telegram 推送逻辑 ---
async def tg_notify(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10) as resp:
                if resp.status != 200:
                    logging.error(f"TG 推送失败: {await resp.text()}")
    except Exception as e:
        logging.error(f"TG 网络异常: {e}")

# --- 初始化 SDK 客户端 (0.34.6 适配) ---
def get_client():
    try:
        # 初始化基础客户端
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=os.getenv("POLY_PRIVATE_KEY"),
            chain_id=POLYGON,
            signature_type=2, # Gnosis Safe 代理钱包模式
            funder=os.getenv("POLY_ADDRESS")
        )
        # 显式注入 API 凭证对象
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
    """获取实盘账户 0x365B... 的 USDC 余额"""
    if not client: return 0.0
    try:
        # 适配 0.34.6：弃用 get_collateral_balance，改用 get_token_balance
        resp = await run_sync(client.get_token_balance, USDC_ADDRESS)
        # 新版 SDK 可能直接返回数值字符串，或带 balance 键的字典
        if isinstance(resp, dict):
            return round(float(resp.get("balance", 0)), 2)
        return round(float(resp), 2)
    except Exception as e:
        logging.error(f"❌ 余额查询异常: {e}")
        return 0.0

async def get_live_token(asset):
    """动态搜索 Polymarket 最新的价格预测 Token ID"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 10}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                # 过滤逻辑：匹配资产名 + "above" (预测价格上涨盘)
                valid = [m for m in data if asset.lower() in m.get("question", "").lower() 
                         and "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
                if valid:
                    # 优先选择成交量最大的活跃盘
                    m = max(valid, key=lambda x: float(x.get("volume", 0)))
                    return m.get("clobTokenIds")[0], m.get("question")
    except Exception as e:
        logging.error(f"❌ 动态扫描 {asset} 异常: {e}")
    return None, None

async def execute_trade(token_id, asset_name, price=0.5, size=ORDER_SIZE):
    """执行实盘下单动作"""
    if not client: return "❌ 下单失败：客户端未就绪"
    try:
        # 下单流程：创建参数 -> 签名 -> 提交
        order_args = await run_sync(client.create_order, price=float(price), size=float(size), side="buy", token_id=str(token_id))
        signed = await run_sync(client.sign_order, order_args)
        resp = await run_sync(client.place_order, signed)
        
        if resp.get("success"):
            return f"✅ 下单成功: {asset_name} | {size} USDC"
        return f"⚠️ 下单响应异常: {resp}"
    except Exception as e:
        return f"❌ {asset_name} 交易执行报错: {e}"

# --- 主巡检流程 ---

async def process_round():
    balance = await get_balance()
    logging.info(f"💰 [实盘状态] 账户余额: {balance} USDC")
    
    if balance < ORDER_SIZE:
        return [f"⚠️ 余额不足 ({balance} USDC)，跳过本轮下单"]

    results = []
    for asset in ASSETS:
        token_id, question = await get_live_token(asset)
        if token_id:
            logging.info(f"📡 监测中: {question}")
            # --- 实盘开火逻辑 ---
            # 如果只想监控不花钱，请注释掉下面两行
            res = await execute_trade(token_id, asset)
            results.append(res)
            # -----------------
            await asyncio.sleep(1) # 下单频率控制
        else:
            logging.warning(f"⚠️ {asset} 目前无匹配的活跃盘口")
    
    return results

async def periodic_report():
    """5分钟一次的 Telegram 状态汇报"""
    while True:
        await asyncio.sleep(REPORT_INTERVAL)
        balance = await get_balance()
        msg = f"📊 【龙虾巡航汇报】\n实盘余额: {balance} USDC\n系统状态: 运行中 🦞"
        await tg_notify(msg)

async def main_loop():
    logging.info("🚀 龙虾实盘系统 V4.5 启动中...")
    await tg_notify("🚀 龙虾实盘系统 V4.5 (SDK 0.34.6 对齐版) 已上线！")
    
    # 启动后台汇报任务
    asyncio.create_task(periodic_report())
    
    while True:
        try:
            results = await process_round()
            if results:
                await tg_notify("🔄 本轮巡检结果:\n" + "\n".join(results))
            
            logging.info(f"⏱ 本轮结束，{LOOP_INTERVAL}s 后进行下一轮...")
            await asyncio.sleep(LOOP_INTERVAL)
        except Exception as e:
            logging.error(f"⚠️ 主循环异常崩溃: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
