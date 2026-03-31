import asyncio
import json
import websockets
import os
import httpx

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BINANCE_WS = "wss://stream.binance.com:9443/ws/ethusdt@trade"

prices = []

BET = 10
MULTIPLIER = 100

trades = 0
wins = 0
balance = 0

async def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg
        })

def check_reversal():
    if len(prices) < 300:
        return False

    window = prices[-300:]
    last_60 = prices[-60:]

    low = min(window)
    current = prices[-1]

    # 是否接近极限低点
    distance = (current - low) / low

    # 是否出现反弹
    rebound = (max(last_60) - low) / low

    if distance < 0.002 and rebound > 0.005:
        return True

    return False

async def main():
    global trades, wins, balance

    async with websockets.connect(BINANCE_WS) as ws:
        print("🟢 已连接 Binance")

        last_report = asyncio.get_event_loop().time()

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            price = float(data["p"])
            prices.append(price)

            if len(prices) > 600:
                prices.pop(0)

            # 触发策略
            if check_reversal():
                trades += 1

                # 用真实后60秒判断胜负（关键）
