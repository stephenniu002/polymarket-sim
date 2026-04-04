import os
import time
import logging
import requests
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# ===== 1. 变量与环境配置 =====
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
API_KEY = os.getenv("POLY_API_KEY")
SECRET = os.getenv("POLY_SECRET")
PASSPHRASE = os.getenv("POLY_PASSPHRASE")
ADDRESS = os.getenv("POLY_ADDRESS")  # 建议填 Proxy 地址，如果填主地址请确保已 Enable Trading

POLYGON_RPC = "https://polygon-rpc.com"
USDC_E_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]'

# 初始化官方 SDK 客户端 (用于签名下单)
try:
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=PRIVATE_KEY,
        chain_id=POLYGON,
        api_key=API_KEY,
        api_secret=SECRET,
        api_passphrase=PASSPHRASE
    )
except Exception as e:
    logging.error(f"❌ 交易客户端初始化失败: {e}")
    client = None

def get_balance():
    """双保险获取余额：协议账户 (CLOB) + 钱包直查 (Web3)"""
    if not ADDRESS: return 0.0

    # 路径 A: 查询 Polymarket 协议内余额 (这是能用来下单的钱)
    if client:
        try:
            # 获取结算资产余额 (USDC)
            resp = client.get_collateral_balance(ADDRESS)
            bal = resp.get("balance", 0)
            if float(bal) > 0:
                return round(float(bal), 2)
        except Exception as e:
            logging.debug(f"协议余额查询跳过: {e}")

    # 路径 B: Web3 直接查询钱包里的 USDC.e (用于确认钱是否在钱包但没进协议)
    try:
        w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
        if w3.is_connected():
            check_addr = Web3.to_checksum_address(ADDRESS)
            contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_CONTRACT), abi=ERC20_ABI)
            raw_balance = contract.functions.balanceOf(check_addr).call()
            # USDC.e 是 6 位精度
            web3_bal = round(float(raw_balance / 10**6), 2)
            if web3_bal > 0:
                logging.info(f"💡 钱包内检测到 {web3_bal} USDC.e (可能需要 Deposit 到协议)")
                return web3_bal
    except:
        pass
    
    return 0.0

def safe_order(token_id, price, size, side, retries=3):
    """带 EIP-712 签名的安全下单"""
    if not client:
        logging.error("❌ 交易客户端未就绪，无法下单")
        return False

    from py_clob_client.clob_types import OrderArgs
    
    for i in range(retries):
        try:
            logging.info(f"🏹 尝试下单: {side} {size} @ {price} (ID: {str(token_id)[:10]}...)")
            
            # 使用 SDK 提供的创建订单方法 (自动处理签名)
            resp = client.create_order(OrderArgs(
                price=float(price),
                size=float(size),
                side=side.upper(),
                token_id=str(token_id)
            ))
            
            if resp.get("success"):
                logging.info(f"✅ 下单成功! 订单ID: {resp.get('orderID')}")
                return True
            else:
                logging.warning(f"⚠️ 下单未成功 (第{i+1}次): {resp}")
        except Exception as e:
            logging.error(f"❌ 下单异常 (第{i+1}次): {e}")
        
        time.sleep(2)
    return False
