import asyncio
import websockets
import json
from config import CLOB_WS

async def stream(token, callback):
    while True:
        try:
            print(f"🔌 连接 WS: {token}")

            async with websockets.connect(CLOB_WS, ping_interval=20) as ws:
                await ws.send(json.dumps({
                    "type": "subscribe",
                    "channel": "trades",
                    "token_id": token
                }))

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    if "price" in data:
                        await callback(data)

        except Exception as e:
            print(f"⚠️ WS断线: {e}，5秒重连...")
            await asyncio.sleep(5)
