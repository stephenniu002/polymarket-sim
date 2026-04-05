import os, asyncio, logging
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 环境配置 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 确保私钥存在
PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
if not PK:
    logging.error("❌ 环境变量中未找到私钥！请在 Railway 变量中设置 PRIVATE_KEY。")
    exit(1)

_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 初始化客户端
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137)

# ================= 2. 核心功能 =================

async def setup_and_check():
    """
    激活 API 权限并穿透探测代理钱包余额
    """
    try:
        # 激活权限
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info(f"✅ API 授权成功 | Key ID: {creds.api_key[:8]}***")

        # 获取专属代理地址
        proxy_addr = client.get_proxy_address()
        logging.info(f"🛡️ 你的【新充值地址】为: {proxy_addr}")

        # 探测余额
        res = await asyncio.to_thread(client.get_collateral_balance)
        
        balance = 0.0
        if isinstance(res, dict):
            balance = float(res.get("balance") or 0.0)
        elif isinstance(res, (str, float, int)):
            balance = float(res)
            
        return balance, proxy_addr

    except Exception as e:
        logging.error(f"❌ 运行异常: {e}")
        return 0.0, "N/A"

# ================= 3. 主循环 =================

async def main():
    logging.info(f"🚀 龙虾 V23.7 启动 | 当前地址: {MY_ADDRESS}")
    
    while True:
        balance, proxy = await setup_and_check()
        
        if balance > 0:
            logging.info(f"💰 【资产锁定成功】当前余额: {balance} USDC")
        else:
            logging.warning("🔎 余额仍为 0。")
            logging.info(f"💡 需向此地址转入 USDC (Polygon): {proxy}")
            
        logging.info("-" * 40)
        # 确保这里有右括号
        await asyncio.sleep(120)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 机器人已手动停止。")
