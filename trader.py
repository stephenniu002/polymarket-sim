import os
import time
import requests
from eth_account import Account
from web3 import Web3

# 变量读取
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
API_KEY = os.getenv("POLY_API_KEY")
SECRET = os.getenv("POLY_SECRET")
PASSPHRASE = os.getenv("POLY_PASSPHRASE")
ADDRESS = os.getenv("POLY_ADDRESS")

# Polygon 链上配置 (针对 USDC.e)
POLYGON_RPC = "https://polygon-rpc.com"
USDC_E_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]'

def get_balance():
    """双保险获取余额：API (交易账户) + Web3 (钱包直查)"""
    if not ADDRESS: return 0.0

    # 路径 A: Polymarket API
    try:
        url = "https://clob.polymarket.com/account"
        headers = {"X-API-KEY": API_KEY, "X-PASSPHRASE": PASSPHRASE, "X-SECRET": SECRET}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            bal = data.get("collateral_balance") or data.get("balance")
            if bal and float(bal) > 0:
                return round(float(bal), 2)
    except:
        pass

    # 路径 B: Web3 直接查询 (防止钱还没 Deposit)
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        if w3.is_connected():
            check_addr = Web3.to_checksum_address(ADDRESS)
            contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_CONTRACT), abi=ERC20_ABI)
            raw_balance = contract.functions.balanceOf(check_addr).call()
            return round(float(raw_balance / 10**6), 2)
    except:
        pass
    
    return 0.0

def place_order(token, price, size, side):
    """底层下单 API"""
    if not all([ADDRESS, API_KEY]): return {"error": "Credentials missing"}
    url = "https://clob.polymarket.com/orders"
    payload = {
        "token_id": str(token),
        "price": price,
        "size": size,
        "side": side.upper(),
        "timestamp": int(time.time())
    }
    headers = {
        "X-Address": ADDRESS,
        "X-API-KEY": API_KEY,
        "X-PASSPHRASE": PASSPHRASE,
        "X-SECRET": SECRET
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def safe_order(token, price, size, side, retries=3):
    """带重试的安全下单"""
    for i in range(retries):
        res = place_order(token, price, size, side)
        if res and "error" not in str(res).lower():
            logging.info(f"✅ 下单成功: {side} {size} @ {price}")
            return True
        time.sleep(2)
    return False
