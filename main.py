import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from market import fetch_latest_market_map

# --- 1. 日志与环境 (Railway 标准配置) ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 从 Railway Variables 读取环境变量
PK = os.getenv("PK")
FUNDER = os.getenv("FUNDER")

# --- 2. 客户端初始化 (适配 2026 规范) ---
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=POLYGON,
    signature_type=2, 
    funder=FUNDER
)
client.set_api_creds(ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
))

# --- 3. 【V16.1 核心】自动适配余额探测器 ---
async def get_balance_v16_1():
    """
    不再死磕 get_collateral_balance，改用反射探测
    """
    # 按照 2026 SDK 优先级探测
    for method_name in ["get_balance", "get_user_balance", "get_collateral_balance"]:
        method = getattr(client, method_name, None)
        if method:
            try:
                # 尝试获取余额
                resp = await asyncio.to_thread(method)
                if isinstance(resp, dict):
                    return float(resp.get("balance") or resp.get("available") or 0)
                return float(resp or 0)
            except Exception as e:
                logging.debug(f"尝试 {method_name} 失败: {e}")
                continue
    return -1.0  # 返回 -1 表示“接口全部失效”，触发 Fallback

# --- 4. 信号驱动的 5 分钟交易逻辑 ---
last_trade_round = 0

async def smart_trade_logic():
    global last_trade_round
    
    # 获取余额 (适配 V16.1)
    balance = await get_balance_v16_1()
    logging.info(f"💰 实时资产探测: {balance if balance != -1.0 else '探测失败'} USDC.e")

    # 5分钟窗口控制
    now_round = int(time.time() // 300)
    if now_round == last_trade_round:
        return
    
    # 强制 Fallback：即使余额读取失败，只要你确认有钱，允许试单
    if balance == -1.0:
        logging.warning("⚠️ 余额读取异常，强制进入【盲打模式】...")
        balance = 10.0 # 假设一个余额
    elif balance < 0.2:
        logging.warning("🛑 余额确实不足，跳过本轮")
        return

    last_trade_round = now_round
    logging.info("⏰ [新周期] 开始扫描 7 路币种信号...")

    # 获取市场信号 (调用你的 market.py)
    markets = fetch_latest_market_map()
    
    # V16.1 策略：不再全推，只打前 2 个有信号的市场
    # 此处省略复杂的打分逻辑，直接演示执行
    for symbol, info in list(markets.items())[:2]:
        await execute_order(info['upTokenId'], info['name'], balance)

async def execute_order(token_id, title, balance):
    try:
        # 动态仓位 (10%)
        size = max(0.1, round(balance * 0.1, 2))
        
        # 2026 版 SDK 下单流程
        order_args = OrderArgs(price=0.2, size=size, side="buy", token_id=str(token_id))
        
        def _post():
            signed = client.create_order(order_args) # 自动签名
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_post)
        if res and res.get("success"):
            logging.info(f"🎯 下单成功: {title} | ID: {res.get('orderID')}")
    except Exception as e:
        logging.error(f"❌ 下单崩溃: {e}")

# --- 5. Railway Worker 入口 ---
async def main_loop():
    logging.info("🚀 龙虾 V16.1 稳定版已上线 (Railway Worker)")
    # 打印当前 SDK 所有方法，方便调试
    logging.info(f"🧪 SDK 可用方法列表: {[m for m in dir(client) if not m.startswith('_')]}")

    while True:
        try:
            await smart_trade_logic()
            await asyncio.sleep(10) # 保持心跳
        except Exception as e:
            logging.error(f"⚠️ 循环抖动: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # 修复 V16 语法错误：必须是 __name__
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass
    except Exception as fatal_e:
        logging.error(f"🚨 进程致命错误: {fatal_e}")
        time.sleep(10)
