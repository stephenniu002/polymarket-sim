import asyncio
import websockets
import json
import logging
import time

from trade import execute_trade
from strategy import generate_signal
from config import MARKETS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WS_URL = "wss://clob.polymarket.com/ws"

# ===============================
# Token
# ===============================
WATCH_TOKENS = []
for m in MARKETS.values():
    WATCH_TOKENS += [m["YES"], m["NO"]]

# ===============================
# 状态
# ===============================
markets = {}

# 冷却（时间戳）
cooldown = {}

COOLDOWN_TIME = 30  # 降低冷却

MAX_TRADES_PER_MIN = 3
trade_count = []

# ===============================
# 工具函数
# ===============================
def can_trade():
    now = time.time()

    # 清理 60 秒前的记录
    while trade_count and now - trade_count[0] > 60:
        trade_count.pop(0)

    return len(trade_count) < MAX_TRADES_PER_MIN


def record_trade():
    trade_count.append(time.time())


# ===============================
# 核心逻辑
# ===============================
async def handle_market(market, state):

    now = time.time()

    # 冷却检查（非阻塞）
    if market in cooldown and now - cooldown[market] < COOLDOWN_TIME:
        return

    # 信号
    signal = generate_signal(state)
    if not signal:
        return

    # 防止无价格
    if not state["last_price"]:
        return

    # symbol
    symbol = None
    for k, v in MARKETS.items():
        if state["last_token"] in [v["YES"], v["NO"]]:
            symbol = k
            break

    if not symbol:
        return

    # 频率限制
    if not can_trade():
        logging.warning("⛔ 交易频率过高，跳过")
        return

    # token
    token_id = MARKETS[symbol]["YES"] if signal == "BUY" else MARKETS[symbol]["NO"]

    price = float(state["last_price"])

    # 简单强度（改进）
    strength = min(len(state["trades"]) / 50, 1)

    logging.info(f"🎯 {symbol} | {signal} | 强度: {strength:.2f} | 价格: {price}")

    # 下单
    execute_trade(symbol, token_id, signal, price, strength)

    # 记录
    cooldown[market] = now
    record_trade()


# ===============================
# WS
# ===============================
async def main():
    logging.info("🚀 V30 Pro 启动")

    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({
            "type": "subscribe",
            "channels": ["trades", "orderbook"],
            "tokens": WATCH_TOKENS
        }))

        logging.info("📡 WS 已连接")

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)

                market = data.get("market")
                token_id = data.get("token_id")

                if not market or not token_id:
                    continue

                if market not in markets:
                    markets[market] = {
                        "trades": [],
                        "orderbook": {"bids": [], "asks": []},
                        "last_price": None,
                        "last_token": None
                    }

                state = markets[market]

                # trades
                if data.get("type") == "trade":
                    state["trades"].append(data)

                    if len(state["trades"]) > 50:
                        state["trades"].pop(0)

                    state["last_price"] = data.get("price")
                    state["last_token"] = token_id

                # orderbook
                elif data.get("type") == "orderbook":
                    state["orderbook"] = data

                await handle_market(market, state)

            except Exception as e:
                logging.error(f"❌ WS错误: {e}")
                await asyncio.sleep(2)


# ===============================
if __name__ == "__main__":
    asyncio.run(main())
