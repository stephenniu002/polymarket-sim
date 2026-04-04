import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds

# --- 1. 配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 从 Railway 环境变量读取
PK = os.getenv("POLY_PRIVATE_KEY") 
FUNDER = os.getenv("POLY_ADDRESS")

# 初始化 ClobClient (基础参数)
client = ClobClient(
    host="https://clob.polymarket.com", 
    key=PK, 
    chain_id=137, 
    funder=FUNDER
)

# --- 2. 核心初始化 (手动凭证模式) ---
def init_v17_1():
    try:
        logging.info("🔧 V17.1 启动：手动加载 API 凭证模式...")
        
        # 1. 直接读取你填在 Railway 的三剑客
        api_key = os.getenv("POLY_API_KEY")
        api_secret = os.getenv("POLY_SECRET")
        api_passphrase = os.getenv("POLY_PASSPHRASE")

        # 2. 检查是否齐全 (任何一个为空都会拦截)
        if not all([api_key, api_secret, api_passphrase]):
            logging.error("❌ 错误：手动凭证不全！请在 Railway 检查 POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE")
            return False

        # 3. 强制注入凭证，彻底避开报错的 create_or_derive_api_creds()
        creds = ApiCreds(
            api_key=api_key, 
            api_secret=api_secret, 
            api_passphrase=api_passphrase
        )
        client.set_api_creds(creds)
        
        # 4. 激活链路 (验证 API 是否有效)
        client.update_balance_allowance()
        logging.info("✅ 链路已激活 (使用手动注入凭证)")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# --- 3. Gamma 强效捕获 ---
def fetch_top_markets_v17_1():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 50, 
        "active": "true", 
        "closed": "false",
        "order": "volume24hr",
        "ascending": "false"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        res = response.json()
        scored_markets = []
        for m in res:
            if m.get("active") is True and not m.get("closed"):
                vol = float(m.get("volume") or 0)
                tokens = m.get("tokens", [])
                if len(tokens) >= 2 and vol > 100:
                    scored_markets.append({
                        "name": m.get("question", "Unknown"),
                        "yes_id": tokens[0].get("token_id"),
                        "volume": vol
                    })
        logging.info(f"📡 Gamma API 获取了 {len(scored_markets)} 个活跃市场")
        return scored_markets
    except Exception as e:
        logging.error(f"⚠️ Gamma API 连通失败: {e}")
        return []

# --- 4. 步进交易逻辑 ---
async def trade_step():
    try:
        # 获取余额 (通过 asyncio 运行同步库)
        resp = await asyncio.to_thread(client.get_balance)
        balance = float(resp.get("balance", 10.84)) if isinstance(resp, dict) else float(resp)
    except Exception as e:
        logging.warning(f"无法获取余额: {e}")
        balance = 10.84

    logging.info(f"💰 当前账户余额: {balance} USDC.e")

    markets = fetch_top_markets_v17_1()
    if not markets:
        return

    best = markets[0]
    logging.info(f"🎯 自动锁定成交量最高市场: {best['name']}")
    
    # 执行下单
    await execute_v17_1(best['yes_id'], best['name'], balance)

async def execute_v17_1(token_id, title, funds):
    try:
        # 10% 仓位，且价格固定在 0.25 尝试捕获
        size = max(0.1, round(funds * 0.1, 2))
        order_args = OrderArgs(price=0.25, size=size, side="buy", token_id=str(token_id))
        
        def _do():
            signed_order = client.create_order(order_args)
            return client.post_order(signed_order, OrderType.GTC)

        res = await asyncio.to_thread(_do)
        if res and res.get("success"):
            logging.info(f"✅ 【实盘成交】ID: {res.get('orderID')} | 市场: {title}")
        else:
            logging.warning(f"❌ 【下单拒绝】: {res}")
    except Exception as e:
        logging.error(f"❌ 下单执行异常: {e}")

# --- 5. 入口 ---
async def main():
    logging.info("🚀 polymarket-sim: V17.1 (Gamma 强捕获版) 启动")
    
    # 强制执行新初始化逻辑
    if not init_v17_1():
        logging.critical("🛑 初始化失败，程序退出。请检查 Railway 里的 API 三剑客变量！")
        return

    while True:
        try:
            await trade_step()
            await asyncio.sleep(300) # 5分钟一轮
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 正在关闭...")
