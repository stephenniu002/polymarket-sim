import requests
import os
import time
import random

API_KEY = os.getenv("POLY_API_KEY")

BASE = "https://clob.polymarket.com"

# ⚠️ 安全开关（先不要关）
REAL_TRADE = False


# ===============================
# 1️⃣ 检查余额
# ===============================
def check_balance():
    try:
        url = f"{BASE}/positions"
        headers = {"Authorization": f"Bearer {API_KEY}"}

        res = requests.get(url, headers=headers, timeout=10)

        print("💰 余额:", res.text)

        return res.json()

    except Exception as e:
        print("❌ 余额错误:", e)
        return None


# ===============================
# 2️⃣ 获取市场（更稳版本）
# ===============================
def get_market():
    try:
        url = f"{BASE}/markets"
        res = requests.get(url, timeout=10)
        data = res.json()

        for m in data:
            if not m.get("active"):
                continue

            tokens = m.get("tokens", [])
            if len(tokens) < 2:
                continue

            yes_token = tokens[0].get("token_id")
            no_token = tokens[1].get("token_id")

            if yes_token and no_token:
                print("🎯 市场:", m.get("question"))
                print("YES:", yes_token)
                print("NO :", no_token)

                return yes_token, no_token

        return None, None

    except Exception as e:
        print("❌ 市场错误:", e)
        return None, None


# ===============================
# 3️⃣ 策略（先简单）
# ===============================
def get_signal():
    r = random.random()

    if r > 0.65:
        return "YES"
    elif r < 0.35:
        return "NO"
    return None


# ===============================
# 4️⃣ 下单（安全版）
# ===============================
def place_order(token_id, side):
    try:
        print(f"🧪 准备下单: {side} | {token_id}")

        if not REAL_TRADE:
            print("⚠️ 当前为模拟模式（未真实下单）")
            return

        url = f"{BASE}/orders"

        payload = {
            "token_id": token_id,
            "side": side,
            "price": 0.5,
            "size": 1
        }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        res = requests.post(url, json=payload, headers=headers, timeout=10)

        print("📤 下单返回:", res.text)

    except Exception as e:
        print("❌ 下单失败:", e)


# ===============================
# 主循环
# ===============================
def main():
    print("🚀 Polymarket Bot V27.3 启动（稳定版）")

    while True:
        print("\n⏰ 新一轮")

        # 1️⃣ 查余额
        check_balance()

        # 2️⃣ 获取市场
        yes_token, no_token = get_market()

        if not yes_token:
            print("❌ 无市场")
            time.sleep(60)
            continue

        # 3️⃣ 信号
        signal = get_signal()

        if not signal:
            print("😴 无信号")
            time.sleep(60)
            continue

        print("📊 信号:", signal)

        # 4️⃣ 下单
        if signal == "YES":
            place_order(yes_token, "YES")
        else:
            place_order(no_token, "NO")

        time.sleep(60)


if __name__ == "__main__":
    main()
