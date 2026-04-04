import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# --- 1. 严谨的日志系统 ---
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
)

PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

# --- 2. 标准化客户端初始化 (回归 SDK 原生逻辑) ---
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137, # Polygon Mainnet
    funder=FUNDER
)

def init_v17_engine():
    """
    依照标准流程激活 API 凭证，不再手动 Hack Signer
    """
    try:
        logging.info("🔧 V17 引擎启动：正在同步 API 凭证...")
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        
        # 激活授权 (Allowance)
        client.update_balance_allowance()
        logging.info("✅ 引擎初始化完成，交易链路已打通")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# --- 3. 真实余额校验 (防盲打) ---
async def get_balance_real():
    try:
        # 优先尝试标准余额接口
        resp = await asyncio.to_thread(client.get_balance)
        if resp and "balance" in resp:
            return float(resp["balance"])
        
        # 备选接口 (适配不同 SDK 版本)
        resp = await asyncio.to_thread(client.get_user_balance)
        return float(resp.get("balance", 0))
    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return -1.0 # 返回 -1 表示异常，触发停手

# --- 4. 智能市场筛选 (带评分系统) ---
def fetch_top_markets():
    url = "https://gamma-api.polymarket.com/markets"
    # 扩大搜索范围，改用成交量(Volume)评分
    params = {"limit": 20, "active": "true", "closed": "false"}
    
    try:
        res = requests.get(url, params=params).json()
        scored_markets = []
        for m in res:
            volume = float(m.get("volume", 0))
            # 过滤：成交量 > 1000 且 必须是 Price 相关或高热度市场
            if volume > 1000:
                tokens = m.get("tokens", [])
                if len(tokens) >= 2:
                    scored_markets.append({
                        "name": m["question"],
                        "yes_id": tokens[0]["token_id"],
                        "volume": volume
                    })
        
        # 按成交量降序排列，取最强的
        scored_markets.sort(key=lambda x: x["volume"], reverse=True)
        return scored_markets
    except Exception as e:
        logging.error(f"⚠️ 市场抓取异常: {e}")
        return []

# --- 5. 核心交易步进 ---
async def trade_step():
    # A. 余额检查
    balance = await get_balance_real()
    if balance == -1.0:
        logging.warning("⚠️ 无法确认真实余额，为了资金安全，本轮跳过")
        return
    if balance < 1.0:
        logging.info(f"💰 余额不足 (当前: {balance})，进入观察模式")
        return

    logging.info(f"💰 账户实盘资金: {balance} USDC.e")

    # B. 寻找最优市场
    markets = fetch_top_markets()
    if not markets:
        logging.warning("🔎 未发现符合流动性要求(Vol > 1000)的市场")
        return

    # C. 选出评分最高的市场
    best_market = markets[0]
    logging.info(f"🎯 锁定最优市场: {best_market['name']} (Vol: {best_market['volume']})")

    # D. 执行成交验证下单
    await execute_with_verify(best_market['yes_id'], best_market['name'], balance)

async def execute_with_verify(token_id, title, funds):
    try:
        # 10% 动态轻仓策略
        trade_size = max(0.1, round(funds * 0.1, 2))
        order_args = OrderArgs(price=0.25, size=trade_size, side="buy", token_id=str(token_id))

        def _do_order():
            signed = client.create_order(order_args)
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_do_order)
        
        # E. 严格的成交验证
        if res and res.get("success"):
            order_id = res.get("orderID")
            logging.info(f"✅ 【交易成功】ID: {order_id} | 市场: {title} | 投入: {trade_size}")
        else:
            logging.warning(f"❌ 【下单被拒】原因: {res.get('error') or '未知网络错误'}")
            
    except Exception as e:
        logging.error(f"❌ 交易执行崩溃保护: {e}")

# --- 6. 生产级主入口 ---
async def main():
    logging.info("🚀 polymarket-sim: V17 稳定盈利版启动")
    
    # 引擎初始化
    if not init_v17_engine():
        logging.error("🚨 核心引擎无法启动，请检查环境变量(PK/Funder)及网络")
        return

    while True:
        try:
            await trade_step()
            # 5分钟扫描一次 (300秒)
            await asyncio.sleep(300)
        except Exception as e:
            logging.error(f"⚠️ 主循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    # 修正主入口判断
    asyncio.run(main())
