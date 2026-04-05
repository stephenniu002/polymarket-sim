import requests
import os
import time

API_KEY = os.getenv("POLY_API_KEY")

BASE = "https://clob.polymarket.com"


# ===============================
# 1️⃣ 检查 API / 余额
# ===============================
def check_balance():
    try:
        url = f"{BASE}/positions"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        res = requests.get(url, headers=headers, timeout=10)

        print("💰 余额返回:", res.text)

        return res.json()
    except Exception as e:
        print("❌ 余额错误:", e)
        return None


# ===============================
# 2️⃣ 获取市场（自动找 token）
# ===============================
def get_markets():
    try:
        url = f"{BASE}/markets"
        res = requests.get(url, timeout=10)
        data = res.json()

        # 找第一个可交易市场
        for m in data:
            if "tokens" in m and len(m["tokens"]) >= 2:
                yes_token = m["tokens"][0]["token_id"]
                no_token = m["tokens"][1]["token_id"]

                print("🎯 市场:", m.get("question"))
                print("YES:", yes_token)
                print("NO :", no_token)

                return yes_token, no_token

        return None, None

    except Exception as e:
        print("❌ 市场获取失败:", e)
        return None, None


# ===============================
# 3️⃣ 简单策略（先能跑）
# ===============================
def get_signal():
    import random
    r = random.random()

    if r > 0.6:
        return "YES"
    elif r < 0.4:
        return "NO"
    return None


# ===============================
# 4️⃣ 下单（真实）
# ===============================
def place_order(token_id, side):
    try:
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

        res = requests.post(url, json=payload, headers=headers)

        print("📤 下单返回:", res.text)

    except Exception as e:
        print("❌ 下单失败:", e)


# ===============================
# 主循环
# ===============================
def main():
    print("🚀 Polymarket Bot V27.2 启动")

    while True:
        print("\n⏰ 新一轮")

        # 1️⃣ 查余额
        check_balance()

        # 2️⃣ 拿市场
        yes_token, no_token = get_markets()

        if not yes_token:
            print("❌ 没找到市场")
            time.sleep(60)
            continue

        # 3️⃣ 策略
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
