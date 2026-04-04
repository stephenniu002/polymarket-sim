import os
import asyncio
import logging
import requests
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ========= 配置 (已适配 Railway 变量) =========
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = Web3.to_checksum_address(os.getenv("Funder"))

ORDER_AMOUNT = 1.0        # 每笔固定投入 1.0 USDC
PRICE_THRESHOLD = 0.2    # 捡漏门槛 <= 0.2
SCAN_INTERVAL = 60       # 每 60 秒全网扫描一轮

SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ========= 初始化 Polymarket 客户端 =========
client = ClobClient(
    host="https://clob.polymarket.com",
    key=SIGNER_PK,
    chain_id=POLYGON,
    signature_type=2,
    funder=FUNDER
)

client.set_api_creds(ApiCreds(
    api_key=os.getenv("POLY_API_KEY"),
    api_secret=os.getenv("POLY_SECRET"),
    api_passphrase=os.getenv("POLY_PASSPHRASE")
))

# ========= 核心功能函数 =========
async def get_balance():
    """获取 Polymarket 协议内的 USDC.e 余额"""
    try:
        # SDK 0.34+ 必须显式传入 FUNDER 
        resp = await asyncio.to_thread(client.get_collateral_balance)
        balance = float(resp.get("balance", 0))
        logging.info(f"💰 账户可用余额: {balance} USDC")
        return balance
    except Exception as e:
        logging.error(f"❌ 余额读取异常: {e}")
        return 0.0

def fetch_market(symbol):
    """从 Gamma API 动态抓取该币种成交量最大的价格盘"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        # 搜索 "Price" 确保是价格类预测盘
        resp = requests.get(url, params={
            "active": "true",
            "search": f"{symbol} Price", 
            "limit": 10
        }, timeout=10).json()

        # 过滤掉没有 TokenID 的无效市场
        valid = [m for m in resp if m.get("clobTokenIds")]
        if not valid:
            return None, None

        # 选取成交量最大的盘口 (通常是最新的)
        best = max(valid, key=lambda x: float(x.get("volume", 0)))
        
        # 返回 Index 0 (看涨/Yes) 和 市场标题
        return best["clobTokenIds"][0], best["question"]

    except Exception as e:
        logging.error(f"❌ 抓取市场失败 [{symbol}]: {e}")
        return None, None

async def trade_one(symbol):
    """
    单路捡漏逻辑：查价 -> 计算份数 -> 执行下单
    """
    token_id, name = fetch_market(symbol)
    if not token_id:
        return False

    try:
        # 1. 获取最新价格
        price_resp = await asyncio.to_thread(client.get_price, token_id, side="BUY")
        price = float(price_resp.get("price", 1.0))
        
        logging.info(f"🔍 {symbol} | 当前价格: {price} | 目标: <= {PRICE_THRESHOLD}")

        # 2. 只有价格 <= 0.2 才下单
        if price > PRICE_THRESHOLD or price <= 0:
            return False

        # 3. 计算份数 (投入 1 USDC / 单价)
        # 例如单价 0.05，则买入 20 份
        shares = round(ORDER_AMOUNT / price, 2)
        logging.info(f"🎯 触发捡漏: {name} (买入 {shares} 份)")

        def _order():
            # 创建订单参数
            order_args = client.create_order(
                price=price,
                size=shares,
                side="buy",
                token_id=token_id
            )
            # 私钥签名
            signed = client.sign_order(order_args)
            # 提交到 CLOB
            return client.place_order(signed)

        res = await asyncio.to_thread(_order)
        if res and res.get("success"):
            logging.info(f"✅ 【下单成功】 {symbol} @ {price}")
            return True
        else:
            logging.warning(f"⚠️ 下单响应失败 {symbol}: {res}")

    except Exception as e:
        logging.error(f"❌ 执行异常 {symbol}: {e}")

    return False

# ========= 主循环 (补全部分) =========
async def main():
    logging.info("🚀 龙虾实盘捡漏系统已上线")
    logging.info(f"🤖 监控币种: {SYMBOLS}")
    logging.info(f"⚙️ 策略: 价格 <= {PRICE_THRESHOLD} 时，每笔投入 {ORDER_AMOUNT} USDC")

    while True:
        try:
            # 1. 检查余额，确保至少够下一笔单 (1 USDC)
            balance = await get_balance()
            
            if balance >= ORDER_AMOUNT:
                logging.info(f"--- 开始全网扫描 ({len(SYMBOLS)} 个币种) ---")
                
                # 2. 7路并发执行 (使用 gather)
                tasks = [trade_one(s) for s in SYMBOLS]
                results = await asyncio.gather(*tasks)
                
                # 3. 汇总本轮结果
                success_count = sum(1 for r in results if r)
                if success_count > 0:
                    logging.info(f"🎊 本轮成功捡漏 {success_count} 笔！")
            else:
                logging.warning(f"🛑 资金不足 (余额 {balance} < {ORDER_AMOUNT})，等待充值...")

        except Exception as e:
            logging.error(f"⚠️ 核心循环发生崩溃: {e}")
            await asyncio.sleep(10) # 崩溃后稍作停顿再重启
            
        # 等待下一轮扫描
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 程序已手动停止")
