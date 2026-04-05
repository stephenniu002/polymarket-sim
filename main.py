import os
import asyncio
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer

# ================= 日志 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.info("🚀 polymarket-sim: V17.2 (7币全覆盖版) 启动")

# ================= 环境变量 =================
PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

if not PK or not PK.startswith("0x"):
    raise Exception("🛑 FOX_PRIVATE_KEY 未正确配置（必须0x开头）")

if not FUNDER or not FUNDER.startswith("0x"):
    raise Exception("🛑 Funder 地址未正确配置（必须0x开头）")

logging.info(f"🔗 链路激活地址: {FUNDER[:10]}...")

# ================= TOKEN 全覆盖 =================
MARKETS = {
    "BTC": {
        "UP": "68033518322462371935856735251001652798688532944534600565715682414078422713363",
        "DOWN": "42290470910454159474303047950885744851262714754899371843021423088168640872907"
    },
    "ETH": {
        "UP": "22697677844037973694672765750606352785901003559149933535427801487665640947803",
        "DOWN": "115090385978773385923886371350527743245393288513466835985021881253014596643630"
    },
    "SOL": {
        "UP": "104603314801857341640835854350038686011870944676564680074680431702449050206849",
        "DOWN": "109356807032619845857448714056328897846193614693799092745423146063644528271739"
    },
    "ARB": {
        "UP": "83969554674239323125534841773025419295324024187242141567151123418758917736351",
        "DOWN": "55696486755928578342776003278410729069499785313927089760850183610072430890445"
    },
    "OP": {
        "UP": "102762789132004280347110241206954008153952900365785095086032215198759595021055",
        "DOWN": "114844319908492689652356903444093235582805928777096660934420753771345312987663"
    },
    "DOGE": {
        "UP": "106625082417191245995145458652026897669356408589941137585886068627196204381551",
        "DOWN": "70904302110360626667376939927906146916424503243022738450880960377487226196037"
    },
    "MATIC": {
        "UP": "113731536206314593343123440641902754070657405235286809042047205745082834474083",
        "DOWN": "70757969820078082396704681961608768251154072300114355273498766356711024291765"
    }
}

# ================= 客户端 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)

client.signer = Signer(PK, chain_id=137)
if client.signer is None:
    raise Exception("🛑 signer 初始化失败")

# ================= 初始化 =================
def init_engine():
    try:
        logging.info("🔧 V17.2 启动：标准初始化模式...")
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
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
        res = await asyncio.to_thread(client.get_balance)
        return float(res.get("balance", 0))
    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return 0

# ================= 价格 & 下单 =================
def get_price(token):
    try:
        ob = client.get_order_book(token)
        bids, asks = ob.get("bids", []), ob.get("asks", [])
        if not bids or not asks:
            return 0.2
        return round((float(bids[0][0]) + float(asks[0][0])) / 2, 3)
    except:
        return 0.2

async def execute(token, name, balance):
    try:
        size = max(0.1, round(balance * 0.1, 2))
        price = get_price(token)
        order = OrderArgs(price=price, size=size, side="buy", token_id=str(token))
        def _do():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)
        res = await asyncio.to_thread(_do)
        if res and res.get("success"):
            logging.info(f"🎯 【交易成功】{name} | {size}")
        else:
            logging.warning(f"❌ 【下单失败】{res}")
    except Exception as e:
        logging.error(f"❌ 交易异常: {e}")

# ================= 主循环 =================
async def step():
    balance = await get_balance()
    if balance <= 0:
        logging.warning("💰 余额异常")
        return
    logging.info(f"💰 账户余额: {balance}")

    for coin, tokens in MARKETS.items():
        token = tokens["UP"]  # 这里示例只下多单，你可以根据策略改 UP/DOWN
        await execute(token, coin, balance)

async def main():
    if not init_engine():
        logging.critical("🛑 初始化失败，程序退出")
        return
    while True:
        try:
            await step()
            await asyncio.sleep(300)  # 每5分钟循环
        except Exception as e:
            logging.error(f"💥 系统异常: {e}")
            await asyncio.sleep(5)

# ================= 正确入口 =================
if __name__ == "__main__":
    asyncio.run(main())import os
