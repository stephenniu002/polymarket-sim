import time

def get_balance():
    """获取账户余额 (目前返回模拟值，需对接 SDK)"""
    # 实际对接时可使用 py-clob-client 获取真实余额
    return 100.0

def place_order(token, price, size, side):
    """核心下单函数，对接 main.py 的调用"""
    print(f"🛒 模拟下单执行: {side} {size} @ {price} | Token: {token}")
    # 实际对接时：return client.create_order(...)
    return {"status": "success"}

def safe_order(token, price, size, side, retries=3):
    """带重试机制的下单"""
    for i in range(retries):
        res = place_order(token, price, size, side)
        if "error" not in str(res).lower():
            return res
        time.sleep(2)
    return None
