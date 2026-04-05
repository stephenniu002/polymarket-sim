import asyncio
import websockets
import json

markets = {}


async def run_ws(callback):
    url = "wss://clob.polymarket.com/ws"

    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "type": "subscribe",
            "channels": ["trades", "orderbook"]
        }))

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            market = data.get("market")

            if market not in markets:
                markets[market] = {
                    "trades": [],
                    "orderbook": {"bids": [], "asks": []}
                }

            state = markets[market]

            if data.get("type") == "trade":
                state["trades"].append(data)

                if len(state["trades"]) > 50:
                    state["trades"].pop(0)

            elif data.get("type") == "orderbook":
                state["orderbook"] = data

            await callback(market, state)
