import asyncio
import json
import websockets
import time
import requests
import os
import logging

# ================= 配置 =================
WS_URL = "wss://clob.polymarket.com/ws/"
BASE = "https://clob.polymarket.com"

EDGE_THRESHOLD = 0.01       # 1% 才下单
ORDER_SIZE = 1              # 每次 1U
REPORT_INTERVAL = 300       # 5分钟

POLY_ADDRESS = os.getenv("POLY_ADDRESS")

# ===== 7个币（必须填真实 token_id）=====
MARKETS = {
    "BTC": {"YES": "yes_id_btc", "NO": "no_id_btc"},
    "ETH": {"YES": "yes_id_eth", "NO": "no_id_eth"},
    "BNB": {"YES": "yes_id_bnb", "NO": "no_id_bnb"},
    "DOGE": {"YES": "yes_id_doge", "NO": "no_id_doge"},
    "SOL": {"YES": "yes_id_sol", "NO": "no_id_sol"},
    "XRP": {"YES": "yes_id_xrp", "NO": "no_id_xrp"},
    "ADA": {"YES": "yes_id_ada", "NO": "no_id_ada"},
}

# ================= 日志 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ================= 余额 =================
def get_balance():
    try:
        url = f"{BASE}/api/v1/accounts/{POLY_ADDRESS}"
        res = requests.get(url, timeout=5).json()
        return float(res.get("USDC", 0))
    except:
        return 0

# ================= Edge 计算 =================
def calculate_edge(yes_price, no_price):
    if not yes_price or not no_price:
        return None
    
    total = yes_price + no_price

    # ❗过滤异常（你之前就是死在这里）
    if total > 1.2 or total < 0.8:
        return None

    return 1 - total

# ================= 下单 =================
def execute_order(market, side, price):
    logging.info(f"🚀 下单 {market} {side} @ {price} | {ORDER_SIZE}U")
    # TODO: 接入真实下单API
    pass

# ================= WS 主逻辑 =================
async def run():
    token_map = {}
    for m, t in MARKETS.items():
        token_map[t["YES"]] = (m, "YES")
        token_map[t["NO"]] = (m, "NO")

    last_report = time.time()

    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20) as ws:
                # 订阅 orderbook
                sub_msg = {
                    "type": "subscribe",
                    "topic": "book",
                    "market_ids": list(token_map.keys())
                }
                await ws.send(json.dumps(sub_msg))
                logging.info("✅ WebSocket 已连接")

                prices = {}

                async for msg in ws:
                    data = json.loads(msg)

                    # ===== 核心解析 =====
                    for token_id, info in data.items():
                        if token_id not in token_map:
                            continue

                        market, side = token_map[token_id]

                        best_ask = info.get("bestAsk")
                        best_bid = info.get("bestBid")

                        if best_ask:
                            prices.setdefault(market, {})[side] = best_ask

                    # ===== 计算套利 =====
                    for market in MARKETS.keys():
                        if market not in prices:
                            continue
                        if "YES" not in prices[market] or "NO" not in prices[market]:
                            continue

                        yes_price = prices[market]["YES"]
                        no_price  = prices[market]["NO"]

                        edge = calculate_edge(yes_price, no_price)

                        if edge is None:
                            continue

                        total = yes_price + no_price

                        logging.info(
                            f"🔍 [{market}] YES:{yes_price:.3f} NO:{no_price:.3f} "
                            f"Total:{total:.3f} Edge:{edge:.2%}"
                        )

                        # ===== 套利触发 =====
                        if edge > EDGE_THRESHOLD:
                            execute_order(market, "YES", yes_price)
                            execute_order(market, "NO", no_price)

                    # ===== 每5分钟汇报 =====
                    if time.time() - last_report > REPORT_INTERVAL:
                        balance = get_balance()
                        logging.info(f"💰 当前余额: {balance} USDC")
                        last_report = time.time()

        except Exception as e:
            logging.warning(f"⚠️ WS异常: {e}，5秒重连")
            await asyncio.sleep(5)

# ================= 启动 =================
if __name__ == "__main__":
    asyncio.run(run())
