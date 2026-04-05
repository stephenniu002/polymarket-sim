import asyncio
import websockets
import json
import logging
import time
import os

# ==========================================
# 1. 配置加载 (对齐 config.py)
# ==========================================
try:
    from trade import execute_trade 
    from strategy import generate_signal
    from config import MARKET_MAP, POLY_ADDRESS
    logging.info("✅ 配置文件加载成功")
except ImportError:
    MARKET_MAP = {}
    POLY_ADDRESS = os.getenv("POLY_ADDRESS", "0xd962C11e253e38EB86303F1462818c4aac17CB24")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ⚠️ 尝试最标准的路径
WS_URL = "wss://clob.polymarket.com/ws/v1" 

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
    
    if data.get("type") == "trade":
        state["trades"].append(data)
        if len(state["trades"]) > 30: state["trades"].pop(0)
        state["last_price"] = data.get("price")
        state["last_token"] = t_id
        
        if m_id in cooldowns and now - cooldowns[m_id] < COOLDOWN_SECONDS:
            return

        signal = generate_signal(state)
        if signal:
            symbol = "UNKNOWN"
            for k, v in MARKET_MAP.items():
                if t_id in [v.get("UP"), v.get("DOWN")]:
                    symbol = k
                    break
            
            strength = min(len(state["trades"]) / 30, 1.0)
            logging.info(f"🎯 [SIGNAL] {symbol} | {signal} | 价格: {state['last_price']} | 强度: {strength:.2f}")
            execute_trade(symbol, t_id, signal, state["last_price"], strength)
            cooldowns[m_id] = now

# ==========================================
# 3. 核心引擎 (删除报错参数 extra_headers)
# ==========================================
async def run_lobster_ws():
    logging.info(f"🚀 龙虾系统启动 | 目标地址: {POLY_ADDRESS}")
    
    if not WATCH_TOKENS:
        logging.error("❌ 监听列表为空！请检查 config.py")
        return

    while True:
        try:
            logging.info(f"📡 正在尝试连接: {WS_URL}")
            # 去掉 extra_headers，避免版本不兼容报错
            async with websockets.connect(WS_URL) as ws:
                logging.info("✅ WebSocket 连接成功 (101)")
                
                subscribe_msg = {
                    "type": "subscribe",
                    "channels": ["trades"],
                    "tokens": WATCH_TOKENS
                }
                await ws.send(json.dumps(subscribe_msg))
                logging.info(f"📡 已订阅 {len(WATCH_TOKENS)} 个资产 ID")
                
                async for msg in ws:
                    data = json.loads(msg)
                    m_id = data.get("market")
                    t_id = data.get("token_id")
                    if m_id and t_id:
                        await handle_market_event(m_id, t_id, data)

        except Exception as e:
            # 如果 v1 路径报 404，打印出来我们换路径
            logging.warning(f"⚠️ 连接状态: {e}, 5秒后重试...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_lobster_ws())
    except KeyboardInterrupt:
        logging.info("🛑 停止")
