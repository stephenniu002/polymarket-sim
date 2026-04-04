import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ========= 配置 =========
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

ORDER_SIZE = 1.0
TARGET_PRICE = 0.2

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ========= TG =========
def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

# ========= 初始化 =========
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

# ========= ✅ 终极余额 =========
async def get_balance():
    try:
        def _get():
            for m in ["get_collateral_balance", "get_balance", "get_user_balance"]:
                if hasattr(client, m):
                    func = getattr(client, m)
                    try:
                        return func(FUNDER)
                    except:
                        return func()
            return 0

        resp = await asyncio.to_thread(_get)

        logging.info(f"🔍 原始余额返回: {resp}")

        if isinstance(resp, dict):
            val = resp.get("balance") or resp.get("available") or resp.get("collateral_balance") or 0
            return float(val)

        return float(resp)

    except Exception as e:
        logging.error(f"❌ 余额失败: {e}")
        return 0.0

# ========= 获取最活跃市场 =========
def get_best_market():
    try:
        data = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "closed": "false", "limit": 50},
            timeout=10
        ).json()

        valid = [m for m in data if m.get("clobTokenIds")]

        if not valid:
            return None, None

        best = max(valid, key=lambda x: float(x.get("volume", 0)))

        return best["clobTokenIds"][0], best.get("question")

    except Exception as e:
        logging.error(f"❌ 市场抓取失败: {e}")
        return None, None

# ========= ✅ 核心下单 =========
async def trade_once():
    token_id, title = get_best_market()

    if not token_id:
        return "❌ 无可用市场"

    logging.info(f"🎯 市场: {title}")

    try:
        def _trade():
            return client.place_order({
                "token_id": str(token_id),
                "price": float(TARGET_PRICE),
                "size": float(ORDER_SIZE),
                "side": "BUY"
            })

        res = await asyncio.to_thread(_trade)

        logging.info(f"📥 下单返回: {res}")

        if res and (res.get("orderID") or res.get("success")):
            return f"✅ 成功下单\n{title}"
        else:
            return f"⚠️ 未成交\n{res}"

    except Exception as e:
        return f"❌ 下单崩溃: {e}"

# ========= 主循环 =========
async def main():
    logging.info("🚀 V10 实盘启动")
    send_tg("🦞 V10 已启动（最终稳定版）")

    counter = 0

    while True:
        try:
            balance = await get_balance()
            logging.info(f"💰 当前余额: {balance}")

            result = await trade_once()

            logging.info(result)
            send_tg(f"{result}\n余额: {balance}")

            counter += 1

            # 每 5 分钟报告
            if counter >= 5:
                send_tg(f"📊 5分钟报告\n余额: {balance}")
                counter = 0

        except Exception as e:
            logging.error(f"⚠️ 主循环异常: {e}")

        await asyncio.sleep(60)

# ========= 启动 =========
if __name__ == "__main__":
    asyncio.run(main())
