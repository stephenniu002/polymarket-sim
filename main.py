import os
import time
import requests
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# =========================
# 🔧 环境变量（Railway 必填）
# =========================
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
ADDRESS = os.getenv("POLY_ADDRESS")
TOKEN_ID = os.getenv("TEST_TOKEN_ID")

# =========================
# 参数（测试用）
# =========================
SIZE = 1        # 买 1 USDC
PRICE = 0.5     # 中间价（提高成交概率）

# =========================
# 日志
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# 初始化客户端
# =========================
def init_client():
    try:
        client = ClobClient(
            key=PRIVATE_KEY,
            chain_id=137  # Polygon
        )
        logging.info("✅ Client 初始化成功")
        return client
    except Exception as e:
        logging.error(f"❌ Client 初始化失败: {e}")
        return None

# =========================
# 获取持仓
# =========================
def get_positions():
    try:
        url = f"https://data-api.polymarket.com/positions?user={ADDRESS}"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            logging.error(f"❌ 持仓接口错误: {res.status_code}")
            return None

        data = res.json()

        if not data:
            logging.warning("⚠️ 没有获取到持仓")
        else:
            logging.info(f"✅ 获取到持仓: {data}")

        return data

    except Exception as e:
        logging.error(f"❌ 获取持仓异常: {e}")
        return None

# =========================
# 强制下单（核心）
# =========================
def force_order(client):
    try:
        logging.info("🚀 开始强制下单测试")

        order = OrderArgs(
            price=PRICE,
            size=SIZE,
            side="BUY",
            token_id=TOKEN_ID,
        )

        logging.info(f"🧾 下单参数: price={PRICE}, size={SIZE}, token={TOKEN_ID}")

        signed_order = client.sign_order(order)

        logging.info("✅ 签名成功")

        res = client.post_order(signed_order, OrderType.GTC)

        logging.info(f"📤 下单返回: {res}")

        return res

    except Exception as e:
        logging.error(f"❌ 下单失败: {e}")
        return None

# =========================
# 主流程
# =========================
def main():
    logging.info("===================================")
    logging.info("🦞 实盘强制检测系统启动")
    logging.info("===================================")

    # 参数检查
    if not PRIVATE_KEY or not ADDRESS or not TOKEN_ID:
        logging.error("❌ 环境变量缺失！请检查：")
        logging.error("POLY_PRIVATE_KEY / POLY_ADDRESS / TEST_TOKEN_ID")
        return

    # 初始化 client
    client = init_client()
    if not client:
        return

    # 1️⃣ 初始持仓
    logging.info("🔍 检查初始持仓...")
    pos_before = get_positions()

    # 防止接口限流
    time.sleep(3)

    # 2️⃣ 强制下单
    result = force_order(client)

    if not result:
        logging.error("❌ 下单失败，终止测试")
        return

    # 3️⃣ 等待成交
    logging.info("⏳ 等待 8 秒让订单成交/上链...")
    time.sleep(8)

    # 4️⃣ 再查持仓
    logging.info("🔍 再次检查持仓...")
    pos_after = get_positions()

    # 5️⃣ 对比结果
    if pos_after and pos_after != pos_before:
        logging.info("🎉 成功！持仓发生变化 → 交易闭环打通")
    else:
        logging.warning("⚠️ 未检测到持仓变化")

        logging.warning("👉 可能原因：")
        logging.warning("1. TOKEN_ID 错误")
        logging.warning("2. 价格不合理（未成交）")
        logging.warning("3. 账户没有 USDC")
        logging.warning("4. 网络/接口延迟")

    logging.info("===================================")
    logging.info("🧪 检测结束")
    logging.info("===================================")

# =========================
if __name__ == "__main__":
    main()import os
import time
import requests
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# =========================
# 🔧 环境变量（Railway 必填）
# =========================
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
ADDRESS = os.getenv("POLY_ADDRESS")
TOKEN_ID = os.getenv("TEST_TOKEN_ID")

# =========================
# 参数（测试用）
# =========================
SIZE = 1        # 买 1 USDC
PRICE = 0.5     # 中间价（提高成交概率）

# =========================
# 日志
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# 初始化客户端
# =========================
def init_client():
    try:
        client = ClobClient(
            key=PRIVATE_KEY,
            chain_id=137  # Polygon
        )
        logging.info("✅ Client 初始化成功")
        return client
    except Exception as e:
        logging.error(f"❌ Client 初始化失败: {e}")
        return None

# =========================
# 获取持仓
# =========================
def get_positions():
    try:
        url = f"https://data-api.polymarket.com/positions?user={ADDRESS}"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            logging.error(f"❌ 持仓接口错误: {res.status_code}")
            return None

        data = res.json()

        if not data:
            logging.warning("⚠️ 没有获取到持仓")
        else:
            logging.info(f"✅ 获取到持仓: {data}")

        return data

    except Exception as e:
        logging.error(f"❌ 获取持仓异常: {e}")
        return None

# =========================
# 强制下单（核心）
# =========================
def force_order(client):
    try:
        logging.info("🚀 开始强制下单测试")

        order = OrderArgs(
            price=PRICE,
            size=SIZE,
            side="BUY",
            token_id=TOKEN_ID,
        )

        logging.info(f"🧾 下单参数: price={PRICE}, size={SIZE}, token={TOKEN_ID}")

        signed_order = client.sign_order(order)

        logging.info("✅ 签名成功")

        res = client.post_order(signed_order, OrderType.GTC)

        logging.info(f"📤 下单返回: {res}")

        return res

    except Exception as e:
        logging.error(f"❌ 下单失败: {e}")
        return None

# =========================
# 主流程
# =========================
def main():
    logging.info("===================================")
    logging.info("🦞 实盘强制检测系统启动")
    logging.info("===================================")

    # 参数检查
    if not PRIVATE_KEY or not ADDRESS or not TOKEN_ID:
        logging.error("❌ 环境变量缺失！请检查：")
        logging.error("POLY_PRIVATE_KEY / POLY_ADDRESS / TEST_TOKEN_ID")
        return

    # 初始化 client
    client = init_client()
    if not client:
        return

    # 1️⃣ 初始持仓
    logging.info("🔍 检查初始持仓...")
    pos_before = get_positions()

    # 防止接口限流
    time.sleep(3)

    # 2️⃣ 强制下单
    result = force_order(client)

    if not result:
        logging.error("❌ 下单失败，终止测试")
        return

    # 3️⃣ 等待成交
    logging.info("⏳ 等待 8 秒让订单成交/上链...")
    time.sleep(8)

    # 4️⃣ 再查持仓
    logging.info("🔍 再次检查持仓...")
    pos_after = get_positions()

    # 5️⃣ 对比结果
    if pos_after and pos_after != pos_before:
        logging.info("🎉 成功！持仓发生变化 → 交易闭环打通")
    else:
        logging.warning("⚠️ 未检测到持仓变化")

        logging.warning("👉 可能原因：")
        logging.warning("1. TOKEN_ID 错误")
        logging.warning("2. 价格不合理（未成交）")
        logging.warning("3. 账户没有 USDC")
        logging.warning("4. 网络/接口延迟")

    logging.info("===================================")
    logging.info("🧪 检测结束")
    logging.info("===================================")

# =========================
if __name__ == "__main__":
    main()
