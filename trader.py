import os
import time
import requests
from eth_account import Account

# ===== 环境变量 =====
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
API_KEY = os.getenv("POLY_API_KEY")
SECRET = os.getenv("POLY_SECRET")
PASSPHRASE = os.getenv("POLY_PASSPHRASE")
ADDRESS = os.getenv("POLY_ADDRESS")

acct = Account.from_key(PRIVATE_KEY)

# ===== 下单 =====
def place_order(token, price, size, side):
    order = {
        "token_id": int(token),
        "price": price,
        "size": size,
        "side": side,
        "timestamp": int(time.time())
    }

    headers = {
        "X-Address": ADDRESS,
        "X-API-KEY": API_KEY,
        "X-PASSPHRASE": PASSPHRASE
    }

    try:
        res = requests.post(
            "https://clob.polymarket.com/orders",
            json=order,
            headers=headers
        )
        return res.json()
    except Exception as e:
        print(f"❌ 下单错误: {e}")
        return None


# ===== 安全下单 =====
def safe_order(token, price, size, side, retries=3):
    for i in range(retries):
        res = place_order(token, price, size, side)
        if res and "error" not in str(res):
            return res
        time.sleep(2)

    print("❌ 下单最终失败")
    return None
