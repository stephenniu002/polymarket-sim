import asyncio
import websockets
import json
import logging
import time
import os

# 核心导入：确保从你修复后的 trade.py 导入
from trade import execute_trade 
from strategy import generate_signal
from config import MARKETS

# 日志配置
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
)

WS_URL = "wss://clob.polymarket.com/ws"

# ===============================
# 1. 资产监控 (针对 0xd962...CB24)
# ===============================
WATCH_TOKENS = []
for m in MARKETS.values():
    WATCH_TOKENS += [m["YES"], m["NO"]]

# 状态追踪
markets_state = {}
cooldowns = {}
COOLDOWN_SECONDS = 30 

# ===============================
# 2. 核心逻辑处理
# ===============================
async def handle_market_event(market_id, state):
    now = time.time()

    # 1️⃣ 冷却检查
    if market_id in cooldowns and now - cooldowns[market_id] < COOLDOWN_SECONDS:
        return

    # 2️⃣ 信号生成 (基于实时 Orderbook/Trades)
    signal = generate_signal(state)
    if not signal:
        return

    # 3️⃣ 数据完整性检查
    if not state.get("last_price") or not state.get("last_token"):
        return

    # 4️⃣ 匹配 Symbol
    symbol = None
    for k, v in MARKETS.items():
        if state["last_token"] in [v["YES"], v["NO"]]:
            symbol = k
            break
    
    if not symbol: return

    # 5️⃣ 强度计算 (基于最近成交密度)
    strength = min(len(state["trades"]) / 50, 1.0)
    
    # 6️⃣ 执行交易 (调用 trade.py 中的函数)
    logging.info(f"🎯 触发信号 | {symbol} | {signal} | 价格: {state['last_price']} | 强度: {strength:.2f}")
    
    # 锁定 0xd962 地址的资产进行下单
    execute_trade(symbol, state["last_token"], signal, state["last_price"], strength)

    # 7️⃣ 记录冷却
    cooldowns[market_id] = now

# ===============================
# 3. WebSocket 引擎
# ===============================
async def run_lobster_ws():
    logging.info("🚀 龙虾火控系统 V31 Pro 启动 | 目标地址: 0xd962...CB24")
    
    async for ws in websockets.connect(WS_URL):
        try:
            # 订阅频道
            subscribe_msg = {
                "type": "subscribe",
                "channels": ["trades", "orderbook"],
                "tokens": WATCH_TOKENS
            }
            await ws.send(json.dumps(subscribe_msg))
            logging.info(f"📡 已连接 Polymarket WS | 正在监听 {len(WATCH_TOKENS)} 个 Token")

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

                # 触发逻辑处理
                await handle_market_event(m_id, state)

        except websockets.ConnectionClosed:
            logging.warning("⚠️ WS 连接断开，正在尝试重连...")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            logging.error(f"❌ 运行异常: {e}")
            await asyncio.sleep(2)

# ===============================
# 4. 启动
# ===============================
if __name__ == "__main__":
    try:
        asyncio.run(run_lobster_ws())
    except KeyboardInterrupt:
        logging.info("🛑 系统手动停止")
