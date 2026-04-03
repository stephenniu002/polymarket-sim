import requests
import time

def safe_order(token, price, size, side, retries=3):
    for i in range(retries):
        try:
            res = place_order(token, price, size, side)

            if "error" not in str(res):
                return res

        except Exception as e:
            print(f"⚠️ 下单失败: {e}")

        time.sleep(2)

    print("❌ 下单最终失败")
    return None