import asyncio
import logging
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer

# ================= 日志 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.info("🚀 polymarket-sim: V17.2 (7币全覆盖版) 启动")

# ================= 环境变量 =================
PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

if not PK or not PK.startswith("0x"):
    raise Exception("🛑 FOX_PRIVATE_KEY 未正确配置（必须0x开头）")

if not FUNDER or not FUNDER.startswith("0x"):
    raise Exception("🛑 Funder 地址未正确配置（必须0x开头）")

logging.info(f"🔗 链路激活地址: {FUNDER[:10]}...")

# ================= TOKEN 全覆盖 =================
MARKETS = {
    "BTC": {
        "UP": "68033518322462371935856735251001652798688532944534600565715682414078422713363",
        "DOWN": "42290470910454159474303047950885744851262714754899371843021423088168640872907"
    },
    "ETH": {
        "UP": "22697677844037973694672765750606352785901003559149933535427801487665640947803",
        "DOWN": "115090385978773385923886371350527743245393288513466835985021881253014596643630"
    },
    "SOL": {
        "UP": "104603314801857341640835854350038686011870944676564680074680431702449050206849",
        "DOWN": "109356807032619845857448714056328897846193614693799092745423146063644528271739"
    },
    "ARB": {
        "UP": "83969554674239323125534841773025419295324024187242141567151123418758917736351",
        "DOWN": "55696486755928578342776003278410729069499785313927089760850183610072430890445"
    },
    "OP": {
        "UP": "102762789132004280347110241206954008153952900365785095086032215198759595021055",
        "DOWN": "114844319908492689652356903444093235582805928777096660934420753771345312987663"
    },
    "DOGE": {
        "UP": "106625082417191245995145458652026897669356408589941137585886068627196204381551",
        "DOWN": "70904302110360626667376939927906146916424503243022738450880960377487226196037"
    },
    "MATIC": {
        "UP": "113731536206314593343123440641902754070657405235286809042047205745082834474083",
        "DOWN": "70757969820078082396704681961608768251154072300114355273498766356711024291765"
    }
}

# ================= 客户端 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)

client.signer = Signer(PK, chain_id=137)
if client.signer is None:
    raise Exception("🛑 signer 初始化失败")

# ================= 初始化 =================
def init_engine():
    try:
        logging.info("🔧 V17.2 启动：标准初始化模式...")
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
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
        res = await asyncio.to_thread(client.get_balance)
        return float(res.get("balance", 0))
    except Exception as e:
        logging.error(f"❌ 余额获取失败: {e}")
        return 0

# ================= 价格 & 下单 =================
def get_price(token):
    try:
        ob = client.get_order_book(token)
        bids, asks = ob.get("bids", []), ob.get("asks", [])
        if not bids or not asks:
            return 0.2
        return round((float(bids[0][0]) + float(asks[0][0])) / 2, 3)
    except:
        return 0.2

async def execute(token, name, balance):
    try:
        size = max(0.1, round(balance * 0.1, 2))
        price = get_price(token)
        order = OrderArgs(price=price, size=size, side="buy", token_id=str(token))
        def _do():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)
        res = await asyncio.to_thread(_do)
        if res and res.get("success"):
            logging.info(f"🎯 【交易成功】{name} | {size}")
        else:
            logging.warning(f"❌ 【下单失败】{res}")
    except Exception as e:
        logging.error(f"❌ 交易异常: {e}")

# ================= 主循环 =================
async def step():
    balance = await get_balance()
    if balance <= 0:
        logging.warning("💰 余额异常")
        return
    logging.info(f"💰 账户余额: {balance}")

    for coin, tokens in MARKETS.items():
        token = tokens["UP"]  # 这里示例只下多单，你可以根据策略改 UP/DOWN
        await execute(token, coin, balance)

async def main():
    if not init_engine():
        logging.critical("🛑 初始化失败，程序退出")
        return
    while True:
        try:
            await step()
            await asyncio.sleep(300)  # 每5分钟循环
        except Exception as e:
            logging.error(f"💥 系统异常: {e}")
            await asyncio.sleep(5)

# ================= 正确入口 =================
if __name__ == "__main__":
    asyncio.run(main())
