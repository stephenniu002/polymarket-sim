import time
import asyncio

# ================= 基础参数 =================
BANKROLL = 100
ORDER_SIZE = 2
REPORT_INTERVAL = 300  # 5分钟
last_report = time.time()
last_close = time.time()

# ================= 工具函数 =================

def calc_size_safe(p_yes, p_no):
    edge = 1 - (p_yes + p_no)

    if edge < 0.005:
        return 0, 0

    max_capital = BANKROLL * 0.1
    capital = min(max_capital, edge * 200)

    yes_size = capital * p_no / (p_yes + p_no)
    no_size = capital - yes_size

    return round(yes_size, 2), round(no_size, 2)


def cancel_all():
    try:
        client.cancel_all()
    except:
        pass


def get_balance():
    try:
        return round(usdc_contract.functions.balanceOf(wallet).call() / 1e6, 2)
    except:
        return 0


def close_positions():
    positions = get_positions()
    for p in positions:
        if p["size"] > 0:
            try:
                client.post_order({
                    "price": p["bid"],
                    "size": p["size"],
                    "side": "SELL",
                    "token_id": p["token_id"]
                })
            except:
                pass


def stop_loss():
    positions = get_positions()
    for p in positions:
        if p.get("pnl", 0) < -1:
            try:
                client.post_order({
                    "price": p["bid"],
                    "size": p["size"],
                    "side": "SELL",
                    "token_id": p["token_id"]
                })
                print("❌ 止损执行")
            except:
                pass


def total_open_position():
    positions = get_positions()
    return sum([p["size"] for p in positions])


# ================= 主交易逻辑 =================

async def run():
    global last_report, last_close, BANKROLL

    while True:
        try:
            markets = get_markets()[:20]

            for m in markets:
                tokens = m.get("tokens", [])
                if len(tokens) < 2:
                    continue

                y = tokens[0]["token_id"]
                n = tokens[1]["token_id"]

                y_bid, y_ask = get_book(y)
                n_bid, n_ask = get_book(n)

                if y_ask == 0 or n_ask == 0:
                    continue

                edge = 1 - (y_ask + n_ask)

                print(f"📈 {y_ask:.3f} + {n_ask:.3f} = {y_ask+n_ask:.3f}")

                # ====== 仓位控制 ======
                if total_open_position() > 50:
                    print("⚠️ 仓位过高，暂停")
                    continue

                # ================= A. 强套利 =================
                if edge > 0.015:
                    yes_size, no_size = calc_size_safe(y_ask, n_ask)

                    if yes_size > 0:
                        await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask + 0.001, 3),
                                "size": yes_size,
                                "side": "BUY",
                                "token_id": y
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(n_ask + 0.001, 3),
                                "size": no_size,
                                "side": "BUY",
                                "token_id": n
                            })
                        )

                        print(f"💰 强套利 edge={edge:.4f}")
