import asyncio
import websockets
import json
import logging
import time
import os

# ==========================================
# 1. 配置文件加载
# ==========================================
try:
    from trade import execute_trade 
    from strategy import generate_signal
    from config import MARKET_MAP, POLY_ADDRESS
    logging.info("✅ config.py 加载成功")
except ImportError:
    MARKET_MAP = {}
    POLY_ADDRESS = os.getenv("POLY_ADDRESS")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ⚠️ 采用你提供的特定频道路径
WS_URL = "wss://clob.polymarket.com/ws/trades" 

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
async def handle_market_event(m_id, t_id, data):
    now = time.time()
    if m_id not in markets_state:
        markets_state[m_id] = {"trades": [], "last_price": None, "last_token": None}
    
    state = markets_state[m_id]
    
    # 因为连接的是 trades 频道，收到的数据直接就是 trade 类型
    state["trades"].append(data)
    if len(state["trades"]) > 30: state["trades"].pop(0)
    state["last_price"] = data.get("price")
    state["last_token"] = t_id
    
    # 冷却检查
    if m_id in cooldowns and now - cooldowns[m_id] < COOLDOWN_SECONDS:
        return

    # 信号生成
    signal = generate_signal(state)
    if signal:
        symbol = "UNKNOWN"
        for k, v in MARKET_MAP.items():
            if t_id in [v.get("UP"), v.get("DOWN")]:
                symbol = k
                break
        
        strength = min(len(state["trades"]) / 30, 1.0)
        logging.info(f"🎯 [SIGNAL] {symbol} | {signal} | 价: {state['last_price']} | 强: {strength:.2f}")
        execute_trade(symbol, t_id, signal, state["last_price"], strength)
        cooldowns[m_id] = now

# ==========================================
# 3. WebSocket 引擎 (对齐 trades 频道)
# ==========================================
async def run_lobster_ws():
    logging.info(f"🚀 龙虾系统启动 | 监听钱包: {POLY_ADDRESS}")
    
    if not WATCH_TOKENS:
        logging.error("❌ 监听列表为空！")
        return

    # 模拟真实客户端 Header
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://polymarket.com"
    }

    while True:
        try:
            logging.info(f"📡 正在连接特定频道: {WS_URL}")
            # 使用 additional_headers 适配最新 websockets 库
            async with websockets.connect(WS_URL, additional_headers=headers) as ws:
                logging.info("✅ WebSocket 握手成功 (101)")
                
                # 在 trades 特定频道下，有时只需要发送 token 列表
                subscribe_msg = {
                    "type": "subscribe",
                    "tokens": WATCH_TOKENS
                }
                await ws.send(json.dumps(subscribe_msg))
                logging.info(f"📡 订阅发送完成，监控 {len(WATCH_TOKENS)} 个资产 ID")
                
                async for msg in ws:
                    data = json.loads(msg)
                    # 某些版本的 trades 频道返回的是数组或列表，进行兼容性处理
                    if isinstance(data, list):
                        for item in data:
                            m_id = item.get("market")
                            t_id = item.get("token_id")
                            if m_id and t_id:
                                await handle_market_event(m_id, t_id, item)
                    else:
                        m_id = data.get("market")
                        t_id = data.get("token_id")
                        if m_id and t_id:
                            await handle_market_event(m_id, t_id, data)

        except Exception as e:
            logging.warning(f"⚠️ 连接状态异常: {e}, 5秒后尝试重连...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_lobster_ws())
    except KeyboardInterrupt:
        logging.info("🛑 龙虾火控下线")
