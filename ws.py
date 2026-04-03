import asyncio
import websockets
import json
from config import CLOB_WS

async def stream(token_id, callback):
    async with websockets.connect(CLOB_WS) as ws:
        await ws.send(json.dumps({
            "type": "subscribe",
            "channel": "trades",
            "token_id": token_id
        }))

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            if "size" in data:
                size = float(data["size"])

                # 🐋 大单检测
                if size > 100:
                    await callback("WHALE", data)

                await callback("TRADE", data)
