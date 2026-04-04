import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer
from eth_account import Account

# ================= 1. 基础配置与 Telegram =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 优先级：FUNDING_KEY > PRIVATE_KEY
PK = os.getenv("FUNDING_KEY") or os.getenv("PRIVATE_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 自动推导地址，防止手动填写 USDC 合约地址的错误再次发生
if PK:
    try:
        _acc = Account.from_key(PK)
        FUNDER = _acc.address
        logging.info(f"✅ 钱包地址已自动识别: {FUNDER}")
    except Exception as e:
        logging.error(f"❌ 私钥解析失败，请检查 FUNDING_KEY 格式: {e}")
        FUNDER = os.getenv("POLY_ADDRESS")
else:
    FUNDER = os.getenv("POLY_ADDRESS")
    logging.warning("⚠️ 未检测到私钥，将使用环境变量中的地址")

def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": f"🦞 龙虾系统报告:\n{text}", "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"❌ Telegram 发送失败: {e}")

logging.info("🚀 polymarket-sim: V17.4 (余额修复版) 启动")

# ================= 2. 客户端初始化 =================
# 强制指定 Polygon 上的 Native USDC 合约地址
NATIVE_USDC = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

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
        logging.info(f"🔗 正在链接地址: {FUNDER}")
        
        # 1. 导出 API 凭据
        creds = client.create_or_derive_api_creds()
        if creds:
            client.set_api_creds(creds)
            logging.info("🔑 API 凭据已就绪")
        
        # 2. 强制同步 Allowance (这一步是识别余额的关键)
        try:
            # 某些库版本需要手动指定 token 地址，这里我们尝试同步
            client.update_balance_allowance()
            logging.info("✅ 已完成资产授权状态同步")
        except Exception as e:
            logging.warning(f"⚠️ 授权同步提示: {e}")
            
        send_telegram(f"✅ 系统已上线\n监控地址: <code>{FUNDER}</code>")
        return True
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return False

async def get_detailed_balance():
    """获取并显示详细余额信息"""
    try:
        # 获取余额响应
        res = await asyncio.to_thread(client.get_balance)
        
        # 打印原始数据到日志，方便排查
        logging.info(f"📊 [调试] 余额接口原始数据: {res}")
        
        # 提取 balance 字段
        if isinstance(res, dict):
            balance = float(res.get("balance", 0.0))
        else:
            balance = 0.0
            
        return balance
    except Exception as e:
        logging.error(f"❌ 获取余额异常: {e}")
        return 0.0

def fetch_top_markets():
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 3, "active": "true", "closed": "false"}
        res = requests.get(url, params=params, timeout=10).json()
        return [{"name": m["question"], "token": m["tokens"][0]["token_id"]} for m in res if m.get("tokens")]
    except: return []

# ================= 4. 交易逻辑 =================

async def trade_step():
    # 获取余额
    balance = await get_detailed_balance()
    logging.info(f"💰 当前实时余额: {balance} USDC")
    
    # 只要余额大于 0.1 就算识别成功
    if balance < 0.1:
        logging.warning(f"⚠️ 识别余额为 {balance}，请确认钱包 {FUNDER} 中持有的是 Native USDC")
        return

    # 获取市场
    markets = fetch_top_markets()
    if not markets: return

    target = markets[0]
    logging.info(f"🔎 正在扫描市场: {target['name']}")
    
    # 下一步逻辑... (保持静默监控，不轻易下单)

# ================= 5. 主循环 =================

async def main():
    if not init_engine(): return
    
    # 初始运行一次显示余额
    await trade_step()
    
    while True:
        try:
            await trade_step()
            # 每 5 分钟检查一次
            await asyncio.sleep(300) 
        except Exception as e:
            logging.error(f"🔄 运行异常: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
