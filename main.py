import os, asyncio, logging
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 变量对齐配置 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 100% 对齐截图中的变量名
PK = os.getenv("PRIVATE_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ORDER_SIZE = os.getenv("ORDER_SIZE", "5") # 默认 5

if not PK:
    logging.error("❌ 错误：Railway 变量中未找到 PRIVATE_KEY！")
    exit(1)

# 解析当前运行地址
_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 初始化 Polymarket 客户端
# 强制不传旧的 POLY_API_KEY，让它根据 PRIVATE_KEY 重新推导
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137)

# ================= 2. 核心探测逻辑 =================

async def setup_and_check():
    """
    激活 API 权限并穿透探测代理钱包余额
    """
    try:
        # A. 激活 API 权限 (L1 -> L2 推导)
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info(f"✅ API 权限已对齐 | Key ID: {creds.api_key[:8]}***")

        # B. 获取专属 L2 代理充值地址 (兼容性处理)
        proxy_addr = "N/A"
        try:
            # 优先尝试推导代理地址
            proxy_addr = client.get_proxy()
        except:
            # 如果失败，通常是因为新钱包还没在链上初始化
            proxy_addr = MY_ADDRESS

        logging.info(f"🛡️ 你的【新充值地址】为: {proxy_addr}")

        # C. 探测 USDC 余额
        res = await asyncio.to_thread(client.get_collateral_balance)
        
        balance = 0.0
        if isinstance(res, dict):
            balance = float(res.get("balance") or 0.0)
        elif isinstance(res, (str, float, int)):
            balance = float(res)
            
        return balance, proxy_addr

    except Exception as e:
        logging.error(f"❌ 运行异常 (可能需要网页端签名): {e}")
        return 0.0, "N/A"

# ================= 3. 主循环 =================

async def main():
    logging.info(f"🚀 龙虾 V24.0 启动 | 当前地址: {MY_ADDRESS}")
    
    while True:
        balance, proxy = await setup_and_check()
        
        if balance > 0:
            logging.info(f"💰 【资产已锁定】余额: {balance} USDC")
            # 下一步：可以在这里恢复下单逻辑模块
        else:
            logging.warning("🔎 余额仍为 0。")
            logging.info(f"💡 需向此地址转入 USDC (Polygon网络): {proxy}")
            
        logging.info("-" * 40)
        # 确保括号完整闭合
        await asyncio.sleep(180)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 机器人已停止。")
