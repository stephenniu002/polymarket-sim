import os, asyncio, logging, time, requests, traceback
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds

# --- 1. 基础日志配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 全局客户端占位
client = None

def init_v17_1():
    global client
    try:
        logging.info("🔧 V17.1 启动：全手动变量校验与初始化...")
        
        # 1. 严格读取所有变量
        pk = os.getenv("POLY_PRIVATE_KEY")
        funder = os.getenv("POLY_ADDRESS")
        api_key = os.getenv("POLY_API_KEY")
        api_secret = os.getenv("POLY_SECRET")
        api_pass = os.getenv("POLY_PASSPHRASE")

        # 校验必填项
        if not pk or not api_key:
            logging.error("❌ 严重错误：POLY_PRIVATE_KEY 或 POLY_API_KEY 为空！")
            return False

        # 2. 实例化客户端 (确保这一步拿到的是非空 PK)
        client = ClobClient(
            host="https://clob.polymarket.com", 
            key=pk, 
            chain_id=137, 
            funder=funder
        )

        # 3. 手动构造 ApiCreds 对象并强制注入
        # 这是为了绕过 SDK 内部可能失效的自动派生逻辑
        creds = ApiCreds(
            api_key=api_key, 
            api_secret=api_secret, 
            api_passphrase=api_pass
        )
        
        # 核心修正：手动给对象补齐 SDK 可能查找的属性
        setattr(creds, 'signature_type', 2) 
        
        client.set_api_creds(creds)
        
        # 4. 验证链路
        logging.info("🔗 正在尝试激活链路...")
        client.update_balance_allowance()
        
        logging.info("✅ 链路已激活 (全手动初始化模式)")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        logging.error(traceback.format_exc()) # 这行会告诉我们到底是哪一行代码崩了
        return False

# --- 3. Gamma 市场抓取 ---
def fetch_top_markets_v17_1():
    url = "https://gamma-api.polymarket.com/markets"
    params = {"limit": 20, "active": "true", "closed": "false", "order": "volume24hr", "ascending": "false"}
    try:
        res = requests.get(url, params=params, timeout=10).json()
        scored = []
        for m in res:
            tokens = m.get("tokens", [])
            if len(tokens) >= 2:
                scored.append({"name": m.get("question"), "yes_id": tokens[0].get("token_id")})
        return scored
    except: return []

# --- 4. 交易循环 ---
async def main():
    logging.info("🚀 polymarket-sim: V17.1 (全手动重构版) 启动")
    
    if not init_v17_1():
        logging.critical("🛑 初始化失败，程序退出。请检查 Railway 环境变量！")
        return

    while True:
        try:
            # 获取余额
            resp = await asyncio.to_thread(client.get_balance)
            balance = float(resp.get("balance", 0)) if isinstance(resp, dict) else float(resp)
            logging.info(f"💰 余额: {balance} USDC.e")

            markets = fetch_top_markets_v17_1()
            if markets:
                best = markets[0]
                logging.info(f"🎯 目标: {best['name']}")
                # 这里可以添加 execute 逻辑
            
            await asyncio.sleep(300)
        except Exception as e:
            logging.error(f"⚠️ 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
