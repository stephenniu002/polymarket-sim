import os
import time
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds # 👈 导入凭证类
from tg import send_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_polymarket_client():
    # 1. 基础初始化
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),
        chain_id=POLYGON,
        signature_type=2, # 直接用数字 2，最稳
        funder=os.getenv("POLY_ADDRESS")
    )
    
    # 2. 构造凭证对象并设置
    # 这个版本可能只接受这种显式的 ApiCreds 对象
    creds = ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )
    client.set_api_creds(creds) # 👈 直接传对象，不传关键字参数
    
    return client

# 尝试启动客户端
try:
    client = get_polymarket_client()
except Exception as e:
    logging.error(f"❌ 客户端启动失败，尝试备选方案: {e}")
    # 如果上面还报错，说明版本要求更简单
    client = ClobClient("https://clob.polymarket.com", POLYGON, os.getenv("POLY_PRIVATE_KEY"))

def get_live_target(asset="Bitcoin"):
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "search": f"{asset} Price", "limit": 5}
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        valid = [m for m in resp if "above" in m.get("question", "").lower() and m.get("clobTokenIds")]
        if valid:
            m = max(valid, key=lambda x: float(x.get("volume", 0)))
            return {"q": m.get("question"), "tid": m.get("clobTokenIds")[0]}
    except: return None
    return None

def lobster_fire_control_v4_2():
    logging.info("🚀 龙虾火控系统 V4.2 (环境适配版) 启动")
    send_message("🦞 龙虾火控系统 V4.2 已上线！")

    while True:
        try:
            # 这里的余额查询是关键
            resp = client.get_collateral_balance(os.getenv("POLY_ADDRESS"))
            balance = round(float(resp.get("balance", 0)), 2)
            logging.info(f"💰 实盘余额: {balance} USDC")

            if balance < 1.0:
                logging.warning("⚠️ 余额不足，系统待机中...")
                time.sleep(60)
                continue

            for asset in ["Bitcoin", "Ethereum", "Solana"]:
                target = get_live_target(asset)
                if target:
                    logging.info(f"📡 监控目标: {target['q']}")

            logging.info("✅ 本轮巡检完成。")
            time.sleep(300)

        except Exception as e:
            logging.error(f"⚠️ 运行异常: {e}")
            time.sleep(10)

if __name__ == "__main__":
    lobster_fire_control_v4_2()
            logging.error(f"主程序故障: {e}")
            time.sleep(10)

if __name__ == "__main__":
    lobster_fire_control_v4()
