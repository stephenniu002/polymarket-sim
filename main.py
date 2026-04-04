import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ========= 基础配置 =========
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ORDER_SIZE = 1.0
TEST_PRICE = 0.99   # 🔥 强制成交用（关键）

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

print("🚨 文件已启动")

# ========= TG =========
def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        logging.error(f"TG发送失败: {e}")

# ========= 客户端 =========
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

# ========= 获取市场 =========
def get_best_market():
    try:
        url = "https://gamma-api.polymarket.com/markets"
        data = requests.get(url, params={"active": "true", "limit": 20}, timeout=10).json()

        valid = [m for m in data if m.get("clobTokenIds")]
        best = max(valid, key=lambda x: float(x.get("volume", 0)))

        return best["clobTokenIds"][0], best.get("question")
    except Exception as e:
        logging.error(f"❌ 市场获取失败: {e}")
        return None, None

# ========= 下单 =========
async def force_trade():
    token_id, title = get_best_market()

    if not token_id:
        logging.warning("⚠️ 没找到市场")
        return

    logging.info(f"🎯 市场: {title}")

    try:
        def _trade():
            order = client.create_order(
                price=TEST_PRICE,
                size=ORDER_SIZE,
                side="buy",
                token_id=str(token_id)
            )
            signed = client.sign_order(order)
            return client.place_order(signed)

        res = await asyncio.to_thread(_trade)

        logging.info(f"📥 返回: {res}")

        send_tg(f"""
🦞 下单测试
市场: {title}
结果: {res}
""")

    except Exception as e:
        logging.error(f"❌ 下单异常: {e}")
        send_tg(f"❌ 下单异常: {e}")

# ========= 主循环 =========
async def main():
    logging.info("🚀 系统启动成功")
    send_tg("🚀 系统已启动（测试版）")

    counter = 0

    while True:
        try:
            logging.info("🔁 循环中...")

            await force_trade()

            counter += 1

            # 每5轮报告一次
            if counter % 5 == 0:
                send_tg("📊 系统正常运行中（5轮心跳）")

        except Exception as e:
            logging.error(f"⚠️ 主循环异常: {e}")

        await asyncio.sleep(60)

# ========= 启动 =========
if __name__ == "__main__":
    asyncio.run(main())
