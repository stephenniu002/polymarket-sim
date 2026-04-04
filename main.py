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

logging.info("🚀 polymarket-sim: V17.5 (SDK兼容性修复版) 启动")

# ================= 2. 客户端初始化 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)
# 修复部分版本 Signer 初始化位置
try:
    client.signer = Signer(PK, chain_id=137)
except:
    pass

# ================= 3. 核心功能函数 =================

def init_engine():
    try:
        logging.info(f"🔗 正在同步 API 凭据...")
        creds = client.create_or_derive_api_creds()
        if creds:
            client.set_api_creds(creds)
            
        # 尝试静默授权同步
        try:
            if hasattr(client, 'update_balance_allowance'):
                client.update_balance_allowance()
        except: pass
            
        send_telegram(f"✅ 系统已上线\n地址: <code>{FUNDER}</code>\n当前状态: 正在获取余额...")
        return True
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        return False

async def get_universal_balance():
    """
    万能余额获取函数：自动适配 py-clob-client 的不同版本方法名
    """
    res = None
    try:
        # 尝试路径 1: 现代版本常用的 collateral balance
        if hasattr(client, 'get_collateral_balance'):
            res = await asyncio.to_thread(client.get_collateral_balance)
        # 尝试路径 2: 某些版本直接使用 get_balance
        elif hasattr(client, 'get_balance'):
            res = await asyncio.to_thread(client.get_balance)
        # 尝试路径 3: 某些版本通过 get_user_allowance 间接返回
        elif hasattr(client, 'get_allowance'):
            res = await asyncio.to_thread(client.get_allowance)
        # 尝试路径 4: 如果方法名都找不到，尝试直接列出 client 属性辅助排查
        else:
            methods = [m for m in dir(client) if 'balance' in m.lower()]
            logging.warning(f"⚠️ 未找到标准余额方法。候选方法: {methods}")
            if methods:
                method_to_call = getattr(client, methods[0])
                res = await asyncio.to_thread(method_to_call)

        logging.info(f"📊 [调试] 余额原始响应: {res}")

        # 解析不同格式的响应
        if isinstance(res, dict):
            # 常见返回格式可能是 {"balance": "25.68"} 或 {"amount": "25.68"}
            val = res.get("balance") or res.get("amount") or 0.0
            return float(val)
        elif isinstance(res, (int, float, str)):
            return float(res)
            
        return 0.0
    except Exception as e:
        logging.error(f"❌ 余额解析失败: {e}")
        return 0.0

# ================= 4. 交易逻辑 =================

async def trade_step():
    balance = await get_universal_balance()
    logging.info(f"💰 账户可用余额: {balance} USDC")
    
    if balance > 0:
        # 如果检测到余额，发送电报通知确认
        send_telegram(f"💰 实时余额更新: <b>{balance} USDC</b>")
    
    if balance < 1.0:
        logging.warning("⚠️ 余额低于 1 USDC，暂不执行扫描")
        return

    # 获取市场信息并继续...
    logging.info("🔎 正在扫描高流动性预测市场...")

# ================= 5. 入口 =================

async def main():
    if not init_engine(): return
    while True:
        try:
            await trade_step()
            await asyncio.sleep(600) # 每10分钟检查一次
        except Exception as e:
            logging.error(f"🔄 循环异常: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
