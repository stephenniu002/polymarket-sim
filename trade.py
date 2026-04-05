
import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===============================
# 初始化（⚠️ 用 api_key 版本）
# ===============================
client = ClobClient(
    host="https://clob.polymarket.com",
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE"),
    chain_id=POLYGON,
    private_key=os.getenv("PRIVATE_KEY")
)

# 尝试激活 API（有些版本必须）
try:
    client.derive_api_key()
    logging.info("✅ API 已激活")
except Exception as e:
    logging.warning(f"⚠️ API 激活跳过: {e}")


# ===============================
# 参数
# ===============================
BASE_SIZE = float(os.getenv("ORDER_SIZE", 2))
MAX_SIZE = BASE_SIZE * 3  # 最大仓位限制


# ===============================
# 动态仓位
# ===============================
def calc_size(strength):
    size = BASE_SIZE * (1 + strength)

    if size > MAX_SIZE:
        size = MAX_SIZE

    return round(size, 2)


# ===============================
# 下单核心
# ===============================
def execute_trade(symbol, token_id, side, price, strength):
    try:
        # 安全检查
        if not price or price <= 0:
            logging.warning("⚠️ 无效价格，跳过")
            return

        size = calc_size(strength)

        logging.info(f"📤 下单准备 | {symbol} | {side} | size={size} | price={price}")

        # ⚠️ Polymarket 规则：
        # 永远 BUY（买 YES 或 NO token）
        order = client.create_order(
            token_id=token_id,
            price=float(price),
            size=float(size),
            side="BUY"
        )

        # 旧版 SDK 有些不需要 sign
        try:
            signed = client.sign_order(order)
            res = client.post_order(signed)
        except:
            # 兼容更老版本
            res = client.post_order(order)

        logging.info(f"✅ 下单返回: {res}")

    except Exception as e:
        logging.error(f"❌ 下单失败: {e}")
