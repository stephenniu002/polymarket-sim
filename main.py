import os, asyncio, logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from eth_account import Account
from web3 import Web3  # 需要在 requirements.txt 中添加 web3

# ================= 1. 配置与日志 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

PK = os.getenv("PRIVATE_KEY")
_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 标准 Polygon RPC 和 USDC 合约
RPC_URL = "https://polygon-rpc.com"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # USDC.e
ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# 初始化客户端 (2026版 API 认证)
client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("POLY_API_KEY"),
    secret=os.getenv("POLY_SECRET"),
    passphrase=os.getenv("POLY_PASSPHRASE"),
    chain_id=POLYGON,
    private_key=PK
)

# ================= 2. 2026 核心逻辑修改 =================

async def latest_sync_check():
    try:
        # A. 鉴权激活 (Polymarket 内部 API 激活)
        try:
            # 2026 版 SDK 推荐使用创建或推导
            client.derive_api_key()
            logging.info(f"✅ 2026 新版 API 认证完成")
        except Exception as e:
            # 如果已经激活过，这里可能会报 400，可以忽略
            pass

        # B. 资产穿透探测 (修复 AttributeError)
        # 针对 Polymarket Proxy 钱包，直接查询链上 USDC 余额是最稳妥的
        balance = 0.0
        # ！！！注意：这里填入你日志中显示的那个 Proxy 地址 ！！！
        PROXY_WALLET = "0xD228e7d8A608a656d4DF53F5cEBAEFeF9402a07b"
        
        try:
            usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=ERC20_ABI)
            raw_balance = usdc_contract.functions.balanceOf(Web3.to_checksum_address(PROXY_WALLET)).call()
            balance = raw_balance / 10**6 # USDC 是 6 位小数
        except Exception as e:
            logging.warning(f"⚠️ 链上余额探测受阻: {e}")

        return balance, PROXY_WALLET

    except Exception as e:
        logging.error(f"❌ 运行异常: {e}")
        return 0.0, "N/A"

# ================= 3. 主循环 =================

async def main():
    logging.info(f"🚀 龙虾 V27.0 (2026 修复版) 启动 | 地址: {MY_ADDRESS}")
    
    # 首次启动先尝试同步一次 API Key
    try:
        client.derive_api_key()
    except:
        pass

    while True:
        balance, proxy = await latest_sync_check()
        
        if balance > 0:
            logging.info(f"💰 【资产已锁定】余额: {balance} USDC")
            # 在这里可以触发下单逻辑: 
            # if balance >= float(os.getenv("ORDER_SIZE")):
            #     execute_trade()
        else:
            logging.warning(f"🔎 余额为 0。")
            logging.info(f"💡 关键提示：请向此 Proxy 地址充值 (Polygon 网络): {proxy}")
            
        logging.info("-" * 45)
        # 每 2 分钟轮询一次
        await asyncio.sleep(120)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 机器人停止。")
