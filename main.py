import os, asyncio, logging
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 基础日志与身份配置 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 从环境变量获取新钱包私钥
PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")

if not PK:
    logging.error("❌ 未检测到私钥！请在 Railway 的 Variables 中设置 PRIVATE_KEY。")
    exit(1)

# 解析新地址
_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 初始化 Polymarket 客户端
# 注意：我们让 SDK 自动推导 funder 和 proxy
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137)

# ================= 2. 核心功能：权限激活与扫描 =================

async def initialize_and_scan():
    """
    一键激活新钱包 API 权限并深度探测余额
    """
    try:
        # 1. 握手 API：为新钱包生成 L2 凭据
        # 运行此行时，如果网页端开着，可能会触发一次小狐狸签名
        logging.info("🔐 正在建立新地址的 API 握手...")
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info(f"✅ 权限已激活 | Key ID: {creds.api_key[:8]}***")

        # 2. 获取 L2 代理地址 (Proxy Address)
        # 所有的 USDC 必须转入这个地址才能在 Polymarket 交易
        proxy_addr = client.get_proxy_address()
        logging.info(f"🛡️ 你的 L2 代理钱包(Funder): {proxy_addr}")

        # 3. 探测余额
        logging.info("📡 正在同步链上资产数据...")
        res = await asyncio.to_thread(client.get_collateral_balance)
        
        balance = 0.0
        if isinstance(res, dict):
            balance = float(res.get("balance") or 0.0)
        elif isinstance(res, (str, float, int)):
            balance = float(res)

        return balance, proxy_addr

    except Exception as e:
        logging.error(f"⚠️ 初始化异常: {e}")
        return 0.0, "N/A"

# ================= 3. 监控主循环 =================

async def main():
    logging.info(f"🚀 龙虾 V23.0 启动 | 当前地址: {MY_ADDRESS}")
    
    while True:
        balance, proxy = await initialize_and_scan()
        
        if balance > 0:
            logging.info(f"💰 【资产锁定成功】余额: {balance} USDC")
            # 在此处可以接入你之前的下单逻辑 (e.g., auto_hunter)
        else:
            logging.warning("🔎 余额为 0。如果是新钱包，请确保已充值。")
            logging.info(f"💡 请向该地址转入 USDC (Polygon网络): {proxy}")
            
        logging.info("-------------------------------------------")
        await asyncio.sleep(18
