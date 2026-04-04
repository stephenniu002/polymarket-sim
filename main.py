import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer
from eth_account import Account  # 建议添加，用于从私钥推导地址

# ================= 1. 基础配置与 Telegram =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 变量对齐 - 优先读取私钥
PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 自动推导地址，防止手动填错合约地址
if PK:
    try:
        # 如果私钥带0x前缀，Account能处理；如果不带，Account也能处理
        _acc = Account.from_key(PK)
        FUNDER = _acc.address
        logging.info(f"✅ 已从私钥识别钱包地址: {FUNDER}")
    except Exception as e:
        logging.error(f"❌ 私钥格式错误: {e}")
        FUNDER = os.getenv("Funder") or os.getenv("POLY_ADDRESS")
else:
    FUNDER = os.getenv("Funder") or os.getenv("POLY_ADDRESS")

def send_telegram(text):
    """发送电报通知"""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        # 增加对地址的脱敏处理
        payload = {"chat_id": TG_CHAT_ID, "text": f"🦞 龙虾系统报告:\n{text}", "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"❌ Telegram 发送失败: {e}")

logging.info("🚀 polymarket-sim: V17.3 (精调修复版) 启动")

# ================= 2. 客户端初始化 =================
# 这里的 funder 必须是你的钱包地址，不能是 USDC 合约地址
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)

# ================= 3. 核心功能函数 =================

def init_engine():
    try:
        if not PK or not FUNDER:
            logging.error("❌ 缺少关键配置: PRIVATE_KEY 或 FUNDER")
            return False
            
        logging.info(f"🔗 正在链接地址: {FUNDER}")
        
        # 签名器初始化
        client.signer = Signer(PK, chain_id=137)
        
        creds = client.create_or_derive_api_creds()
        if creds:
            client.set_api_creds(creds)
        
        # 尝试更新额度授权
        try:
            client.update_balance_allowance()
        except: 
            logging.warning("⚠️ 无法更新 Allowance，可能余额为0或RPC超时")
        
        send_telegram(f"✅ 系统已上线\n地址: <code>{FUNDER}</code>")
        return True
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return False

async def get_safe_balance():
    try:
        # 获取代币余额
        res = await asyncio.to_thread(client.get_balance)
        # 打印完整响应方便调试
        logging.info(f"📊 余额接口原始数据: {res}")
        return float(res.get("balance", 0))
    except Exception as e:
        logging.error(f"❌ 获取余额异常: {e}")
        return 0.0

def fetch_top_markets():
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 5, "active": "true", "closed": "false", "minimum_order_size": "1"}
        res = requests.get(url, params=params, timeout=10).json()
        return [{"name": m["question"], "token": m["tokens"][0]["token_id"]} for m in res if m.get("tokens")]
    except: return []

# ================= 4. 交易逻辑 =================

async def trade_step():
    balance = await get_safe_balance()
    logging.info(f"💰 当前可用余额: {balance} USDC")
    
    # 因为你钱包里目前只有 1.0 USDC，这里门槛设低一点
    if balance < 0.5:
        logging.warning("⚠️ 余额极低，可能无法覆盖最小下单额(通常需>1或5 USDC)")
        return

    markets = fetch_top_markets()
    if not markets: 
        logging.warning("⚠️ 未能获取到活跃市场")
        return

    target = markets[0]
    try:
        # 获取买卖盘
        ob = client.get_order_book(target['token'])
        if not ob.get("bids") or not ob.get("asks"): 
            logging.warning("⚠️ 盘口深度不足")
            return
            
        # 取中间价
        mid_price = round((float(ob["bids"][0][0]) + float(ob["asks"][0][0])) / 2, 2)
        
        # 验证性下单：尽量接近最小限额
        # 注意：Polymarket 很多市场最小下单是 5 USDC，如果失败请看日志返回的错误信息
        order_size = 1.0  # 尝试 1 USDC
        
        order = OrderArgs(price=mid_price, size=order_size, side="buy", token_id=str(target['token']))
        
        def _send():
            signed = client.create_order(order)
            return client.post_order(signed, OrderType.GTC)
            
        res = await asyncio.to_thread(_send)
        
        if res and res.get("success"):
            msg = f"🎯 【下单成功】\n市场: {target['name']}\n价格: {mid_price}\n数量: {order_size}\n余额: {balance} USDC"
            logging.info(msg)
            send_telegram(msg)
        else:
            err_msg = res.get("errorMsg
