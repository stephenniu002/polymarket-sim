import asyncio
import os
import httpx

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": CHAT_ID,
            "text": "🚀 机器人正在运行（循环模式）"
        })

async def main():
    while True:
        await send()
        await asyncio.sleep(60)  # 每60秒发一次

asyncio.run(main())
