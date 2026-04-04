import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ========== 配置 ==========
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
ASSETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "Dogecoin", "BNB"]
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
# =========================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_message(msg: str):
    if TG_TOKEN and TG_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg}, timeout=5)
        except Exception as e:
            logging.error(f"Telegram 发送失败: {e}")

def get_client():
    # 修复：ClobClient 基础初始化
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),
        chain_id=POLYGON
    )
    # 设置 API 凭证
    creds = ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )
    client.set_api_creds(creds)
    return client

# 全局客户端
client = get_client()

async def get_balance():
    """异步查询余额，并增加健壮性校验"""
    try:
        # 使用 run_in_executor 防止阻塞异步循环
        resp = await asyncio.get_event_loop().run_in_executor(
            None, client.get_collateral_balance
        )
        # 注意：SDK 返回结构通常是字符串或包含 'balance' 的字典
        if resp and isinstance(resp, dict):
            balance = round(float(resp.get("balance", 0)), 2)
            logging.info(f"💰 [实盘状态] 账户余额: {balance} USDC")
            return balance
        return 0.0
    except Exception as e:
        logging.error(f"❌ 余额查询异常 (请检查 API 权限): {e}")
        return 0.0

def fetch_live_token(asset_name: str):
    """抓取市场 token_id"""
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": asset_name, "limit": 10}
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        # 筛选条件：包含 'above'，有 token，且是活跃的
        valid = [m for m in resp if "clobTokenIds" in m and m.get("clobTokenIds")]
        if valid:
            # 按成交量排序选最火的市场
            m = max(valid, key=lambda x: float(x.get("volume", 0)))
            return m.get("clobTokenIds")[0]
    except Exception as e:
        logging.warning(f"获取 {asset_name} 市场数据失败: {e}")
    return None

async def execute_trade(token_id: str, price: float = 0.5):
    """异步执行下单全流程"""
    try:
        def _place():
            # 整合下单逻辑到线程池，避免 ClobClient 内部同步调用卡死异步
            order_args = client.create_order(
                price=price,
                size=ORDER_SIZE,
                side="buy",
                token_id=token_id
            )
            signed_order = client.sign_order(order_args)
            return client.place_order(signed_order)

        result = await asyncio.get_event_loop().run_in_executor(None, _place)
        if result and result.get("success"):
            logging.info(f"✅ 下单成功: {token_id}")
            return result
        else:
            logging.error(f"❌ 下单未成功: {result}")
            return None
    except Exception as e:
        logging.error(f"❌ 下单异常: {e}")
        return None

async def trade_cycle():
    """单轮交易循环"""
    balance = await get_balance()
    if balance < ORDER_SIZE:
        logging.warning("⚠️ 余额不足，系统待机中...")
        return

    tasks = []
    for asset in ASSETS:
        token_id = fetch_live_token(asset)
        if token_id:
            logging.info(f"📡 {asset} 匹配成功: {token_id}")
            tasks.append(execute_trade(token_id))
        else:
            logging.debug(f"⏭️ {asset} 未找到合适市场")

    if tasks:
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r)
        if success_count > 0:
            send_message(f"🦞 龙虾巡检: 成功下单 {success_count} 个品种，当前余额 {balance} USDC")

async def main_loop():
    logging.info("🚀 龙虾实盘系统 V5.5 (修复版) 启动")
    send_message("🦞 龙虾系统已上线！")
    while True:
        try:
            await trade_cycle()
        except Exception as e:
            logging.error(f"⚠️ 核心循环异常: {e}")
        
        await asyncio.sleep(300) # 5分钟轮询一次

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("程序手动停止")
