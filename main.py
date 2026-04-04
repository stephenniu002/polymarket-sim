import os
import time
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from tg import send_message # 确保 tg.py 还在

# 1. 基础配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
SIGNATURE_TYPE_PROXY = 2 # 代理钱包模式

# 2. 实例化客户端 (适配 0.34.6)
def get_polymarket_client():
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),
        chain_id=POLYGON,
        signature_type=SIGNATURE_TYPE_PROXY,
        funder=os.getenv("POLY_ADDRESS")
    )
    client.set_api_creds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )
    return client

client = get_polymarket_client()

# 3. 动态扫描函数 (解决 5 分钟 ID 变化)
def get_live_target(asset="Bitcoin"):
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        valid = [m for m in resp if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
        if valid:
            m = max(valid, key=lambda x: float(x.get("volume", 0)))
            return {"q": m.get("question"), "tid": m.get("clobTokenIds")[0]}
    except:
        return None
    return None

# 4. 下单函数
def place_lobster_order(token_id, price=0.5, size=1.0):
    try:
        order_args = client.create_order(price=float(price), size=float(size), side="buy", token_id=str(token_id))
        signed = client.sign_order(order_args)
        return client.place_order(signed)
    except Exception as e:
        logging.error(f"❌ 交易异常: {e}")
        return None

# 5. 主循环
def lobster_fire_control_v4():
    logging.info("🚀 龙虾火控系统 V4.1 (单文件实盘版) 启动")
    send_message("🦞 龙虾火控系统 V4.1 已上线！\n监测账户余额中...")

    while True:
        try:
            # 检查余额 (0x365B...)
            resp = client.get_collateral_balance(os.getenv("POLY_ADDRESS"))
            balance = round(float(resp.get("balance", 0)), 2)
            logging.info(f"💰 账户余额: {balance} USDC")

            if balance < 1.0:
                logging.warning("⚠️ 余额不足，挂机中...")
                time.sleep(60)
                continue

            # 扫描核心资产
            for asset in ["Bitcoin", "Ethereum", "Solana"]:
                target = get_live_target(asset)
                if target:
                    logging.info(f"📡 监测中: {target['q']}")
                    # 测试下单逻辑 (去掉注释即可开火)
                    # place_lobster_order(target['tid'], price=0.5, size=1.0)

            logging.info("✅ 轮询完成，5分钟后同步新 ConditionID")
            time.sleep(300)

        except Exception as e:
            logging.error(f"主程序故障: {e}")
            time.sleep(10)

if __name__ == "__main__":
    lobster_fire_control_v4()
