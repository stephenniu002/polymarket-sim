import os, asyncio, logging
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 配置 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 初始化客户端
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137)

# ================= 2. 核心：修正后的探测逻辑 =================

async def setup_and_check():
    try:
        # 1. 权限激活
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info(f"✅ API 授权成功 | Key ID: {creds.api_key[:8]}***")

        # 2. 获取 Proxy 地址 (修正函数名兼容性)
        proxy_addr = "N/A"
        try:
            # 尝试最新 SDK 路径
            proxy_addr = client.get_proxy() 
        except AttributeError:
            try:
                # 尝试备选路径
                res = client.get_profile()
                proxy_addr = res.get("proxyAddress") or res.get("proxy_address")
            except:
                # 最后的保底：如果实在拿不到，通常就是你的主地址（EOA）
                proxy_addr = MY_ADDRESS

        logging.info(f"🛡️ 你的【资产充值地址】为: {proxy_addr}")

        # 3. 探测余额
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
    logging.info(f"🚀 龙虾 V23.8 (属性修复版) 启动 | 当前地址: {MY_ADDRESS}")
    
    while True:
        balance, proxy = await setup_and_check()
        
        if balance > 0:
            logging.info(f"💰 【资产锁定成功】当前余额: {balance} USDC")
        else:
            logging.warning("🔎 余额仍为 0。")
            logging.info(f"💡 需向此地址转入 USDC (Polygon): {proxy}")
            
        logging.info("-" * 40)
        await asyncio.sleep(120)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 机器人停止。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 机器人已手动停止。")
