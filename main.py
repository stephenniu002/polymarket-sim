import time
import requests
import logging

logging.basicConfig(level=logging.INFO)

BASE = "https://clob.polymarket.com"

# ==============================
# 获取当前可交易市场
# ==============================
def get_active_market():
    try:
        res = requests.get(f"{BASE}/markets", timeout=5)
        data = res.json()

        for m in data:
            if (
                m.get("seriesSlug") == "eth-up-or-down-5m"
                and m.get("acceptingOrders") == True
                and m.get("active") == True
                and m.get("closed") == False
            ):
                token_ids = eval(m["clobTokenIds"])
                return {
                    "name": m["question"],
                    "up": token_ids[0],
                    "down": token_ids[1],
                }

        return None
    except Exception as e:
        logging.error(f"获取市场失败: {e}")
        return None


# ==============================
# 获取 orderbook
# ==============================
def get_orderbook(token_id):
    try:
        url = f"{BASE}/orderbook/{token_id}"
        res = requests.get(url, timeout=5)
        return res.json()
    except:
        return {}


# ==============================
# 获取价格
# ==============================
def get_price(orderbook):
    try:
        asks = orderbook.get("asks", [])
        bids = orderbook.get("bids", [])

        best_ask = float(asks[0]["price"]) if asks else None
        best_bid = float(bids[0]["price"]) if bids else None

        return best_bid, best_ask
    except:
        return None, None


# ==============================
# 策略（套利 / 对冲）
# ==============================
def strategy(up_bid, up_ask, down_bid, down_ask):
    try:
        if not all([up_ask, down_ask]):
            return None

        total = up_ask + down_ask

        # 套利机会
        if total < 0.98:
            return "ARB"

        # 正常对冲策略
        if up_ask < 0.4:
            return "BUY_UP"

        if down_ask < 0.4:
            return "BUY_DOWN"

        return None

    except:
        return None


# ==============================
# 下单（你自己接入签名）
# ==============================
def execute(action, market):
    logging.info(f"🚀 执行动作: {action} | {market['name']}")


# ==============================
# 主循环
# ==============================
def main():
    logging.info("🚀 实盘自动交易系统启动")

    current_market = None

    while True:
        try:
            market = get_active_market()

            if not market:
                logging.info("⏳ 等待新市场...")
                time.sleep(5)
                continue

            # 市场切换检测
            if current_market != market["up"]:
                logging.info(f"🔄 新市场: {market['name']}")
                current_market = market["up"]

            up_ob = get_orderbook(market["up"])
            down_ob = get_orderbook(market["down"])

            up_bid, up_ask = get_price(up_ob)
            down_bid, down_ask = get_price(down_ob)

            # 防止空数据
            if not all([up_ask, down_ask]):
                logging.warning("⚠️ 无流动性，跳过")
                time.sleep(2)
                continue

            action = strategy(up_bid, up_ask, down_bid, down_ask)

            if action:
                execute(action, market)

            # 打印监控
            logging.info(
                f"UP: {up_bid}/{up_ask} | DOWN: {down_bid}/{down_ask}"
            )

            time.sleep(2)

        except Exception as e:
            logging.error(f"❌ 主循环错误: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
