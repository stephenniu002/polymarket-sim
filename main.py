import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# --- 1. 配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

# --- 2. 客户端初始化 ---
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)

def init_v17_1():
    try:
        logging.info("🔧 V17.1 启动：同步 API 凭证...")
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        client.update_balance_allowance()
        logging.info("✅ 链路已激活")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# --- 3. Gamma 强效捕获 (修复“未发现市场”核心痛点) ---
def fetch_top_markets_v17_1():
    """
    放弃关键词过滤，直接抓取全量活跃市场并按成交量降序
    """
    url = "https://gamma-api.polymarket.com/markets"
    # 增加 limit 到 100，确保覆盖面
    params = {
        "limit": 100, 
        "active": "true", 
        "closed": "false",
        "order": "volume24hr", # 优先拿 24 小时最火的市场
        "ascending": "false"
    }
    
    try:
        res = requests.get(url, params=params).json()
        scored_markets = []
        for m in res:
            # 过滤掉已经结束或无效的市场
            if m.get("active") is True and not m.get("closed"):
                vol = float(m.get("volume", 0))
                tokens = m.get("tokens", [])
                
                # 必须有 Token 且成交量 > 100 (降低门槛，确保能抓到)
                if len(tokens) >= 2 and vol > 100:
                    scored_markets.append({
                        "name": m.get("question", "Unknown"),
                        "yes_id": tokens[0].get("token_id"),
                        "volume": vol
                    })
        
        logging.info(f"📡 Gamma API 返回了 {len(res)} 个候选，筛选出 {len(scored_markets)} 个有效市场")
        return scored_markets
    except Exception as e:
        logging.error(f"⚠️ Gamma API 连通失败: {e}")
        return []

# --- 4. 步进逻辑 ---
async def trade_step():
    # 余额校验
    try:
        resp = await asyncio.to_thread(client.get_balance)
        balance = float(resp.get("balance", 0))
    except:
        balance = 10.84 # 兜底

    logging.info(f"💰 当前实时余额: {balance} USDC.e")

    # 寻找市场
    markets = fetch_top_markets_v17_1()
    if not markets:
        logging.warning("🔎 警告：依然无法获取市场！尝试更换节点或检查 Railway 网络...")
        return

    # 锁定最火的一个
    best = markets[0]
    logging.info(f"🎯 自动锁定最活跃市场: {best['name']} (Vol: {best['volume']})")

    # 执行下单 (10% 试探)
    await execute_v17_1(best['yes_id'], best['name'], balance)

async def execute_v17_1(token_id, title, funds):
    try:
        size = max(0.1, round(funds * 0.1, 2))
        order = OrderArgs(price=0.25, size=size, side="buy", token_id=str(token_id))
        
        def _do():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_do)
        if res and res.get("success"):
            logging.info(f"✅ 【实盘成交】ID: {res.get('orderID')} | 市场: {title}")
        else:
            logging.warning(f"❌ 【下单拒绝】: {res}")
    except Exception as e:
        logging.error(f"❌ 执行异常: {e}")

# --- 5. 入口 ---
async def main():
    logging.info("🚀 polymarket-sim: V17.1 (Gamma 强捕获版) 启动")
    if not init_v17_1(): return

    while True:
        try:
            await trade_step()
            await asyncio.sleep(300) # 5分钟一轮
        except Exception as e:
            logging.error(f"⚠️ 守护异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
