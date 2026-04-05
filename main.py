import asyncio
import websockets
import json
import logging
import os

from trade import execute_trade   # ✅ 注意：这里用 trade.py
from strategy import generate_signal
from config import MARKETS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===============================
# 初始化
# ===============================
WS_URL = "wss://clob.polymarket.com/ws"

# 收集所有 token
WATCH_TOKENS = []
for m in MARKETS.values():
    WATCH_TOKENS.append(m["YES"])
    WATCH_TOKENS.append(m["NO"])

# 市场状态缓存
markets = {}

# 冷却机制（防止疯狂下单）
cooldown = {}

COOLDOWN_TIME = 60  # 秒


# ===============================
# 核心处理逻辑
# ===============================
async def handle_market(market, state):
    # 冷却中
    if market in cooldown:
        return

    signal = generate_signal(state)

    if not signal:
        return

    # 强度（简单版：交易数量）
    strength = len(state["trades"])

    # 找 symbol（BTC / ETH 等）
    symbol = None
    for k, v in MARKETS.items():
        if state["last_token"] in [v["YES"], v["NO"]]:
            symbol = k
            break

    if not symbol:
        return

    # 选 token
    token_id = MARKETS[symbol]["YES"] if signal == "BUY" else MARKETS[symbol]["NO"]

    # 最新价格
    price = state["last_price"]

    logging.info(f"🎯 {symbol} | 信号: {signal} | 强度: {strength} | 价格: {price}")

    # 下单
    execute_trade(symbol, token_id, signal, price, strength)

    # 冷却
    cooldown[market] = True
    await asyncio.sleep(COOLDOWN_TIME)
    cooldown.pop(market, None)


# ===============================
# WebSocket 主循环
# ===============================
async def main():
    logging.info("🚀 V30 实时交易系统启动")

    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({
            "type": "subscribe",
            "channels": ["trades", "orderbook"],
            "tokens": WATCH_TOKENS
        }))

        logging.info("📡 WebSocket 已连接")

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)

                market = data.get("market")
                token_id = data.get("token_id")

                if not market or not token_id:
                    continue

                # 初始化市场
                if market not in markets:
                    markets[market] = {
                        "trades": [],
                        "orderbook": {"bids": [], "asks": []},
                        "last_price": None,
                        "last_token": None
                    }

                state = markets[market]

                # ===== trades =====
                if data.get("type") == "trade":
                    state["trades"].append(data)

                    if len(state["trades"]) > 50:
                        state["trades"].pop(0)

                    state["last_price"] = data.get("price")
                    state["last_token"] = token_id

                # ===== orderbook =====
                elif data.get("type") == "orderbook":
                    state["orderbook"] = data

                # ===== 触发策略 =====
                await handle_market(market, state)

            except Exception as e:
                logging.error(f"❌ WS错误: {e}")
                await asyncio.sleep(3)


# ===============================
# 启动
# ===============================
if __name__ == "__main__":
    asyncio.run(main())
