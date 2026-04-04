import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
FUNDER = "0xD228e7d8A608a656d4DF53F5cEBAEFeF9402a07b" # 强制锁定你的主地址

client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)

async def find_real_money():
    """
    穿透逻辑：获取 Proxy 地址并查询其余额
    """
    try:
        # 1. 必须先获取 API 凭据才能查询 Proxy
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        
        # 2. 获取你的 Proxy 地址 (这是存那 25U 的真正地方)
        proxy_res = await asyncio.to_thread(client.get_proxy_address)
        proxy_address = proxy_res if isinstance(proxy_res, str) else proxy_res.get("proxyAddress")
        logging.info(f"🔍 找到你的交易代理地址 (Proxy): {proxy_address}")

        # 3. 核心：查询代理地址在 Polymarket 协议里的余额
        # 注意：这里调用的是 get_collateral_balance，它是查协议余额的唯一正确方式
        balance_res = await asyncio.to_thread(client.get_collateral_balance)
        
        logging.info(f"📊 协议层原始响应: {balance_res}")
        
        balance = float(balance_res.get("balance") or balance_res.get("amount") or 0.0)
        return balance, proxy_address
    except Exception as e:
        logging.error(f"❌ 穿透查询失败: {e}")
        return 0.0, None

async def main():
    logging.info("🚀 启动资产穿透扫描...")
    while True:
        balance, proxy = await find_real_money()
        logging.info(f"💰 最终确认余额: {balance} USDC")
        
        if balance > 5.0:
            logging.info("✅ 钱找到了！准备执行智能下单...")
            # 这里可以放你之前的下单逻辑
        else:
            logging.warning("⚠️ 协议层依然显示 0，请确认网页端是否完成了 Deposit 确认")
            
        await asyncio.sleep(60) # 每分钟查一次

if __name__ == "__main__":
    asyncio.run(main())
