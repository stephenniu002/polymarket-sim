import sys
import subprocess
import os
import asyncio
import logging

# ================= 1. 自动修复环境依赖 (防止 Railway 缓存崩溃) =================
def repair_env():
    try:
        from web3 import Web3
        import websockets.legacy  # 检查特定报错模块
    except (ImportError, ModuleNotFoundError):
        print("🔧 正在修复依赖环境 (安装 Web3 v6.11 + Websockets v11)...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "web3==6.11.1", "websockets==11.0.3", "py-clob-client==0.34.6", "eth-account"
        ])
        print("✅ 环境修复完成，重新启动程序...")
        os.execv(sys.executable, ['python'] + sys.argv)

repair_env()

# --- 环境修复后正式导入 ---
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from eth_account import Account
from web3 import Web3

# ================= 2. 配置与日志 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 读取环境变量
PK = os.getenv("PRIVATE_KEY")
_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 核心合约与网络 (针对 Polygon USDC.e)
RPC_URL = "https://polygon-rpc.com"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# 初始化 Polymarket 客户端
client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("POLY_API_KEY"),
    secret=os.getenv("POLY_SECRET"),
    passphrase=os.getenv("POLY_PASSPHRASE"),
    chain_id=POLYGON,
    private_key=PK
)

# ================= 3. 资产与 API 探测逻辑 =================

async def lobster_sync_check():
    try:
        # A. API 激活 (如果已激活会报 400，
