import os
import time
import requests
from eth_account import Account

# ===== 环境变量 (请确保在 Railway Variables 中配置好这些名称) =====
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
API_KEY = os.getenv("POLY_API_KEY")
SECRET = os.getenv("POLY_SECRET")
PASSPHRASE = os.getenv("POLY_PASSPHRASE")
ADDRESS = os.getenv("POLY_ADDRESS")

# 初始化账户（验证私钥有效性）
try:
    if PRIVATE_KEY:
        acct = Account.from_key(PRIVATE_KEY)
except Exception as e:
    print(f"⚠️ 私钥配置错误: {e}")

# ===== 获取真实余额 =====
def get_balance():
    """获取 Polymarket 账户的真实 USDC 余额"""
    if not ADDRESS:
        return 0.0
    
    url = f"https://clob.polymarket.com/balance?address={ADDRESS}"
    headers = {
        "X-API-KEY": API_KEY,
        "X-PASSPHRASE": PASSPHRASE
    }
    
    try:
        # 注意：这里需要根据 API 返回结构解析，通常是返回 balance 字段
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        
        # 假设返回格式为 {"balance": "100.50"}
        balance = data.get("balance", "0.0")
        return round(float(balance), 2)
    except Exception as e:
        print(f"❌ 获取余额错误: {e}")
        return 0.0

# ===== 下单 =====
def place_order(token, price, size, side):
    """核心下单函数：返回字典表示结果"""
    if not all([ADDRESS, API_KEY]):
        return {"error": "Missing credentials"}

    order = {
        "token_id": str(token), # 确保是字符串格式的 ID
        "price": price,
        "size": size,
        "side": side.upper(), # BUY 或 SELL
        "timestamp": int(time.time())
    }

    headers = {
        "X-Address": ADDRESS,
        "X-API-KEY": API_KEY,
        "X-PASSPHRASE": PASSPHRASE,
        "X-SECRET": SECRET
    }

    try:
        res = requests.post(
            "https://clob.polymarket.com/orders",
            json=order,
            headers=headers,
            timeout=10
        )
        return res.json()
    except Exception as e:
        print(f"❌ 下单错误: {e}")
        return {"error": str(e)}

# ===== 安全下单 =====
def safe_order(token, price, size, side, retries=3):
    """带重试机制的下单，返回布尔值便于 main.py 统计"""
    for i in range(retries):
        res = place_order(token, price, size, side)
        if res and "error" not in str(res).lower():
            return True # 下单成功
        time.sleep(2)

    print("❌ 下单最终失败")
    return False # 下单失败
