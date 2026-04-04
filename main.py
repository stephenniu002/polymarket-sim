import os, asyncio, logging, time, requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.signer import Signer

# ================= 1. 基础配置 =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.info("🚀 polymarket-sim: V17.1 (实盘资产对齐版) 启动")

# 变量对齐：兼容多种命名方式
PK = os.getenv("PRIVATE_KEY") or os.getenv("FOX_PRIVATE_KEY") or os.getenv("POLY_PRIVATE_KEY")
FUNDER = os.getenv("Funder") or os.getenv("POLY_ADDRESS")

if not PK or not PK.startswith("0x"):
    raise Exception("🛑 错误: PRIVATE_KEY 未配置或格式不正确 (需0x开头)")

if not FUNDER:
    logging.warning("⚠️ Funder 变量缺失，将尝试在初始化时自动推导")

# ================= 2. 客户端初始化 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)

# 强制绑定 Signer 解决 SDK 内部 NoneType 报错
client.signer = Signer(PK, chain_id=137)

# ================= 3. 核心功能函数 =================

def init_engine():
    """初始化 API 凭证与授权"""
    try:
        logging.info(f"🔗 激活链路: {FUNDER[:10] if FUNDER else '正在推导'}...")
        
        # 强制派生/获取凭证
        creds = client.create_or_derive_api_creds()
        if creds:
            client.set_api_creds(creds)
            # 深度注入：确保所有属性被强制更新
            client.api_key = creds.api_key
            client.api_secret = creds.api_secret
            client.api_passphrase = creds.api_passphrase
            logging.info(f"✅ 凭证注入成功: {creds.api_key[:8]}...")
        
        # 尝试更新授权 (即使报错也不中断程序)
        try:
            client.update_balance_allowance()
        except Exception as e:
            logging.warning(f"⚠️ Allowance 刷新跳过 (通常因为USDC余额为0): {e}")
            
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化严重失败: {e}")
        return False

async def get_safe_balance():
    """多策略余额获取：识别 Native USDC"""
    try:
        # 策略 1: 扫描所有用户资产列表 (最准确)
        res_list = await asyncio.to_thread(client.get_user_balances)
        if isinstance(res_list, list):
            for asset in res_list:
                # 寻找资产类型为 collateral 的项 (Polymarket 抵押品)
                if asset.get("asset_type") == "collateral":
                    bal = float(asset.get("balance", 0))
                    if bal > 0: return bal

        # 策略 2: 备选单项查询
        res_single = await asyncio.to_thread(client.get_balance)
        return float(res_single.get("balance", 0))
    except Exception as e:
        logging.error(f"❌ 余额扫描失败: {e}")
        return 0.0

def fetch_active_markets():
    """从 Gamma API 获取高热度市场"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 15, "active": "true", "closed": "false"}
        res = requests.get(url, params=params, timeout=10).json()
        
        valid_markets = []
        for m in res:
            tokens = m.get("tokens", [])
            vol = float(m.get("volume", 0))
            # 过滤有成交量且有 token 的市场
            if vol > 1000 and len(tokens) >= 2:
                valid_markets.append({
                    "name": m.get("question", "未知"),
                    "token": tokens[0]["token_id"],
                    "volume": vol
                })
        return sorted(valid_markets, key=lambda x: x["volume"], reverse=True)
    except:
        return []

# ================= 4. 交易执行逻辑 =================

async def trade_step():
    logging.info("💓 Heartbeat: 正在检索市场状态...")
    
    # 1. 检查余额
    balance = await get_safe_balance()
    logging.info(f"💰 当前识别到可用余额: {balance} USDC")
    
    if balance <= 0.1: # 留 0.1 的底仓余量
        logging.warning("⚠️ 余额极低或未识别到 Native USDC，跳过扫描")
        return

    # 2. 获取市场
    markets = fetch_active_markets()
    if not markets:
        logging.warning("🔎 暂时没有符合交易条件的市场")
        return

    # 3. 简单的盘口扫描与下单测试
    for m in markets:
        try:
            # 自动获取当前盘口价格 (买一卖一中间价)
            ob = client.get_order_book(m['token'])
            if not ob.get("bids") or not ob.get("asks"): continue
            
            mid_price = round((float(ob["bids"][0][0]) + float(ob["asks"][0][0])) / 2, 3)
            
            # 策略：买入 0.1 USDC 价值的份额进行链路测试
            order_size = 0.1 
            logging.info(f"🎯 尝试在市场 [{m['name'][:20]}...] 下单 | 价格: {mid_price}")
            
            order = OrderArgs(
                price=mid_price,
                size=order_size,
                side="buy",
                token_id=str(m['token'])
            )
            
            def _send():
                signed = client.create_order(order)
                return client.post_order(signed, OrderType.GTC)
            
            result = await asyncio.to_thread(_send)
            
            if result and result.get("success"):
                logging.info(f"✅ 【交易成功】订单 ID: {result.get('orderID')}")
                return # 每次循环只下一个单
            else:
                logging.warning(f"❌ 下单未成交: {result}")
                
        except Exception as e:
            logging.error(f"⚠️ 扫描市场 {m['name'][:10]} 出错: {e}")
            continue

# ================= 5. 主入口 =================

async def main():
    # 执行初始化
    if not init_engine():
        logging.critical("🛑 引擎初始化失败，请检查私钥权限！")
        return

    while True:
        try:
            await trade_step()
            logging.info("💤 扫描结束，5分钟后进行下一次 Heartbeat...")
            await asyncio.sleep(300) 
        except Exception as e:
            logging.error(f"🔄 循环捕获异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())

# ... 后面 execute, step, main 保持你提供的逻辑不变 ...
