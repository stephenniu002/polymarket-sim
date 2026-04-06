import os
import time
import requests
import logging
from web3 import Web3

# ================= 配置区 =================
BASE = "https://clob.polymarket.com"
MIN_ORDER_SIZE = 1.0       
MAX_ORDER_SIZE = 3.0       
EDGE_THRESHOLD = 0.006     
REPORT_INTERVAL = 300      

# 钱包和 RPC
POLY_RPC = os.getenv("POLY_RPC")  # Polygon RPC URL
POLY_ADDRESS = os.getenv("POLY_ADDRESS")
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")

# Telegram
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# USDC 合约地址 (Polygon)
USDC_ADDRESS = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174") 

# 市场示例
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
    # 简化 ABI 只用 balanceOf
    {
        "constant": True,
        "inputs": [{"name": "_owner","type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance","type": "uint256"}],
        "type": "function"
    }
])

# ================= 动态资金分配 =================
def calculate_dynamic_size(edge):
    min_edge = EDGE_THRESHOLD
    max_edge = 0.02
    if edge < min_edge:
        return MIN_ORDER_SIZE
    elif edge > max_edge:
        return MAX_ORDER_SIZE
    else:
        size = MIN_ORDER_SIZE + (edge - min_edge) / (max_edge - min_edge) * (MAX_ORDER_SIZE - MIN_ORDER_SIZE)
        return round(size, 2)

# ================= Telegram =================
def send_telegram(msg):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": msg}
        try:
            requests.post(url, data=data, timeout=3)
        except:
            pass

# ================= 获取余额 =================
def get_balance(address):
    try:
        balance = usdc_contract.functions.balanceOf(address).call()
        return round(balance / 1e6, 2)  # USDC 6 位小数
    except:
        return 0.0

# ================= 获取市场价格 =================
def get_market_price(token_id):
    try:
        url = f"{BASE}/trades?token_id={token_id}&limit=1"
        res = requests.get(url, timeout=5).json()
        if res and "price" in res[0]:
            return float(res[0]["price"])
    except:
        pass
    return None

# ================= 计算 Edge =================
def calculate_edge(yes_price, no_price):
    if yes_price is None or no_price is None:
        return 0
    return 1 - (yes_price + no_price)

# ================= 下单模拟 =================
def execute_order(market, side, size):
    logging.info(f"[下单] {market} | {side} | {size} USDC")
    # TODO: 调用实际 Polymarket 下单 API
    pass

# ================= 主循环 =================
def main():
    last_report = time.time()
    while True:
        balance = get_balance(POLY_ADDRESS)
        logging.info(f"💰 当前 USDC 余额: {balance} USDC")

        total_edge_count = 0
        for market, tokens in MARKETS.items():
            yes_price = get_market_price(tokens["YES"])
            no_price = get_market_price(tokens["NO"])
            edge = calculate_edge(yes_price, no_price)

            if edge >= EDGE_THRESHOLD:
                size = calculate_dynamic_size(edge)
                execute_order(market, "YES", size)
                execute_order(market, "NO", size)
                total_edge_count += 1

        if time.time() - last_report > REPORT_INTERVAL:
            send_telegram(f"💹 执行 {total_edge_count} 个市场套利订单 | 当前余额 {balance} USDC")
            last_report = time.time()

        time.sleep(5)

if __name__ == "__main__":
    main()
