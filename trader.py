import os
import time
import logging
import requests
from web3 import Web3

# 变量读取 (Railway 环境变量)
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
API_KEY = os.getenv("POLY_API_KEY")
SECRET = os.getenv("POLY_SECRET")
PASSPHRASE = os.getenv("POLY_PASSPHRASE")
ADDRESS = os.getenv("POLY_ADDRESS")

# Polygon 链上配置 (USDC.e)
POLYGON_RPC = "https://polygon-rpc.com"
USDC_E_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
# 简化的 ERC20 ABI
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]'

def get_balance():
    """双保险获取余额：1. API (协议内) 2. Web3 (钱包直查)"""
    if not ADDRESS: 
        logging.error("🚨 缺少 POLY_ADDRESS 变量设置")
        return 0.0

    # 路径 A: Web3 直接查询 (最稳，解决你看到的 10.84 不一致问题)
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        if w3.is_connected():
            check_addr = Web3.to_checksum_address(ADDRESS)
            contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_CONTRACT), abi=ERC20_ABI)
            raw_balance = contract.functions.balanceOf(check_addr).call()
            web3_bal = round(float(raw_balance / 10**6), 2)
            if web3_bal > 0:
                return web3_bal
    except Exception as e:
        logging.debug(f"Web3 余额查询异常: {e}")

    # 路径 B: Polymarket CLOB API
    try:
        url = "https://clob.polymarket.com/account"
        headers = {"X-API-KEY": API_KEY, "X-PASSPHRASE": PASSPHRASE, "X-SECRET": SECRET}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            bal = data.get("collateral_balance") or data.get("balance")
            if bal: return round(float(bal), 2)
    except:
        pass
    
    return 0.0

def place_order(token, price, size, side):
    """底层下单 API"""
    if not all([ADDRESS, API_KEY, PRIVATE_KEY]): 
        return {"error": "实盘凭证配置不全"}
        
    url = "https://clob.polymarket.com/orders"
    # 注意：实盘下单这里通常需要对订单哈希进行 EIP-712 签名
    # 这里保留你的逻辑，但建议确保 API KEY 拥有 Proxy 授权
    payload = {
        "token_id": str(token),
        "price": float(price),
        "size": float(size),
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
        logging.info(f"🏹 尝试下单: {side} {size} @ {price}")
        res = place_order(token, price, size, side)
        
        # 成功判定逻辑
        res_str = str(res).lower()
        if "success" in res_str or "order_id" in res_str:
            logging.info(f"✅ 下单成功: {side} {size} @ {price}")
            return True
        else:
            logging.warning(f"⚠️ 下单反馈: {res}")
            
        time.sleep(2)
    return False
