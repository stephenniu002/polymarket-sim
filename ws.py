import asyncio
import json
import logging
import websockets

# 直接定义 WebSocket 地址，不再尝试从 config 导入
# 这是 Polymarket 的标准 WebSocket 地址
CLOB_WS = "wss://clob.polymarket.com/ws"

logger = logging.getLogger("LOBSTER-WS")

async def stream(token_id, callback):
    """监听 WebSocket 并回调数据给 main.py 的 hunting_filter"""
    payload = {
        "type": "subscribe",
        "assets_ids": [token_id],
        "channels": ["trades"]
    }
    
    # 建立 WebSocket 长连接
    async for websocket in websockets.connect(CLOB_WS):
        try:
            await websocket.send(json.dumps(payload))
            logger.info(f"📡 监听开启 (Token: {token_id[:8]})")
            
            async for message in websocket:
                data = json.loads(message)
                # 处理不同格式的推送数据，确保回调给 hunting_filter
                if isinstance(data, list):
                    for item in data:
                        await callback("TRADE", item)
                elif data.get("event_type") == "trades" or "price" in data:
                    await callback("TRADE", data)
                    
        except Exception as e:
            # 自动重连机制
            logger.warning(f"🔄 连接中断 ({e})，正在尝试重连...")
            await asyncio.sleep(5)
