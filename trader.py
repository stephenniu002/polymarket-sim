import requests, time, json
from eth_account import Account
from eth_account.messages import encode_structured_data
import config

account = Account.from_key(config.PRIVATE_KEY)

def sign_order(market_id, token_id, price, size):
    order = {
        "salt": int(time.time()*1000),
        "maker": config.ADDRESS,
        "signer": config.ADDRESS,
        "taker": "0x0000000000000000000000000000000000000000",
        "tokenId": str(token_id),
        "makerAmount": str(size),
        "takerAmount": str(int(size * price)),
        "expiration": str(int(time.time()) + 300),
        "nonce": 0,
        "feeRateBps": 0,
        "side": 0  # buy
    }

    domain = {
        "name": "Clob",
        "version": "1",
        "chainId": 137
    }

    types = {
        "Order": [
            {"name":"salt","type":"uint256"},
            {"name":"maker","type":"address"},
            {"name":"signer","type":"address"},
            {"name":"taker","type":"address"},
            {"name":"tokenId","type":"uint256"},
            {"name":"makerAmount","type":"uint256"},
            {"name":"takerAmount","type":"uint256"},
            {"name":"expiration","type":"uint256"},
            {"name":"nonce","type":"uint256"},
            {"name":"feeRateBps","type":"uint256"},
            {"name":"side","type":"uint8"},
        ]
    }

    message = encode_structured_data({
        "domain": domain,
        "types": types,
        "primaryType": "Order",
        "message": order
    })

    signed = account.sign_message(message)
    return order, signed.signature.hex()

def place(order, sig):
    url = "https://clob.polymarket.com/order"
    headers = {"Content-Type":"application/json"}

    payload = {
        "order": order,
        "signature": sig
    }

    r = requests.post(url, json=payload, headers=headers)
    print("📥 下单返回:", r.text)
