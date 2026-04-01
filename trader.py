from web3 import Web3
from eth_account import Account
import config

w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
account = Account.from_key(config.PRIVATE_KEY)

def sign_and_send_order(market_id, side, amount):
    # ⚠️ Polymarket真实需要 EIP-712 签名
    print(f"📥 下单: {market_id} {side} {amount}")

    # TODO: 接 CLOB API
    return True
