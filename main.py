import asyncio
import json
import websockets
import time
import hmac
import hashlib
import requests
import os

# ================== 配置 ==================
POLY_ADDRESS = os.getenv("POLY_ADDRESS")       # 钱包地址
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")    # 私钥
MARKET_ID = "BTC-5min"                         # 示例市场
USDC_AMOUNT = 10                               # 总资金池
ORDER_STEP = 0.01                               # 阶梯价格间距
ORDER_SIZE = 1                                  # 单笔订单大小
FEE_RATE_BPS = 156                              # 手续费bps
WS_URL = "wss://clob.polymarket.com/ws"
BALANCE_INTERVAL = 300                           # 每 5 分钟汇报余额 (秒)

# ================== 获取余额 ==================
def get_balance():
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

# ================== 阶梯挂单逻辑 ==================
async def market_maker(bid_price, ask_price):
    buy_prices = [round(bid_price - ORDER_STEP * i, 2) for i in range(3)]
    sell_prices = [round(ask_price + ORDER_STEP * i, 2) for i in range(3)]

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
    response = requests.post(url, headers=headers, json=order_payload)
    print(f"{side.upper()} {price}x{size} -> {response.status_code}")

# ================== WebSocket 数据订阅 ==================
async def subscribe_market():
    async with websockets.connect(WS_URL) as ws:
        subscribe_msg = {"type": "subscribe", "marketId": MARKET_ID}
        await ws.send(json.dumps(subscribe_msg))

        async for message in ws:
            data = json.loads(message)
            if "bestBid" in data and "bestAsk" in data:
                bid = data["bestBid"]
                ask = data["bestAsk"]
                await market_maker(bid, ask)

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
