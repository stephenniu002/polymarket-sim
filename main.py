import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer

# ================= 1. 基础配置与 Telegram =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 变量对齐
PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder") or os.getenv("POLY_ADDRESS")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(text):
    """发送电报通知"""
    if not TG_TOKEN or not TG_CHAT_ID:
        logging.warning("⚠️ 未配置 TG_TOKEN 或 TELEGRAM_CHAT_ID，跳过发送")
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": f"🦞 龙虾系统报告:\n{text}", "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"❌ Telegram 发送失败: {e}")

logging.info("🚀 polymarket-sim: V17.3 (电报联动版) 启动")

# ================= 2. 客户端初始化 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)
client.signer = Signer(PK, chain_id=137)

# ================= 3. 核心功能函数 =================

def init_engine():
    try:
        logging.info(f"🔗 正在链接地址: {FUNDER[:10]}...")
        creds = client.create_or_derive_api_creds()
        if creds:
            client.set_api_creds(creds)
            client.api_key = creds.api_key
            client.api_secret = creds.api_secret
            client.api_passphrase = creds.api_passphrase
        try:
            client.update_balance_allowance()
        except: pass
        
        send_telegram(f"✅ 系统已上线\n地址: <code>{FUNDER[:10]}...</code>")
        return True
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return False

async def get_safe_balance():
    try:
        res = await asyncio.to_thread(client.get_balance)
        return float(res.get("balance", 0))
    except:
        return 0.0

def fetch_top_markets():
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 5, "active": "true", "closed": "false"}
        res = requests.get(url, params=params, timeout=10).json()
        return [{"name": m["question"], "token": m["tokens"][0]["token_id"]} for m in res if m.get("tokens")]
    except: return []

# ================= 4. 交易逻辑 =================

async def trade_step():
    balance = await get_safe_balance()
    logging.info(f"💰 当前余额: {balance} USDC")
    
    if balance < 0.1:
        logging.warning("⚠️ 余额不足或未识别到 Native USDC")
        return

    markets = fetch_top_markets()
    if not markets: return

    target = markets[0]
    try:
        ob = client.get_order_book(target['token'])
        if not ob.get("bids") or not ob.get("asks"): return
        mid_price = round((float(ob["bids"][0][0]) + float(ob["asks"][0][0])) / 2, 3)
        
        # 尝试下单 0.1 USDC 验证
        order = OrderArgs(price=mid_price, size=0.1, side="buy", token_id=str(target['token']))
        
        def _send():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)
            
        res = await asyncio.to_thread(_send)
        
        if res and res.get("success"):
            msg = f"🎯 【下单成功】\n市场: {target['name']}\n价格: {mid_price}\n余额: {balance} USDC"
            logging.info(msg)
            send_telegram(msg)
        else:
            logging.warning(f"❌ 下单失败: {res}")
                
    except Exception as e:
        logging.error(f"💥 异常: {e}")

# ================= 5. 入口 =================

async def main():
    if not init_engine(): return
    while True:
        try:
            await trade_step()
            await asyncio.sleep(300) 
        except Exception as e:
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
