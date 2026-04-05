import os
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("POLY_API_KEY"),
    secret=os.getenv("POLY_SECRET"),
    passphrase=os.getenv("POLY_PASSPHRASE"),
    chain_id=POLYGON,
    private_key=os.getenv("PRIVATE_KEY")
)

BASE_SIZE = float(os.getenv("ORDER_SIZE", 2))


def calc_size(strength):
    return BASE_SIZE * (1 + strength)


def execute_trade(market, token_id, side, price, strength):
    size = calc_size(strength)

    order = client.create_order(
        token_id=token_id,
        side="BUY" if side == "BUY" else "SELL",
        price=price,
        size=size
    )

    signed = client.sign_order(order)
    res = client.post_order(signed)

    print(f"📤 {market} | {side} | size={size} | {res}")
