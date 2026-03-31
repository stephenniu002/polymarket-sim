import httpx
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg
        })
