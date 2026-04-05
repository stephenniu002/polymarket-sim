def detect_tail(trades):
    if len(trades) < 5:
        return None

    prices = [t["price"] for t in trades[-5:]]

    if prices[-1] < 0.2 and prices[-1] > prices[0]:
        return "BUY"

    if prices[-1] > 0.8 and prices[-1] < prices[0]:
        return "SELL"

    return None


def detect_imbalance(orderbook):
    bids = sum([b[1] for b in orderbook.get("bids", [])[:5]])
    asks = sum([a[1] for a in orderbook.get("asks", [])[:5]])

    if bids > asks * 2:
        return "BUY"
    if asks > bids * 2:
        return "SELL"

    return None


def detect_whale(trades):
    if len(trades) < 5:
        return None

    sizes = [t["size"] for t in trades[-10:]]
    avg = sum(sizes) / len(sizes)

    for t in trades[-3:]:
        if t["size"] > avg * 5:
            return "BUY" if t["side"] == "buy" else "SELL"

    return None


def generate_signal(state):
    s1 = detect_tail(state["trades"])
    s2 = detect_imbalance(state["orderbook"])
    s3 = detect_whale(state["trades"])

    signals = [s1, s2, s3]

    if signals.count("BUY") >= 2:
        return "BUY"
    if signals.count("SELL") >= 2:
        return "SELL"

    return None
