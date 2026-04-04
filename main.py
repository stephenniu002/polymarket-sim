import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# --- 1. 配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 已根据 Railway 变量列表对齐名称
PK = os.getenv("POLY_PRIVATE_KEY") 
FUNDER = os.getenv("POLY_ADDRESS")

# --- 2. 客户端初始化 ---
# 增加预检，确保变量已读入
if not PK:
    logging.error("❌ 严重错误：未读取到环境变量 'POLY_PRIVATE_KEY'！请检查 Railway 变量设置。")
    PK = "" 

if not FUNDER:
    logging.error("❌ 严重错误：未读取到环境变量 'POLY_ADDRESS'！请检查 Railway 变量设置。")
    FUNDER = ""

# 初始化 ClobClient
client = ClobClient(
    host="https://clob.polymarket.com", 
    key=PK, 
    chain_id=137, 
    funder=FUNDER
)

def init_v17_1():
    # 物理长度检查：0x + 64位私钥 = 66
    if not PK or len(PK) < 60:
        logging.error("❌ 引擎初始化失败: 私钥缺失或格式不正确！当前长度: %s", len(PK) if PK else 0)
        return False

    try:
        logging.info("🔧 V17.1 启动：同步 API 凭证...")
        
        # 尝试派生或创建 API Key
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        
        # 更新账户津贴和余额状态
        client.update_balance_allowance()
        logging.info("✅ 链路已激活")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# --- 3. Gamma 强效捕获 ---
def fetch_top_markets_v17_1():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 100, 
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
                
                # 至少有 Yes/No 两个 Token 且有一定成交量
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

# --- 4. 交易逻辑 ---
async def trade_step():
    try:
        # 获取余额
        resp = await asyncio.to_thread(client.get_balance)
        if isinstance(resp, dict):
            balance = float(resp.get("balance", 10.84))
        else:
            balance = float(resp)
    except Exception as e:
        logging.warning(f"无法获取实时余额: {e}")
        balance = 10.84

    logging.info(f"💰 当前账户余额: {balance} USDC.e")

    markets = fetch_top_markets_v17_1()
    if not markets:
        logging.warning("🔎 未发现符合条件的市场，跳过此轮...")
        return

    best = markets[0]
    logging.info(f"🎯 自动锁定成交量最高市场: {best['name']}")
    await execute_v17_1(best['yes_id'], best['name'], balance)

async def execute_v17_1(token_id, title, funds):
    try:
        # 10% 仓位试探，单笔不少于 0.1
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
    
    if not init_v17_1():
        logging.critical("🛑 初始化失败，程序即将退出。请检查变量名和私钥准确性！")
        return

    while True:
        try:
            await trade_step()
            await asyncio.sleep(300) # 每5分钟扫描一次
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 正在关闭机器人...")
