import os
import asyncio
import requests
import logging
import sys
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 日志 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

# ================= TG 通知 =================
def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=5)
        except:
            pass

# ================= 获取价格 =================
def get_price(token_id):
    try:
        url = f"https://clob.polymarket.com/price?token_id={token_id}"
        r = requests.get(url, timeout=5).json()
        return float(r.get("price", 0))
    except:
        return 0

# ================= 获取市场 =================
def get_markets():
    try:
        url = "https://clob.polymarket.com/markets"
        data = requests.get(url, timeout=5).json()
        return data[:7]  # 只取前7个
    except:
        return []

# ================= 主程序 =================
async def main():
    logger.info("🚀 实盘套利系统启动...")

    # 环境变量
    pk = os.getenv("PRIVATE_KEY")
    order_size = float(os.getenv("ORDER_SIZE", "1"))

    # 初始化
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=pk,
        chain_id=42161  # ✅ Arbitrum
    )

    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    logger.info("🔑 API 初始化完成")

    while True:
        try:
            markets = get_markets()
            logger.info(f"📊 扫描市场数量: {len(markets)}")

            for m in markets:
                try:
                    yes_id = m["tokens"][0]["token_id"]
                    no_id = m["tokens"][1]["token_id"]

                    yes_price = get_price(yes_id)
                    no_price = get_price(no_id)

                    if yes_price == 0 or no_price == 0:
                        continue

                    total = yes_price + no_price

                    logger.info(f"🪙 YES:{yes_price} NO:{no_price} SUM:{total}")

                    # ================= 套利逻辑 =================
                    if total < 0.97:
                        logger.info("🔥 发现套利机会！")

                        # 买 YES
                        client.post_order({
                            "price": round(yes_price, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": yes_id
                        })

                        # 买 NO
                        client.post_order({
                            "price": round(no_price, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": no_id
                        })

                        msg = f"✅ 套利成功\nYES:{yes_price}\nNO:{no_price}\nSUM:{total}"
                        send_tg(msg)

                    # ================= 趋势策略 =================
                    elif yes_price < 0.4:
                        logger.info("📈 低价买 YES")

                        client.post_order({
                            "price": round(yes_price, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": yes_id
                        })

                    elif yes_price > 0.6:
                        logger.info("📉 高价买 NO")

                        client.post_order({
                            "price": round(no_price, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": no_id
                        })

                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"❌ 单市场错误: {e}")

            logger.info("⏳ 进入下一轮...")
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"💥 主循环崩溃: {e}")
            await asyncio.sleep(10)

# ================= 启动 =================
if __name__ == "__main__":
    asyncio.run(main())
