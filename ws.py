import asyncio
import json
import logging
import websockets

# 直接定义 WebSocket 地址，不再从 config 导入
CLOB_WS = "wss://clob.polymarket.com/ws"
logger = logging.getLogger("LOBSTER-WS")

async def stream(token_id, callback):
    """监听 WebSocket 并回调 hunting_filter"""
    payload = {
        "type": "subscribe",
        "assets_ids": [token_id],
        "channels": ["trades"]
    }
    
    # 建立长连接
    async for websocket in websockets.connect(CLOB_WS):
        try:
            await websocket.send(json.dumps(payload))
            logger.info(f"📡 监听开启: {token_id[:8]}...")
            
            async for message in websocket:
                data = json.loads(message)
                # 处理不同格式的交易数据
                if isinstance(data, list):
                    for item in data:
                        await callback("TRADE", item)
                else:
                    await callback("TRADE", data)
                    
        except Exception as e:
            logger.warning(f"🔄 连接中断 ({e})，5秒后重连...")
            await asyncio.sleep(5)
