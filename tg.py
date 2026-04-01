import requests
import config

def send(msg):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": config.CHAT_ID,
        "text": msg
    })
