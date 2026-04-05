import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 基础配置 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
# 自动推导钱包地址，确保 Funder 永远正确
_acc = Account.from_key(PK)
FUNDER = _acc.address

# 初始化客户端
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)

# ================= 2. 核心穿透逻辑 (彻底重写) =================

async def get_balance_final_boss():
    """
    不再依赖 get_proxy_address，直接通过多种 API 路径强制抓取余额
    """
    try:
        # 解决日志中的 400 Bad Request：先衍生，再设置
        logging.info("🔐 正在重新握手 API 权限...")
        try:
            # 某些版本 SDK 需要先执行 derive
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)
        except Exception as cred_err:
            logging.warning(f"⚠️ 凭据同步提示: {cred_err}")

        # 核心：绕过所有可能报错的 Proxy 方法，直接探测可用接口
        res = None
        # 按照新版 SDK 成功率排序
        check_methods = ['get_collateral_balance', 'get_balance', 'get_user_allowance']
        
        for m_name in check_methods:
            if hasattr(client, m_name):
                try:
                    logging.info(f"📡 尝试接口: {m_name}")
                    res = await asyncio.to_thread(getattr(client, m_name))
                    if res: break
                except: continue

        # 日志诊断：这是找钱的关键
        logging.info(f"📊 [底层诊断] 原始响应原文: {res}")
        
        if not res:
            return 0.0

        # 智能解析
        if isinstance(res, dict):
            # 自动提取任何看起来像余额的数字
            for key in ['balance', 'amount', 'collateral', 'available']:
                if key in res:
                    return float(res[key])
        return float(res) if isinstance(res, (int, float, str)) else 0.0

    except Exception as e:
        logging.error(f"❌ 穿透抓取崩溃: {e}")
        return 0.0

# ================= 3. 执行循环 =================

async def main():
    logging.info(f"🚀 龙虾 V18.0 穿透部署成功 | 目标钱包: {FUNDER}")
    
    while True:
        balance = await get_balance_final_boss()
        
        if balance > 0:
            logging.info(f"✅ 【锁定余额！】成功抓取到: {balance} USDC")
            # 钱一旦找到，此处可以触发你的下单逻辑
        else:
            logging.warning("🔎 余额仍为 0。请检查网页端 'Portfolio' -> 'Deposit' 是否有待确认的交易。")
            
        # 延长检查间隔至 3 分钟，防止 API 频率限制导致的 400 错误
        await asyncio.sleep(180)

if __name__ == "__main__":
    asyncio.run(main())
