import websockets
import json
import asyncio

WS_URL = "wss://clob.polymarket.com/ws"

async def stream_orderbook(token_id, callback):
    async with websockets.connect(WS_URL) as ws:
        sub_msg = {
            "type": "subscribe",
            "channel": "orderbook",
            "token_id": str(token_id)
        }
        await ws.send(json.dumps(sub_msg))

        while True:
            data = await ws.recv()
            msg = json.loads(data)

            if "bids" in msg or "asks" in msg:
                await callback(token_id, msg)
