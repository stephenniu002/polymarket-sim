async def trade():
    trades = client.get_trades()       # 最近成交
    orderbook = client.get_orderbook() # 盘口

    signal1 = detect_tail_reversal(trades)
    signal2 = orderbook_imbalance(orderbook)
    signal3 = detect_whale(trades)

    signals = [signal1, signal2, signal3]

    # 👉 多信号确认
    if signals.count("BUY") >= 2:
        return "BUY"

    if signals.count("SELL") >= 2:
        return "SELL"

    return None
