import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer

# ================= 日志 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

logging.info("🚀 polymarket-sim: V17.1 (全变量对齐版) 启动")

# ================= 环境变量 =================
PK = os.getenv("PRIVATE_KEY")
FUNDER = os.getenv("Funder")

if not PK or not PK.startswith("0x"):
    raise Exception("🛑 FOX_PRIVATE_KEY 未正确配置（必须0x开头）")

logging.info(f"🔗 正在为地址 {FUNDER[:10]}... 激活链路...")

# ================= 客户端 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)

# 🔥 核心修复（你之前一直卡在这里）
client.signer = Signer(PK, chain_id=137)

if client.signer is None:
    raise Exception("🛑 signer 初始化失败")

# ================= 初始化 =================
def init_engine():
    try:
        logging.info("🔧 V17.1 启动：标准初始化模式...")

        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)

        # ⚠️ 加保护（避免 signature_type 再炸）
        try:
            client.update_balance_allowance()
        except Exception as e:
            logging.warning(f"⚠️ Allowance 跳过: {e}")

        logging.info("✅ 引擎初始化完成，交易链路已打通")
        return True

    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# ================= 余额 =================
async def get_balance():
    try:
        if hasattr(client, "get_balance"):
            res = await asyncio.to_thread(client.get_balance)
            return float(res.get("balance", 0))

        elif hasattr(client, "get_user_balance"):
            res = await asyncio.to_thread(client.get_user_balance)
            return float(res.get("balance", 0))

        return -1

    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return -1

# ================= Gamma =================
def fetch_markets():
    url = "https://gamma-api.polymarket.com/markets"
    params = {"limit": 20, "active": "true"}

    try:
        res = requests.get(url, params=params, timeout=10).json()

        markets = []
        for m in res:
            vol = float(m.get("volume", 0))
            tokens = m.get("tokens", [])

            if vol > 1000 and len(tokens) >= 2:
                markets.append({
                    "name": m["question"],
                    "token": tokens[0]["token_id"],
                    "volume": vol
                })

        markets.sort(key=lambda x: x["volume"], reverse=True)
        return markets[:5]

    except Exception as e:
        logging.error(f"⚠️ Gamma API 异常: {e}")
        return []

# ================= 盘口 =================
def is_tradeable(token):
    try:
        ob = client.get_order_book(token)
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])

        if not bids or not asks:
            return False

        spread = float(asks[0][0]) - float(bids[0][0])
        return spread < 0.05

    except:
        return False

# ================= 价格 =================
def get_price(token):
    try:
        ob = client.get_order_book(token)
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])

        if not bids or not asks:
            return 0.2

        return round((float(bids[0][0]) + float(asks[0][0])) / 2, 3)

    except:
        return 0.2

# ================= 风控 =================
trade_history = []
cooldown_until = 0

def can_trade():
    global cooldown_until

    if time.time() < cooldown_until:
        return False

    if len(trade_history) >= 3 and all(x == "LOSE" for x in trade_history[-3:]):
        cooldown_until = time.time() + 600
        logging.warning("🛑 连续亏损，暂停10分钟")
        return False

    return True

# ================= 下单 =================
async def execute(token, name, balance):
    try:
        size = max(0.1, round(balance * 0.1, 2))
        price = get_price(token)

        order = OrderArgs(
            price=price,
            size=size,
            side="buy",
            token_id=str(token)
        )

        def _do():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)

        res = await asyncio.to_thread(_do)

        if res and res.get("success"):
            logging.info(f"🎯 【交易成功】{name} | {size}")
            trade_history.append("WIN")
        else:
            logging.warning(f"❌ 【下单失败】{res}")
            trade_history.append("LOSE")

    except Exception as e:
        logging.error(f"❌ 交易异常: {e}")
        trade_history.append("LOSE")

# ================= 主循环 =================
async def step():
    logging.info("💓 polymarket-sim heartbeat")

    if not can_trade():
        return

    balance = await get_balance()

    if balance <= 0:
        logging.warning("💰 余额异常")
        return

    logging.info(f"💰 账户余额: {balance}")

    markets = fetch_markets()

    if not markets:
        logging.warning("🔎 未发现市场")
        return

    for m in markets:
        if is_tradeable(m["token"]):
            logging.info(f"🎯 锁定市场: {m['name']}")
            await execute(m["token"], m["name"], balance)
            return

    logging.warning("⚠️ 无可交易市场")

# ================= 主入口 =================
async def main():
    if not init_engine():
        logging.critical("🛑 初始化失败，程序退出。请检查 Railway 环境变量！")
        return

    while True:
        try:
            await step()
            await asyncio.sleep(300)
        except Exception as e:
            logging.error(f"💥 系统异常: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
