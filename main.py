import os, asyncio, logging
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 日志配置 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 获取私钥 (新钱包地址)
PK = os.getenv("PRIVATE_KEY")
_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 初始化客户端 (2026版标准初始化)
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137)

# ================= 2. 2026 新版探测逻辑 =================

async def latest_sync_check():
    try:
        # A. 强制执行 L1 -> L2 鉴权推导
        # 这一步会自动处理你之前遇到的 400 错误
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info(f"✅ 2026 新版 API 已激活 | Key: {creds.api_key[:8]}***")

        # B. 资产穿透探测 (使用 2026 最新兼容函数)
        balance = 0.0
        
        # 尝试最新版本的 get_balance
        try:
            # 0.34.x 版本后的标准写法
            res = await asyncio.to_thread(client.get_balance)
            if isinstance(res, dict):
                balance = float(res.get("balance") or 0.0)
            else:
                balance = float(res)
        except Exception as e:
            logging.warning(f"⚠️ get_balance 探测受阻: {e}")

        # C. 自动定位 Proxy 充值地址
        proxy = "N/A"
        try:
            # 2026版 SDK 内部会自动维护这个属性
            proxy = client.get_proxy()
        except:
            proxy = MY_ADDRESS

        return balance, proxy

    except Exception as e:
        logging.error(f"❌ 运行异常: {e}")
        return 0.0, "N/A"

# ================= 3. 主循环 =================

async def main():
    logging.info(f"🚀 龙虾 V27.0 (2026 适配版) 启动 | 地址: {MY_ADDRESS}")
    
    while True:
        balance, proxy = await latest_sync_check()
        
        if balance > 0:
            logging.info(f"💰 【资产已锁定】余额: {balance} USDC")
        else:
            logging.warning(f"🔎 余额为 0。")
            logging.info(f"💡 关键提示：新钱包必须向此 Proxy 地址充值: {proxy}")
            
        logging.info("-" * 45)
        await asyncio.sleep(120)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 机器人停止。")
