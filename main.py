import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer
from eth_account import Account

# ================= 1. 基础配置与策略参数 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 策略配置
MIN_BALANCE_RESERVE = 5.0  # 至少保留 5U 不动
SINGLE_ORDER_SIZE = 5.0    # 每次下单 5U
MAX_PRICE_THRESHOLD = 0.9  # 不买胜率超过 90% 的（赔率太低）
MIN_PRICE_THRESHOLD = 0.1  # 不买胜率低于 10% 的（风险太大）

if PK:
    try:
        _acc = Account.from_key(PK)
        FUNDER = _acc.address
        logging.info(f"✅ 智能体账户已激活: {FUNDER}")
    except:
        FUNDER = os.getenv("POLY_ADDRESS")
else:
    FUNDER = os.getenv("POLY_ADDRESS")

def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": f"🤖 龙虾智能体报告:\n{text}", "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except: pass

# ================= 2. 客户端兼容性初始化 =================
client = ClobClient(host="https://clob.polymarket.com", key=PK, chain_id=137, funder=FUNDER)
try:
    client.signer = Signer(PK, chain_id=137)
except: pass

async def get_balance_safe():
    """兼容多版本 SDK 的余额获取"""
    try:
        # 尝试所有可能的 SDK 方法名
        for method_name in ['get_collateral_balance', 'get_balance', 'get_allowance']:
            if hasattr(client, method_name):
                res = await asyncio.to_thread(getattr(client, method_name))
                if isinstance(res, dict):
                    return float(res.get("balance") or res.get("amount") or 0.0)
                elif isinstance(res, (int, float, str)):
                    return float(res)
        return 0.0
    except: return 0.0

# ================= 3. 智能决策与下单模块 =================

def fetch_active_markets():
    """获取当前最热门的交易市场"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        # 筛选条件：活跃、未关闭、有流动性
        params = {"limit": 10, "active": "true", "closed": "false", "order_by": "volume24h", "order_direction": "desc"}
        res = requests.get(url, params=params, timeout=10).json()
        return [{"name": m["question"], "token": m["tokens"][0]["token_id"]} for m in res if m.get("tokens")]
    except: return []

async def execute_smart_trade():
    """核心决策逻辑：扫描 -> 评估 -> 下单"""
    balance = await get_balance_safe()
    logging.info(f"💰 账户余额: {balance} USDC")

    if balance < (MIN_BALANCE_RESERVE + SINGLE_ORDER_SIZE):
        logging.warning("⚠️ 余额不足以执行下一次智能下单")
        return

    markets = fetch_active_markets()
    if not markets: return

    for market in markets:
        try:
            # 1. 获取盘口详情
            ob = await asyncio.to_thread(client.get_order_book, market['token'])
            if not ob.get("asks"): continue
            
            current_price = float(ob["asks"][0][0]) # 获取当前买入价格
            
            # 2. 智能评估：价格是否在预设范围内？
            if MIN_PRICE_THRESHOLD <= current_price <= MAX_PRICE_THRESHOLD:
                msg = f"🔎 发现机会!\n市场: {market['name']}\n当前价格: {current_price}\n正在尝试自动下单 {SINGLE_ORDER_SIZE}U..."
                logging.info(msg)
                
                # 3. 执行下单
                order = OrderArgs(price=current_price, size=SINGLE_ORDER_SIZE, side="buy", token_id=str(market['token']))
                
                def _post():
                    signed = client.create_order(order)
                    return client.post_order(signed, OrderType.GTC)
                
                res = await asyncio.to_thread(_post)
                
                if res and res.get("success"):
                    success_msg = f"🎯 <b>【自动下单成功】</b>\n市场: {market['name']}\n成交价: {current_price}\n投入: {SINGLE_ORDER_SIZE} USDC"
                    send_telegram(success_msg)
                    logging.info(success_msg)
                    return # 每次循环只下一单，防止连环下单
                else:
                    logging.warning(f"❌ 下单未成功: {res.get('errorMsg') or res}")
        except Exception as e:
            logging.error(f"💥 评估市场 {market['name']} 时出错: {e}")

# ================= 4. 主程序运行 =================

async def main():
    # 初始化
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds)
    send_telegram("🚀 <b>龙虾智能体 V2.0 已上线</b>\n策略: 热点追踪/自动扫货\n状态: 持续监控中...")

    while True:
        try:
            await execute_smart_trade()
            # 每 15 分钟扫描一次机会
            await asyncio.sleep(900)
        except Exception as e:
            logging.error(f"🔄 循环异常: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
