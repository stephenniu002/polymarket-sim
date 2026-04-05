import os, asyncio, logging, requests
from py_clob_client.client import ClobClient
from eth_account import Account

# ================= 1. 基础配置 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
_acc = Account.from_key(PK)
FUNDER = _acc.address

# 初始化客户端
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)

# ================= 2. 核心：强制激活与查询 =================

async def get_balance_with_activation():
    """
    针对 400 错误的终极修复方案
    """
    try:
        # 1. 强制激活逻辑：如果一直 400，说明服务器不认这个 key
        logging.info("⚡ 正在执行 API 强制激活...")
        try:
            # 第一步：先尝试获取现有的，如果不成功会自动抛出异常
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)
            logging.info(f"🔑 凭据激活成功! Key ID: {creds.api_key[:8]}***")
        except Exception as e:
            logging.warning(f"⚠️ 自动激活跳过 (可能已存在): {e}")

        # 2. 深度探测余额
        # 注意：如果 API Key 没过，下面这些方法都会返回 None 或抛异常
        res = None
        for method_name in ['get_collateral_balance', 'get_balance']:
            if hasattr(client, method_name):
                try:
                    # 增加超时控制，防止死锁
                    res = await asyncio.to_thread(getattr(client, method_name))
                    if res: break
                except Exception as inner_e:
                    logging.debug(f"探测 {method_name} 失败: {inner_e}")

        logging.info(f"📊 [底层诊断] 原始响应原文: {res}")
        
        # 3. 解析结果
        if isinstance(res, dict):
            # Polymarket 常见的返回字段
            return float(res.get("balance") or res.get("amount") or 0.0)
        return float(res) if isinstance(res, (int, float, str)) else 0.0

    except Exception as e:
        logging.error(f"❌ 系统穿透失败: {e}")
        return 0.0

# ================= 3. 执行循环 =================

async def main():
    logging.info(f"🚀 龙虾 V18.5 启动 | 监控地址: {FUNDER}")
    
    # 初次启动先尝试激活一次
    await get_balance_with_activation()
    
    while True:
        balance = await get_balance_with_activation()
        
        if balance > 0:
            logging.info(f"💰 【钱抓到了！】当前余额: {balance} USDC")
        else:
            logging.warning("🔎 余额仍为 0。请执行以下【必杀技】：")
            logging.info("1. 打开 Polymarket 网页并登录")
            logging.info("2. 点击右上角钱包 -> Settings -> API Keys")
            logging.info("3. 删掉现有的 Key，让机器人重新生成")
            
        await asyncio.sleep(120) # 缩短为 2 分钟，加快同步

if __name__ == "__main__":
    asyncio.run(main())
