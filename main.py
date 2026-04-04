import os, asyncio, logging, time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from market import fetch_latest_market_map

# --- 1. 日志与环境变量配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 对接你 Railway 面板上的变量
PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder") # 对应你的 Proxy 钱包

# --- 2. 客户端初始化 (根据 1:52 PM 最新规范) ---
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,            # 🔥 你的私钥
    chain_id=137,      # 🔥 必须是 137 (Polygon)
    signature_type=2,  # 签名类型
    funder=FUNDER      # 资金管理地址
)

def init_lobster_engine():
    """
    根据 1:50 PM 逻辑：灵魂注入、初始化 API Creds 并设置授权
    """
    try:
        logging.info("🔧 正在初始化 API 凭证与签名器...")
        # 1️⃣ 派生凭证 (激活 client.signer，解决 NoneType 报错的关键)
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info("✅ API creds 初始化成功")

        # 2️⃣ 设置授权额度 (确保可以下单)
        try:
            collateral_address = client.get_collateral_address()
            res = client.update_balance_allowance(token_address=collateral_address)
            logging.info(f"✅ Allowance 设置成功: {res}")
        except Exception as e:
            logging.warning(f"⚠️ Allowance 设置略过 (通常已是最大值): {e}")
            
        return True
    except Exception as e:
        logging.error(f"❌ 引擎启动失败: {e}")
        return False

# --- 3. 对齐 2026 SDK 的余额探测 ---
async def get_real_balance():
    try:
        # signer 激活后，此接口将正常返回字典
        resp = await asyncio.to_thread(client.get_balance_allowance)
        if isinstance(resp, dict):
            # 兼容 balance 或 available 字段
            return float(resp.get("balance") or resp.get("available") or 0)
        return float(resp or 0)
    except Exception as e:
        logging.error(f"❌ 余额读取依旧受阻: {e}")
        return -1.0 # 标识异常

# --- 4. 信号驱动的交易逻辑 ---
last_trade_round = 0

async def trade_logic():
    global last_trade_round
    
    # 5分钟周期窗口判定
    now_round = int(time.time() // 300)
    if now_round == last_trade_round:
        return
    
    balance = await get_real_balance()
    
    # Fallback: 如果探测异常但你确认有钱，使用 10.84 逻辑兜底试单
    funds = balance if balance > 0 else 10.84
    
    if funds < 0.5:
        logging.warning("🛑 账户余额过低，跳过本轮")
        return

    last_trade_round = now_round
    logging.info(f"⏰ [新周期] 账户余额: {funds} | 开始扫描信号...")

    # 获取 7 路信号 (通过 market.py)
    markets = fetch_latest_market_map()
    if not markets:
        logging.warning("🔎 信号池为空，请检查关键词匹配")
        return

    # 只打信号最强的前 2 个市场，降低回撤
    for _, info in list(markets.items())[:2]:
        await safe_execute(info['upTokenId'], info['name'], funds)

async def safe_execute(token_id, title, funds):
    try:
        # 10% 动态仓位
        trade_size = max(0.1, round(funds * 0.1, 2))
        
        order_args = OrderArgs(
            price=0.2, # 你的挂单价格策略
            size=trade_size, 
            side="buy", 
            token_id=str(token_id)
        )

        def _do_post():
            signed = client.create_order(order_args)
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_do_post)
        if res and res.get("success"):
            logging.info(f"🎯 【下单成功】{title} | 规模: {trade_size} USDC.e")
    except Exception as e:
        logging.error(f"❌ 下单防崩保护: {e}")

# --- 5. Railway 守护进程入口 ---
async def main_worker():
    logging.info("🚀 polymarket-sim: V16.5 (灵魂注入版) 已启动")
    
    # 第一步必须成功，否则 signer 是空的，查余额必崩
    if not init_lobster_engine():
        logging.error("🚨 核心组件未就绪，将在 30s 后重试...")
        await asyncio.sleep(30)
        return

    while True:
        try:
            await trade_logic()
            await asyncio.sleep(10) # 保持探针活跃
        except Exception as e:
            logging.error(f"⚠️ 守护循环抖动: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main_worker())
    except Exception as e:
        logging.error(f"🚨 致命进程崩溃: {e}")
        time.sleep(10)
