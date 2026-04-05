import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer
from eth_account import Account

# ================= 1. 基础配置 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 交易参数设置
MIN_BET = 5.0        # 每次下单金额
MAX_BET_PRICE = 0.8  # 不买胜率超过 80% 的单子 (赔率太低)
MIN_BET_PRICE = 0.1  # 不买胜率低于 10% 的单子 (风险太大)

if PK:
    try:
        _acc = Account.from_key(PK)
        FUNDER = _acc.address
        logging.info(f"✅ 钱包地址识别成功: {FUNDER}")
    except:
        FUNDER = os.getenv("POLY_ADDRESS")
else:
    FUNDER = os.getenv("POLY_ADDRESS")

def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": f"🦞 龙虾系统报告:\n{text}", "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except: pass

# ================= 2. 客户端初始化 =================
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)
try:
    client.signer = Signer(PK, chain_id=137)
except: pass

# ================= 3. 核心功能函数 =================

async def get_universal_balance():
    """万能余额获取函数：自适应方法扫描"""
    res = None
    try:
        # 强制同步凭据，防止 400 错误
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)

        # 方法扫描逻辑
        for m_name in ['get_collateral_balance', 'get_balance', 'get_allowance']:
            if hasattr(client, m_name):
                res = await asyncio.to_thread(getattr(client, m_name))
                if res: break
        
        logging.info(f"📊 [调试] 余额原始响应: {res}")

        if isinstance(res, dict):
            val = res.get("balance") or res.get("amount") or res.get("collateral") or 0.0
            return float(val)
        return float(res) if isinstance(res, (int, float, str)) else 0.0
    except Exception as e:
        logging.error(f"❌ 余额解析失败: {e}")
        return 0.0

async def auto_market_hunter():
    """
    【智能下单模块】: 扫描热门市场并尝试下单
    """
    try:
        # 1. 抓取 Gamma API 上的热门市场
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 5, "active": "true", "closed": "false", "order_by": "volume24h", "order_direction": "desc"}
        resp = requests.get(url, params=params, timeout=10).json()
        
        for m in resp:
            title = m.get("question")
            token_id = m["tokens"][0]["token_id"] # 默认取第一个 Token (通常是 YES)
            
            # 2. 获取盘口价格
            ob = await asyncio.to_thread(client.get_order_book, token_id)
            if not ob.get("asks"): continue
            
            best_price = float(ob["asks"][0][0])
            
            # 3. 策略判断：价格在 0.1~0.8 之间则自动买入 5U
            if MIN_BET_PRICE <= best_price <= MAX_BET_PRICE:
                logging.info(f"🎯 发现机会: {title} | 价格: {best_price} | 尝试下单...")
                
                order_args = OrderArgs(price=best_price, size=MIN_BET, side="buy", token_id=token_id)
                
                def _place():
                    signed = client.create_order(order_args)
                    return client.post_order(signed, OrderType.GTC)
                
                res = await asyncio.to_thread(_place)
                if res.get("success"):
                    msg = f"✅ <b>自动下单成功!</b>\n市场: {title}\n成交价: {best_price}\n投入: {MIN_BET} USDC"
                    send_telegram(msg)
                    return True # 每次循环只下一单，稳健为主
        return False
    except Exception as e:
        logging.error(f"💥 猎手模块异常: {e}")
        return False

# ================= 4. 主程序入口 =================

async def main():
    send_telegram(f"🚀 龙虾 V17.9 启动\n监控地址: <code>{FUNDER}</code>")
    
    while True:
        try:
            balance = await get_universal_balance()
            logging.info(f"💰 当前实时余额: {balance} USDC")
            
            if balance >= MIN_BET:
                logging.info("✅ 余额充足，开始扫描市场...")
                await auto_market_hunter()
            else:
                logging.warning(f"⚠️ 余额 ({balance}) 不足 {MIN_BET}U，等待充值...")

            # 建议缩短检查时间，比如 5 分钟，提高抓单成功率
            await asyncio.sleep(300) 
        except Exception as e:
            logging.error(f"🔄 循环异常: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
