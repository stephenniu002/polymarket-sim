import requests

BASE = "https://clob.polymarket.com"

def get_market(keyword="Trump"):
    data = requests.get(f"{BASE}/markets").json()

    for m in data:
        if keyword.lower() in m["question"].lower():
            return m

    return None

def get_tokens(market):
    yes, no = None, None
    for t in market["tokens"]:
        if t["outcome"].lower() == "yes":
            yes = t["token_id"]
        else:
            no = t["token_id"]
    return yes, no
