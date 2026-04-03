import time
import requests
from eth_account import Account
from eth_account.messages import encode_structured_data
from config import PRIVATE_KEY, PUBLIC_ADDRESS, CLOB_REST

acct = Account.from_key(PRIVATE_KEY)

def sign_order(order):
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
            ],
            "Order": [
                {"name": "token_id", "type": "uint256"},
                {"name": "price", "type": "float"},
                {"name": "size", "type": "float"},
                {"name": "side", "type": "string"},
                {"name": "timestamp", "type": "uint256"},
            ]
        },
        "primaryType": "Order",
        "domain": {"name": "Polymarket"},
        "message": order
    }

    msg = encode_structured_data(typed_data)
    signed = acct.sign_message(msg)
    return signed.signature.hex()

def place_order(token_id, price, size, side):
    order = {
        "token_id": int(token_id),
        "price": price,
        "size": size,
        "side": side,
        "timestamp": int(time.time())
    }

    sig = sign_order(order)

    headers = {
        "Authorization": sig,
        "X-Address": PUBLIC_ADDRESS
    }

    return requests.post(f"{CLOB_REST}/orders", json=order, headers=headers).json()
