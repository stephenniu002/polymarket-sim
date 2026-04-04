import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# --- 1. 配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 修改点 1：确保这里从环境变量读取的名字和你在 Railway/控制台设置的一致
# 如果你在控制台填的是 PRIVATE_KEY，这里就要改成 "PRIVATE_KEY"
PK = os.getenv("FOX_PRIVATE_KEY") 
FUNDER = os.getenv("Funder")

# --- 2. 客户端初始化 ---
# 修改点 2：增加异常判断，防止 PK 为空时直接初始化
if not PK:
    logging.error("❌ 错误：环境变量 FOX_PRIVATE_KEY 未读取到，请检查配置！")
    # 如果没读取到，后面初始化肯定失败，这里可以加个占位符防止崩溃，或者直接 sys.exit()
    PK = "" 

# 注意：ClobClient 的初始化通常需要 host, key, chain_id
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)

def init_v17_1():
    # 修改点 3：严谨性检查
    if not PK or len(PK) < 60:
        logging.error("❌ 引擎初始化失败: A private key is needed to interact with this endpoint! (私钥为空或长度不足)")
        return False

    try:
        logging.info("🔧 V17.1 启动：同步 API 凭证...")
        
        # 修改点 4：对于已有 API Key 的用户，建议使用 derive 而不是 create_or_derive
        # 如果报错 400，通常是这里在尝试重复创建。
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        
        # 这一步需要私钥签名
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
        # 修改点 5：增加 timeout 防止请求卡死
        response = requests.get(url, params=params, timeout=10)
        res = response.json()
        scored_markets = []
        for m in res:
            if m.get("active") is True and not m.get("closed"):
                # 安全获取 volume 字段
                vol_str = m.get("volume") or 0
                vol = float(vol_str)
                tokens = m.get("tokens", [])
                
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
    try:
        # 使用 asyncio.to_thread 运行同步库方法
        resp = await asyncio.to_thread(client.get_balance)
        # 修改点 6：Polymarket 返回的通常是字典，需确保取值逻辑正确
        balance = float(resp) if isinstance(resp, (int, float)) else float(resp.get("balance", 10.84))
    except Exception as e:
        logging.warning(f"无法获取实时余额 ({e})，使用兜底值")
        balance = 10.84

    logging.info(f"💰 当前实时余额: {balance} USDC.e")

    markets = fetch_top_markets_v17_1()
    if not markets:
        logging.warning("🔎 警告：依然无法获取市场！")
        return

    best = markets[0]
    logging.info(f"🎯 自动锁定最活跃市场: {best['name']} (Vol: {best['volume']})")
    await execute_v17_1(best['yes_id'], best['name'], balance)

async def execute_v17_1(token_id, title, funds):
    try:
        # 10% 仓位
        size = max(0.1, round(funds * 0.1, 2))
        # 构建订单参数
        order_args = OrderArgs(price=0.25,
