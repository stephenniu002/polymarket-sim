import os, asyncio, logging
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 环境与日志 =================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

PK = os.getenv("PRIVATE_KEY")
if not PK:
    logging.error("❌ 错误：Railway 变量中未找到 PRIVATE_KEY！")
    exit(1)

_acc = Account.from_key(PK)
MY_ADDRESS = _acc.address

# 初始化客户端
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137)

# ================= 2. 强力探测逻辑 (解决 Attribute 报错) =================

async def setup_and_check():
    try:
        # A. 激活 API 权限
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        logging.info(f"✅ API 权限激活 | Key ID: {creds.api_key[:8]}***")

        # B. 探测 Proxy 地址
        proxy_addr = MY_ADDRESS
        for method in ['get_proxy', 'get_proxy_address', 'get_proxy_wallet']:
            if hasattr(client, method):
                try:
                    proxy_addr = getattr(client, method)()
                    break
                except: continue
        logging.info(f"🛡️ 充值/Funder地址: {proxy_addr}")

        # C. 【核心修复】多路径平衡探测
        balance = 0.0
        # 依次尝试新版和旧版的所有余额查询函数
        methods_to_try = ['get_balance', 'get_collateral_balance', 'get_user_balance']
        
        found_method = False
        for m_name in methods_to_try:
            if hasattr(client, m_name):
                try:
                    logging.info(f"📡 尝试调用方法: {m_name}")
                    res = await asyncio.to_thread(getattr(client, m_name))
                    if isinstance(res, dict):
                        balance = float(res.get("balance") or res.get("amount") or 0.0)
                    else:
                        balance = float(res or 0.0)
                    found_method = True
                    break
                except Exception as e:
                    logging.warning(f"⚠️ 方法 {m_name} 调用失败: {e}")
        
        if not found_method:
            logging.error("❌ SDK 版本异常：找不到任何可用的余额查询函数。")
            
        return balance, proxy_addr

    except Exception as e:
        logging.error(f"❌ 运行异常: {e}")
        return 0.0, "N/A"

# ================= 3. 主循环 =================

async def main():
    logging.info(f"🚀 龙虾 V25.1 (强力探测版) 启动 | 地址: {MY_ADDRESS}")
    
    while True:
        balance, proxy = await setup_and_check()
        
        if balance > 0:
            logging.info(f"💰 【资产已锁定】当前余额: {balance} USDC")
        else:
            logging.warning("🔎 余额仍为 0。")
            logging.info(f"💡 确认: 钱必须在 Proxy 钱包里，且 PRIVATE_KEY 正确。")
            
        logging.info("-" * 45)
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
        logging.info("🛑 机器人已停止。")
