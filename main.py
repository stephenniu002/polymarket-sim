import asyncio
import os
import httpx

TOKEN = os.getenv("8526469896:AAF7oU1hGK3TjEa0Z3KDnwMy7QYqho45MhY")
CHAT_ID = os.getenv("5739995837")

async def send():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": CHAT_ID,
            "text": "🚀 机器人部署成功！"
        })

asyncio.run(send())
