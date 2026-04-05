from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
import os

# ===============================
# 初始化（只做一次）
# ===============================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("POLY_API_KEY"),
    secret=os.getenv("POLY_SECRET"),
    passphrase=os.getenv("POLY_PASSPHRASE"),
    chain_id=POLYGON,
    private_key=os.getenv("PRIVATE_KEY")
)

# 🔥 很关键（有些环境必须）
try:
    client.derive_api_key()
    print("✅ API 已激活")
except:
    pass


# ===============================
# 下单（最终版）
# ===============================
def place_order(token_id, side):
    try:
        print(f"🧪 准备下单: {side} | {token_id}")

        if not REAL_TRADE:
            print("⚠️ 当前模拟模式")
            return

        # ⚠️ Polymarket 规则：
        # BUY = 买这个 token（YES 或 NO）
        # SELL = 卖（一般不用）

        order = client.create_order(
            token_id=token_id,
            price=0.5,   # 建议后面换成盘口价
            size=1.0,    # 先小仓测试
            side="BUY"
        )

        signed = client.sign_order(order)

        res = client.post_order(signed)

        print("📤 下单成功:", res)

    except Exception as e:
        print("❌ 下单失败:", e)
