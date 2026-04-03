import os
import time
import requests
from eth_account import Account
from web3 import Web3

# ===== 环境变量读取 (强力清理版) =====
def get_env_safe(key):
    val = os.getenv(key)
    return val.strip() if val else None

PRIVATE_KEY = get_env_safe("POLY_PRIVATE_KEY")
API_KEY = get_env_safe("POLY_API_KEY")
SECRET = get_env_safe("POLY_SECRET")
PASSPHRASE = get_env_safe("POLY_PASSPHRASE")
ADDRESS = get_env_safe("POLY_ADDRESS")

# Polygon 链上配置 (USDC.e)
POLYGON_RPC = "https://polygon-rpc.com"
USDC_E_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]'

# 初始化账户
try:
    if PRIVATE_KEY:
        acct = Account.from_key(PRIVATE_KEY)
except Exception as e:
    print(f"⚠️ 私钥验证失败: {e}")

def get_balance():
    """双保险获取余额：优先 API（交易账户），备选链上查询（钱包内）"""
    if not ADDRESS:
        return 0.0

    # --- 尝试 A: Polymarket CLOB API ---
    try:
        url = "https://clob.polymarket.com/account"
        headers = {
            "X-API-KEY": API_KEY,
            "X-PASSPHRASE": PASSPHRASE,
            "X-SECRET": SECRET
        }
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            # 调试开关：若仍为0可取消下行注释查看原因
            # print(f"DEBUG API: {data}")
            bal = data.get("collateral_balance") or data.get("balance")
            if bal and float(bal) > 0:
                return round(float(bal), 2)
    except:
        pass

    # --- 尝试 B: Web3 直接查询 (查询钱包内 USDC.e) ---
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        if w3.is_connected():
            check_addr = Web3.to_checksum_address(ADDRESS)
            contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_CONTRACT), abi=ERC20_ABI)
            raw_balance = contract.functions.balanceOf(check_addr).call()
            on_chain_bal = raw_balance / 10**6
            return round(float(on_chain_bal), 2)
    except Exception as e:
        print(f"❌ 链上查询失败: {e}")
    
    return 0.0

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
        return {"error": str(e)}

def safe_order(token, price, size, side, retries=3):
    """带重试的下单接口"""
    for i in range(retries):
        res = place_order(token, price, size, side)
        if res and "error" not in str(res).lower():
            return True
        time.sleep(2)
    return False
