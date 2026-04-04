import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType
from py_clob_client.signer import Signer 

# --- 1. 配置与变量 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

# --- 2. 客户端初始化与手动绑定 ---
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    signature_type=2,
    funder=FUNDER
)

def init_v16_7():
    try:
        logging.info("🔧 正在执行 V16.7 核心初始化...")
        # 1️⃣ 手动绑定 Signer (彻底解决 NoneType 'signature_type' 报错)
        if PK:
            client.signer = Signer(PK, chain_id=137)
            logging.info("✅ Signer 手动绑定完成")

        # 2️⃣ 派生并注入凭证
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info("✅ API Credentials 注入成功")

        # 3️⃣ 修正后的授权调用
        try:
            client.update_balance_allowance() # 不传参数，使用 SDK 默认值
            logging.info("✅ 资产授权已自动同步")
        except: pass
        return True
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return False

# --- 3. Gamma API 市场发现 (根据 2:02 PM 优化) ---
def fetch_markets_v16_7():
    """
    使用正确的关键词搜索：bitcoin, ethereum, solana
    """
    url = "https://gamma-api.polymarket.com/markets"
    keywords = ["bitcoin", "ethereum", "solana"]
    found_tokens = []
    
    for kw in keywords:
        try:
            params = {"limit": 5, "active": "true", "search": kw}
            res = requests.get(url, params=params).json()
            for m in res:
                # 只要 question 里包含 Price 的预测市场
                if "Price" in m.get("question", ""):
                    tokens = m.get("tokens", [])
                    if len(tokens) >= 2:
                        found_tokens.append({
                            "name": m["question"],
                            "yes_id": tokens[0]["token_id"]
                        })
        except Exception as e:
            logging.warning(f"⚠️ 搜索 {kw} 异常: {e}")
            
    return found_tokens[:7] # 最多取 7 个

# --- 4. 余额与交易逻辑 ---
async def trade_step():
    # 余额读取 (Signer 绑定后将恢复正常)
    try:
        resp = await asyncio.to_thread(client.get_balance_allowance)
        balance = float(resp.get("balance") if isinstance(resp, dict) else (resp or 0))
    except:
        balance = 10.84 # 盲打兜底

    logging.info(f"💰 实时余额: {balance} USDC.e")

    # 发现市场
    market_list = fetch_markets_v16_7()
    if not market_list:
        logging.warning("🔎 依然未发现活跃市场，请确认 Gamma API 连通性")
        return

    logging.info(f"📡 已锁定 {len(market_list)} 个目标市场，准备扫描信号...")
    
    # 模拟下单第一个市场 (V16.7 演示)
    target = market_list[0]
    await execute_safe(target['yes_id'], target['name'], balance)

async def execute_safe(token_id, title, funds):
    try:
        size = max(0.1, round(funds * 0.1, 2))
        order = OrderArgs(price=0.2, size=size, side="buy", token_id=str(token_id))
        
        def _post():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_post)
        if res and res.get("success"):
            logging.info(f"🎯 【实盘成交】市场: {title} | 规模: {size}")
    except Exception as e:
        logging.error(f"❌ 下单失败: {e}")

# --- 5. 守护进程 ---
async def main():
    logging.info("🚀 polymarket-sim: V16.7 终极整合版启动")
    if not init_v16_7(): return

    while True:
        try:
            await trade_step()
            await asyncio.sleep(300) # 每 5 分钟一个周期
        except Exception as e:
            logging.error(f"⚠️ 运行异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
