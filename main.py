import os
import time
import requests
import logging
from web3 import Web3

# ================= 配置区 =================
BASE = "https://clob.polymarket.com"
BUY_AMOUNT = 1.0        # 每次投入 1 USDC
INTERVAL = 300          # 每5分钟触发一次
POLY_RPC = os.getenv("POLY_RPC")
POLY_ADDRESS = os.getenv("POLY_ADDRESS")
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")

# Telegram
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# USDC 合约地址 (Polygon)
USDC_ADDRESS = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")

# 7 个币尾盘反转示例
MARKETS = {
    "BTC": {"YES": "token_id_yes_btc", "NO": "token_id_no_btc"},
    "ETH": {"YES": "token_id_yes_eth", "NO": "token_id_no_eth"},
    "SOL": {"YES": "token_id_yes_sol", "NO": "token_id_no_sol"},
    "ADA": {"YES": "token_id_yes_ada", "NO": "token_id_no_ada"},
    "BNB": {"YES": "token_id_yes_bnb", "NO": "token_id_no_bnb"},
    "DOT": {"YES": "token_id_yes_dot", "NO": "token_id_no_dot"},
    "XRP": {"YES": "token_id_yes_xrp", "NO": "token_id_no_xrp"},
}

# ================= 日志 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ================= Web3 初始化 =================
w3 = Web3(Web3.HTTPProvider(POLY_RPC))
usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=[
    {"constant": True,"inputs": [{"name": "_owner","type": "address"}],
     "name": "balanceOf","outputs": [{"name": "balance","type": "uint256"}],
     "type": "function"}
])

# ================= 获取余额 =================
def get_balance(address):
    try:
        balance = usdc_contract.functions.balanceOf(address).call()
        return round(balance / 1e6, 2)
    except:
        return 0.0

# ================= 获取市场最新价格 =================
def get_market_price(token_id):
    try:
        url = f"{BASE}/trades?token_id={token_id}&limit=1"
        res = requests.get(url, timeout=5).json()
        if res and "price" in res[0]:
            return float(res[0]["price"])
    except:
        pass
    return None

# ================= 下单模拟 =================
def execute_order(market, side, size):
    logging.info(f"[下单] {market} | {side} | {size} USDC")
    # TODO: 替换为实际 Polymarket 下单 API
    pass

# ================= Telegram =================
def send_telegram(msg):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": msg}
        try:
            requests.post(url, data=data, timeout=3)
        except:
            pass

# ================= 主循环 =================
def main():
    while True:
        balance = get_balance(POLY_ADDRESS)
        logging.info(f"💰 当前 USDC 余额: {balance} USDC")
        
        for market, tokens in MARKETS.items():
            # 获取最新价格
            yes_price = get_market_price(tokens["YES"])
            no_price = get_market_price(tokens["NO"])

            # 尾盘策略: 价格低于 0.01 就买
            if yes_price and yes_price <= 0.01:
                execute_order(market, "YES", BUY_AMOUNT)
            if no_price and no_price <= 0.01:
                execute_order(market, "NO", BUY_AMOUNT)

        # Telegram 汇报
        send_telegram(f"🕔 尾盘反转执行完毕 | 当前余额: {balance} USDC")

        # 等待 5 分钟
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
