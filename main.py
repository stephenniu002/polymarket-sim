import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ==================== 1. 严格对齐 Railway 环境变量 ====================
# 签名：使用小狐狸私钥
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
# 出钱：使用 Polymarket 充值地址 (Funder)
FUNDER_ADDR = os.getenv("Funder") 
# 模式：从变量读取并强制转为整数
SIG_TYPE = int(os.getenv("signature_type", 2))

# API 凭证
POLY_KEY = os.getenv("POLY_API_KEY")
POLY_SECRET = os.getenv("POLY_SECRET")
POLY_PASS = os.getenv("POLY_PASSPHRASE")

# Telegram 配置 (匹配截图中的变量名)
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TG_BOT_TOKEN = os.getenv("TG_TOKEN")

# 下单设置
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
# ====================================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_tg_msg(text: str):
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": text}, timeout=10)
        except Exception as e:
            logging.error(f"Telegram 发送失败: {e}")

def get_polymarket_client():
    """初始化 ClobClient，确保签名与出金地址分离"""
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=SIGNER_PK,
        chain_id=POLYGON,
        signature_type=SIG_TYPE,
        funder=FUNDER_ADDR
    )
    client.set_api_creds(ApiCreds(
        api_key=POLY_KEY,
        api_secret=POLY_SECRET,
        api_passphrase=POLY_PASS
    ))
    return client

# 全局初始化客户端
pm_client = get_polymarket_client()

async def get_funder_balance():
    """查询 Funder 地址的 USDC 余额"""
    try:
        # 在代理模式下，SDK 会自动查询 funder 的 collateral 余额
        resp = await asyncio.to_thread(pm_client.get_collateral_balance)
        if resp and isinstance(resp, dict):
            balance = round(float(resp.get("balance", 0)), 2)
            logging.info(f"💰 [资金池检查] 余额: {balance} USDC")
            return balance
    except Exception as e:
        logging.error(f"❌ 余额查询异常: {e}")
    return 0.0

def fetch_active_token(asset_keyword: str):
    """动态抓取最热门市场的 Token ID"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": asset_keyword, "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        # 筛选出有 Token 的有效市场
        valid_markets = [m for m in resp if m.get("clobTokenIds")]
        if valid_markets:
            # 选取成交量最大的市场（确保流动性）
            best_m = max(valid_markets, key=lambda x: float(x.get("volume", 0)))
            # [0] 为 Yes/Above，[1] 为 No/Below
            return best_m["clobTokenIds"][0], best_m.get("question")
    except: pass
    return None, None

async def execute_trade_task(asset: str):
    """下单执行逻辑"""
    token_id, market_title = fetch_active_token(asset)
    if not token_id:
        logging.warning(f"⚠️ 未找到有效市场: {asset}")
        return False
    
    try:
        def _sync_trade():
            # 创建订单 -> 签名 -> 提交
            order_args = pm_client.create_order(
                price=0.5, # 示例限价 0.5
                size=ORDER_SIZE,
                side="buy",
                token_id=token_id
            )
            signed = pm_client.sign_order(order_args)
            return pm_client.place_order(signed)

        res = await asyncio.to_thread(_sync_trade)
        if res and res.get("success"):
            logging.info(f"✅ 成功下单: {market_title}")
            return True
        else:
            logging.error(f"❌ 下单未成交: {res}")
    except Exception as e:
        logging.error(f"❌ 交易执行异常 {asset}: {e}")
    return False

async def main_strategy_loop():
    logging.info("🚀 龙虾实盘 V6.2 适配版启动成功")
    send_tg_msg("🦞 龙虾实盘已上线！\n已精准适配 Railway 环境变量。")
    
    assets_to_watch = ["Bitcoin Price Above", "Ethereum Price Above", "Solana Price Above"]
    
    while True:
        try:
            current_balance = await get_funder_balance()
            
            if current_balance >= ORDER_SIZE:
                tasks = [execute_trade_task(a) for a in assets_to_watch]
                results = await asyncio.gather(*tasks)
                
                success_num = sum(1 for r in results if r)
                if success_num > 0:
                    send_tg_msg(f"🦞 轮询完成\n成功下单: {success_num} 个市场\n剩余余额: {current_balance} USDC")
            else:
                logging.warning(f"🛑 资金不足 (仅剩 {current_balance} USDC)，等待充值...")

        except Exception as e:
            logging.error(f"⚠️ 核心循环异常: {e}")
            
        await asyncio.sleep(600) # 每10分钟扫描一轮

if __name__ == "__main__":
    try:
        asyncio.run(main_strategy_loop())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("用户停止程序")
