import os
import time
import requests
from eth_account import Account
from web3 import Web3

# ===== 环境变量 =====
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
API_KEY = os.getenv("POLY_API_KEY")
SECRET = os.getenv("POLY_SECRET")
PASSPHRASE = os.getenv("POLY_PASSPHRASE")
ADDRESS = os.getenv("POLY_ADDRESS")

# Polygon 链上配置
POLYGON_RPC = "https://polygon-rpc.com"
USDC_E_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # Polygon上的USDC.e
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]'

# 初始化账户（验证私钥有效性）
try:
    if PRIVATE_KEY:
        acct = Account.from_key(PRIVATE_KEY)
except Exception as e:
    print(f"⚠️ 私钥配置错误: {e}")

# ===== 获取真实余额 (双保险版) =====
def get_balance():
    """双保险获取余额：优先 API（交易账户），备选链上查询（钱包内）"""
    if not ADDRESS:
        print("❌ 错误: POLY_ADDRESS 未设置")
        return 0.0

    # --- 尝试 A: Polymarket CLOB API (查询交易账户里的钱) ---
    try:
        # 使用 account 接口获取已充值的抵押品余额
        url = "https://clob.polymarket.com/account"
        headers = {
            "X-API-KEY": API_KEY,
            "X-PASSPHRASE": PASSPHRASE
        }
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            bal = data.get("collateral_balance") or data.get("balance")
            if bal and float(bal) > 0:
                return round(float(bal), 2)
    except Exception as e:
        # print(f"DEBUG: API余额查询尝试跳过: {e}")
        pass

    # --- 尝试 B: Web3 直接查询 (查询钱包里还没 Deposit 的钱) ---
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        if w3.is_connected():
            # 格式化地址以符合 Web3 要求
            check_addr = Web3.to_checksum_address(ADDRESS)
            contract_addr = Web3.to_checksum_address(USDC_E_CONTRACT)
            
            contract = w3.eth.contract(address=contract_addr, abi=ERC20_ABI)
            raw_balance = contract.functions.balanceOf(check_addr).call()
            
            # USDC.e 是 6 位小数
            on_chain_bal = raw_balance / 10**6
            if on_chain_bal > 0:
                return round(float(on_chain_bal), 2)
    except Exception as e:
        print(f"❌ 链上查询余额也失败了: {e}")
    
    return 0.0

# ===== 下单 =====
def place_order(token, price, size, side):
    """核心下单函数"""
    if not all([ADDRESS, API_KEY]):
        return {"error": "Missing credentials"}

    url = "https://clob.polymarket.com/orders"
    order = {
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
        res = requests.post(url, json=order, headers=headers, timeout=10)
        return res.json()
    except Exception as e:
        print(f"❌ 下单错误: {e}")
        return {"error": str(e)}

# ===== 安全下单 =====
def safe_order(token, price, size, side, retries=3):
    """带重试机制的下单，返回布尔值便于 main.py 统计"""
    for i in range(retries):
        res = place_order(token, price, size, side)
        # 只要没有 error 关键字，通常视为下单成功
        if res and "error" not in str(res).lower():
            return True
        time.sleep(2)

    print("❌ 下单最终失败")
    return False
