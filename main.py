import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ==================== 1. 配置对齐 ====================
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")      # 小狐狸私钥
FUNDER_ADDR = os.getenv("Funder")             # Polymarket 充值地址 (有钱的那个)

# API 凭证
POLY_CREDS = ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
)

# 策略参数
ORDER_AMOUNT = 1.0        # 每笔固定投入 1 USDC
PRICE_LIMIT = 0.2         # 捡漏门槛：价格 <= 0.2
SCAN_INTERVAL = 60        # 扫描间隔 (秒)

ASSETS = ["Bitcoin Price Above", "Ethereum Price Above", "Solana Price Above", "XRP Price Above"]
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TG_TOKEN = os.getenv("TG_TOKEN")
# ====================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def send_tg(text: str):
    if TG_TOKEN and TG_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": text}, timeout=5)
        except: pass

# 初始化客户端 (签名者 + 出资者模式)
client = ClobClient(
    host="https://clob.polymarket.com", 
    key=SIGNER_PK, 
    chain_id=POLYGON, 
    signature_type=2, 
    funder=FUNDER_ADDR
)
client.set_api_creds(POLY_CREDS)

async def get_real_balance():
    """
    核心修复：强制查询 FUNDER_ADDR 在 Polymarket 协议内的可用余额
    """
    try:
        # SDK 0.34+ 建议用法：显式传入地址查询
        resp = await asyncio.to_thread(client.get_collateral_balance, FUNDER_ADDR)
        if resp and isinstance(resp, dict):
            # 有些版本返回 'balance', 有些返回 'collateral_balance'
            raw_val = resp.get("balance") or resp.get("collateral_balance") or 0
            return round(float(raw_val), 2)
    except Exception as e:
        logging.error(f"❌ 余额读取失败: {e}")
    return 0.0

def get_market_data(asset: str):
    """动态获取 Token ID"""
    try:
        res = requests.get("https://gamma-api.polymarket.com/markets", 
                           params={"active": "true", "search": asset, "limit": 3}).json()
        valid = [m for m in res if m.get("clobTokenIds")]
        if valid:
            m = max(valid, key=lambda x: float(x.get("volume", 0)))
            return m["clobTokenIds"][0], m.get("question")
    except: pass
    return None, None

async def trade_task(asset: str):
    """单路捡漏：查价 -> 计算份数 -> 下单"""
    token_id, title = get_market_data(asset)
    if not token_id: return False
    
    try:
        # 获取当前买入单价
        p_res = await asyncio.to_thread(client.get_price, token_id, side="BUY")
        price = float(p_res.get("price", 1.0))
        
        logging.info(f"🔍 {asset[:7]}.. 现价: {price}")

        if 0 < price <= PRICE_LIMIT:
            # 计算份数：投入 1 USDC / 单价 = 购买份数
            shares = round(ORDER_AMOUNT / price, 2)
            
            logging.info(f"🎯 触发捡漏! 价格 {price} <= {PRICE_LIMIT}. 计划买入 {shares} 份")
            
            def _place():
                args = client.create_order(price=price, size=shares, side="buy", token_id=token_id)
                signed = client.sign_order(args)
                return client.place_order(signed)

            res = await asyncio.to_thread(_place)
            if res and res.get("success"):
                logging.info(f"✅ 成功成交: {title}")
                return True
    except Exception as e:
        logging.warning(f"⚠️ {asset} 任务跳过: {e}")
    return False

async def main_loop():
    logging.info("🚀 龙虾实盘 V6.8 上线 (Funder 模式)")
    send_tg("🦞 龙虾实盘已启动！\n监控地址: " + FUNDER_ADDR[:10] + "...")
    
    while True:
        try:
            # 1. 检查 Polymarket 协议内的资金
            balance = await get_real_balance()
            logging.info(f"💰 Polymarket 可用资金: {balance} USDC")
            
            if balance >= ORDER_AMOUNT:
                # 2. 并发扫描 7 个币种
                tasks = [trade_task(a) for a in ASSETS]
                results = await asyncio.gather(*tasks)
                
                success_count = sum(1 for r in results if r)
                if success_count > 0:
                    new_bal = await get_real_balance()
                    send_tg(f"✅ 捡漏成功！\n成交笔数: {success_count}\n剩余资金: {new_bal} USDC")
            else:
                logging.warning(f"🛑 资金不足 ({balance} < {ORDER_AMOUNT})，请往 Funder 地址充值并 Deposit 到 Polymarket")
                
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main_loop())
