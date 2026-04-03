import time

buffer = []

def signal(trade):
    now = time.time()
    buffer.append((now, float(trade["price"])))

    # 保留30秒
    global buffer
    buffer = [(t, p) for t, p in buffer if now - t < 30]

    if len(buffer) < 5:
        return None

    prices = [p for _, p in buffer]

    # 尾部反转逻辑
    if prices[-1] > max(prices[:-1]):
        return "BUY"

    if prices[-1] < min(prices[:-1]):
        return "SELL"

    return None

        # 👉 可调核心参数
        if distance < 0.003 and rebound > 0.006:
            return True

        return False
