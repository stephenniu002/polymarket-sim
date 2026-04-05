import asyncio
import websockets
import json
import logging
import time
import os

# ==========================================
# 1. 基础配置
# ==========================================
try:
    from trade import execute_trade 
    from strategy import generate_signal
    from config import MARKET_MAP, POLY_ADDRESS
    logging.info("✅ 配置文件加载成功")
except ImportError:
    MARKET_MAP = {}
    POLY_ADDRESS = os.getenv("POLY_ADDRESS")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 🚀 三路备选地址列表
WS_ENDPOINTS = [
    "wss://clob.polymarket.com/ws/trades",              # 方案 A (你提供的最新路径)
    "wss://ws-subscriptions-clob.polymarket.com/ws",    # 方案 B (高稳订阅节点)
    "wss://clob.polymarket.com/ws/"                     # 方案 C (带斜杠根路径)
]

WATCH_TOKENS = []
for m in MARKET_MAP.values():
    if "UP" in m: WATCH_TOKENS.append(m["UP"])
    if "DOWN" in m: WATCH_TOKENS.append(m["DOWN"])

markets_state = {}
cooldowns = {}
COOLDOWN_SECONDS = 20

# ==========================================
# 2. 逻辑处理器
# ==========================================
async def handle_market_event(data):
    # 兼容新版 trades 频道返回的数据格式
    m_id = data.get("market")
    t_id = data.get("token_id")
    price = data.get("price")
    
    if not m_id or not t_id or not price: return

    if m_id not in markets_state:
        markets_state[m_id] = {"trades": [], "last_price": None, "last_token": t_id}
    
    state = markets_state[m_id]
    state["trades"].append(data)
    if len(state["trades"]) > 30: state["trades"].pop(0)
    state["last_price"] = price

    now = time.time()
    if m_id in cooldowns and now - cooldowns[m_id] < COOLDOWN_SECONDS:
        return

    signal = generate_signal(state)
    if signal:
        symbol = "UNKNOWN"
        for k, v in MARKET_MAP.items():
            if t_id in [v.get("UP"), v.get("DOWN")]:
                symbol = k
                break
        
        strength = min(len(state["trades"]) / 25, 1.0)
        logging.info(f"🎯 [SIGNAL] {symbol} | {signal} | 价格: {price} | 强度: {strength:.2f}")
        execute_trade(symbol, t_id, signal, price, strength)
        cooldowns[m_id] = now

# ==========================================
# 3. 核心引擎 (带自动 Fallback 逻辑)
# ==========================================
async def run_lobster_ws():
    logging.info(f"🚀 龙虾系统启动 | 监听钱包: {POLY_ADDRESS}")
    
    if not WATCH_TOKENS:
        logging.error("❌ 监听列表为空，请检查 config.py")
        return

    endpoint_idx = 0
    headers = {"User-Agent": "Mozilla/5.0", "Origin": "https://polymarket.com"}

    while True:
        current_url = WS_ENDPOINTS[endpoint_idx % len(WS_ENDPOINTS)]
        try:
            logging.info(f"📡 正在尝试连接 Endpoint [{endpoint_idx % len(WS_ENDPOINTS)}]: {current_url}")
            
            async with websockets.connect(current_url, additional_headers=headers) as ws:
                logging.info("✅ WebSocket 握手成功 (101)")
                
                # 🚀 采用你提供的新版订阅格式
                subscribe_msg = {
                    "type": "subscribe",
                    "channel": "trades",
                    "token_ids": WATCH_TOKENS
                }
                await ws.send(json.dumps(subscribe_msg))
                logging.info(f"📡 订阅已发送 (token_ids 模式)，监控资产数: {len(WATCH_TOKENS)}")
                
                async for msg in ws:
                    data = json.loads(msg)
                    # 某些 endpoint 返回的是消息包装格式，提取里面的 data
                    payload = data.get("data") if "data" in data else data
                    
                    if isinstance(payload, list):
                        for item in payload: await handle_market_event(item)
                    else:
                        await handle_market_event(payload)

        except Exception as e:
            logging.warning(f"⚠️ Endpoint 失败: {e}")
            endpoint_idx += 1  # 切换到下一个地址
            wait_time = 5 if "404" not in str(e) else 1
            logging.info(f"🔄 {wait_time}秒后尝试下一个备选地址...")
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    try:
        asyncio.run(run_lobster_ws())
    except KeyboardInterrupt:
        logging.info("🛑 龙虾火控下线")
