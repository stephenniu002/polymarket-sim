import asyncio
import websockets
import json
import logging
import time
import os

# ==========================================
# 核心对齐：从 config 导入 MARKET_MAP
# ==========================================
try:
    from trade import execute_trade 
    from strategy import generate_signal
    from config import MARKET_MAP, POLY_ADDRESS
    logging.info("✅ 配置文件加载成功")
except ImportError as e:
    logging.error(f"❌ 导入失败: {e}。请检查 config.py 是否有 MARKET_MAP 变量。")
    # 应急处理：如果导入失败，防止系统崩溃
    MARKET_MAP = {}
    POLY_ADDRESS = None

# 日志配置
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
)

WS_URL = "wss://clob.polymarket.com/ws"

# ==========================================
# 1. 资产监听列表 (对齐 UP/DOWN 键)
# ==========================================
WATCH_TOKENS = []
for m in MARKET_MAP.values():
    if "UP" in m: WATCH_TOKENS.append(m["UP"])
    if "DOWN" in m: WATCH_TOKENS.append(m["DOWN"])

# 状态追踪
markets_state = {}
cooldowns = {}
COOLDOWN_SECONDS = 30 

# ==========================================
# 2. 核心逻辑处理
# ==========================================
async def handle_market_event(market_id, state):
    now = time.time()

    # 1️⃣ 冷却检查
    if market_id in cooldowns and now - cooldowns[market_id] < COOLDOWN_SECONDS:
        return

    # 2️⃣ 信号生成
    signal = generate_signal(state)
    if not signal:
        return

    # 3️⃣ 匹配 Symbol 和 Token
    symbol = None
    token_id = state.get("last_token")
    
    for k, v in MARKET_MAP.items():
        if token_id in [v.get("UP"), v.get("DOWN")]:
            symbol = k
            break
    
    if not symbol or not state.get("last_price"): 
        return

    # 4️⃣ 强度计算
    strength = min(len(state.get("trades", [])) / 50, 1.0)
    
    # 5️⃣ 执行交易 (调用 trade.py)
    logging.info(f"🎯 信号触发 | {symbol} | {signal} | 价格: {state['last_price']} | 强度: {strength:.2f}")
    
    # 执行下单逻辑
    execute_trade(symbol, token_id, signal, state["last_price"], strength)

    # 6️⃣ 记录冷却
    cooldowns[market_id] = now

# ==========================================
# 3. WebSocket 引擎
# ==========================================
async def run_lobster_ws():
    logging.info(f"🚀 龙虾系统启动 | 监听地址: {POLY_ADDRESS}")
    
    if not WATCH_TOKENS:
        logging.error("❌ 监听列表为空，请检查 config.py 的 MARKET_MAP 配置！")
        return

    async for ws in websockets.connect(WS_URL):
        try:
            # 订阅频道
            subscribe_msg = {
                "type": "subscribe",
                "channels": ["trades", "orderbook"],
                "tokens": WATCH_TOKENS
            }
            await ws.send(json.dumps(subscribe_msg))
            logging.info(f"📡 已连接 WS | 正在监听 {len(WATCH_TOKENS)} 个资产 ID")

            while True:
                msg = await ws.recv()
                data = json.loads(msg)

                m_id = data.get("market")
                t_id = data.get("token_id")

                if not m_id or not t_id: continue

                # 初始化市场状态
                if m_id not in markets_state:
                    markets_state[m_id] = {
                        "trades": [],
                        "orderbook": {"bids": [], "asks": []},
                        "last_price": None,
                        "last_token": None
                    }

                state = markets_state[m_id]

                # 更新数据
                if data.get("type") == "trade":
                    state["trades"].append(data)
                    if len(state["trades"]) > 50: state["trades"].pop(0)
                    state["last_price"] = data.get("price")
                    state["last_token"] = t_id

                elif data.get("type") == "orderbook":
                    state["orderbook"] = data

                # 触发处理逻辑
                await handle_market_event(m_id, state)

        except websockets.ConnectionClosed:
            logging.warning("⚠️ WS 连接断开，5秒后重连...")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            logging.error(f"❌ 运行异常: {e}")
            await asyncio.sleep(2)

# ==========================================
# 4. 启动入口
# ==========================================
if __name__ == "__main__":
    try:
        asyncio.run(run_lobster_ws())
    except KeyboardInterrupt:
        logging.info("🛑 系统手动停止")
