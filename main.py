import asyncio
import json
import websockets
import time

from strategy import TailStrategy
from stats import Stats
from notify import send

MARKETS = {
    "ETH": "wss://stream.binance.com:9443/ws/ethusdt@trade",
    "BTC": "wss://stream.binance.com:9443/ws/btcusdt@trade"
}

strategies = {k: TailStrategy() for k in MARKETS}
stats_map = {k: Stats() for k in MARKETS}

pending_trades = []

BET = 10

async def run_market(name, url):
    async with websockets.connect(url) as ws:
        print(f"🟢 {name} 已连接")

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            price = float(data["p"])
            strategies[name].update(price)

            # 触发信号
            if strategies[name].signal():
                pending_trades.append({
                    "market": name,
                    "entry": price,
                    "time": time.time()
                })

async def settlement_loop():
    while True:
        now = time.time()

        for trade in pending_trades[:]:
            if now - trade["time"] > 60:
                market = trade["market"]
                entry = trade["entry"]

                prices = strategies[market].prices[-60:]

                win = max(prices) > entry * 1.003

                stats_map[market].record(win)

                pending_trades.remove(trade)

        await asyncio.sleep(1)

async def report_loop():
    while True:
        await asyncio.sleep(300)

        msg = "📊 多市场尾部套利报告\n\n"

        for m, s in stats_map.items():
            data = s.summary()
            if not data:
                continue

            msg += f"【{m}】\n"
            msg += f"交易: {data['trades']}\n"
            msg += f"胜率: {data['win_rate']:.2%}\n"
            msg += f"ROI: {data['roi']:.2f}\n"
            msg += f"余额: ${data['balance']}\n\n"

        await send(msg)
        print(msg)

async def main():
    tasks = []

    for name, url in MARKETS.items():
        tasks.append(asyncio.create_task(run_market(name, url)))

    tasks.append(asyncio.create_task(settlement_loop()))
    tasks.append(asyncio.create_task(report_loop()))

    await asyncio.gather(*tasks)

asyncio.run(main())
