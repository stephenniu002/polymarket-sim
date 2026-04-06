import asyncio
import json
import websockets
import time
import hmac
import hashlib
import requests
import os

# ================== 配置 ==================
POLY_ADDRESS = os.getenv("POLY_ADDRESS")
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
MARKET_ID = "BTC-5min"
USDC_AMOUNT = 10
ORDER_STEP = 0.01
ORDER_SIZE = 1
FEE_RATE_BPS = 156
WS_URL = "wss://clob.polymarket.com/ws/"  # 注意末尾斜杠
BALANCE_INTERVAL = 300

# ================== 获取余额 ==================
def get_balance():
    try:
        url = f"https://clob.polymarket.com/api/v1/accounts/{POLY_ADDRESS}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            usdc_balance = float(data.get("USDC", 0))
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] USDC余额: {usdc_balance:.2f}")
            return usdc_balance
        else:
            print(f"获取余额失败: {response.status_code}, {response.text}")
            return 0
    except Exception as e:
        print(f"获取余额异常: {e}")
        return 0

# ================== 阶梯挂单 ==================
async def market_maker(bid_price, ask_price):
    buy_prices = [round(bid_price - ORDER_STEP * i, 4) for i in range(3)]
    sell_prices = [round(ask_price + ORDER_STEP * i, 4) for i in range(3)]

    for price in buy_prices:
        await place_order("buy", price, ORDER_SIZE)
    for price in sell_prices:
        await place_order("sell", price, ORDER_SIZE)

# ================== 下单函数 ==================
async def place_order(side, price, size):
    timestamp = int(time.time() * 1000)
    order_payload = {
        "marketId": MARKET_ID,
        "side": side,
        "price": price,
        "size": size,
        "feeRateBps": FEE_RATE_BPS,
        "timestamp": timestamp
    }
    message = f"{MARKET_ID}{side}{price}{size}{timestamp}".encode()
    signature = hmac.new(PRIVATE_KEY.encode(), message, hashlib.sha256).hexdigest()
    order_payload["signature"] = signature

    url = f"https://clob.polymarket.com/api/v1/orders"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {POLY_ADDRESS}"}

    try:
        response = requests.post(url, headers=headers, json=order_payload, timeout=5)
        print(f"{side.upper()} {price}x{size} -> {response.status_code}")
    except Exception as e:
        print(f"下单异常: {e}")

# ================== WebSocket 数据订阅 ==================
async def subscribe_market():
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                subscribe_msg = {"type": "subscribe", "marketId": MARKET_ID}
                await ws.send(json.dumps(subscribe_msg))
                print(f"✅ 已订阅 {MARKET_ID} 市场")

                async for message in ws:
                    data = json.loads(message)
                    if "bestBid" in data and "bestAsk" in data:
                        bid = data["bestBid"]
                        ask = data["bestAsk"]
                        await market_maker(bid, ask)

        except websockets.exceptions.ConnectionClosed as e:
            print(f"⚠️ WebSocket 断开，重连中: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️ WebSocket 异常: {e}")
            await asyncio.sleep(5)

# ================== 定时汇报余额 ==================
async def balance_reporter():
    while True:
        get_balance()
        await asyncio.sleep(BALANCE_INTERVAL)

# ================== 主循环 ==================
async def main():
    await asyncio.gather(
        subscribe_market(),
        balance_reporter()
    )

if __name__ == "__main__":
    asyncio.run(main())
