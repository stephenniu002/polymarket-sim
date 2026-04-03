import asyncio
import time
from market import load_tokens
from ws import stream
from strategy import Strategy
from trader import safe_order, positions, save_positions, load_positions
from reporter import Reporter
from config import TRADE_SIZE

# ===== 初始化 =====
reporter = Reporter()
balance = 1000
market_score = {}
last_trade_time = {}
strategies_stats = {
    "tail": {"win": 1, "lose": 1},
    "deep": {"win": 1, "lose": 1}
}

# ===== 工具函数 =====

def update_market_score(token, size):
    market_score[token] = market_score.get(token, 0) + size

def top_markets():
    sorted_m = sorted(market_score.items(), key=lambda x: x[1], reverse=True)
    return [m[0] for m in sorted_m[:2]]

def winrate(name):
    s = strategies_stats[name]
    total = s["win"] + s["lose"]
    return s["win"] / total if total else 0.5

def kelly(wr, rr=2):
    return max(0, wr - (1 - wr) / rr)

def calc_size(balance, strategy):
    wr = winrate(strategy)
    k = min(kelly(wr), 0.2)
    return balance * k

def can_trade(token):
    now = time.time()
    if token in last_trade_time and now - last_trade_time[token] < 300:
        return False
    last_trade_time[token] = now
    return True

# ===== 核心市场逻辑 =====

async def run_market(m):
    global balance

    strat = Strategy()
    token = m["token"]

    async def on_msg(data):
        global balance

        price = float(data["price"])
        size = float(data["size"])

        strat.update(price, size)
        update_market_score(token, size)

        # ===== 策略信号 =====
        sig = strat.signal()
        if not sig:
            return

        # ===== 市场筛选 =====
        if token not in top_markets():
            return

        # ===== 冷却 =====
        if not can_trade(token):
            return

        # ===== 策略选择 =====
        strategy = "deep" if price < 0.2 else "tail"

        # ===== 仓位 =====
        trade_size = calc_size(balance, strategy)
        if trade_size <= 0:
            return

        # ===== 下单 =====
        res = safe_order(token, price, trade_size, "BUY")

        if not res:
            return

        positions[token] = {
            "entry": price,
            "size": trade_size,
            "sold": False,
            "strategy": strategy
        }

        save_positions()

        print(f"🟢 BUY {token} {price} size={trade_size}")

    await stream(token, on_msg)

# ===== 持仓管理 =====

async def manage_positions():
    global balance

    while True:
        for token, pos in list(positions.items()):
            price = pos.get("last_price", pos["entry"])

            # 🎯 0.50 卖75%
            if price >= 0.5 and not pos["sold"]:
                sell_size = pos["size"] * 0.75
                safe_order(token, price, sell_size, "SELL")

                pos["size"] *= 0.25
                pos["sold"] = True

            # 🔒 回撤保护
            if pos["sold"] and price < 0.45:
                safe_order(token, price, pos["size"], "SELL")

                pnl = (price - pos["entry"]) * pos["size"]
                balance += pnl

                # 📊 记录
                strat = pos["strategy"]
                if pnl > 0:
                    strategies_stats[strat]["win"] += 1
                else:
                    strategies_stats[strat]["lose"] += 1

                reporter.record_trade(token, pnl, strat)
                reporter.update_balance(balance)

                positions.pop(token)
                save_positions()

        await asyncio.sleep(5)

# ===== 心跳 =====

async def heartbeat():
    while True:
        print(f"💓 alive | balance={balance:.2f}")
        await asyncio.sleep(60)

# ===== 主入口 =====

async def main():
    load_positions()

    markets = load_tokens()

    tasks = [run_market(m) for m in markets]

    await asyncio.gather(
        *tasks,
        manage_positions(),
        heartbeat()
    )

if __name__ == "__main__":
    asyncio.run(main())
