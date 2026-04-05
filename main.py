import time
import requests
import logging
from config import MARKETS, POLY_ADDRESS

logging.basicConfig(level=logging.INFO)

# ===============================
# Polymarket API
# ===============================
POSITION_URL = "https://data-api.polymarket.com/positions"

# ===============================
# 获取大户持仓
# ===============================
def get_positions(user):
    try:
        params = {
            "user": user,
            "sizeThreshold": 0.1,
            "limit": 50,
            "offset": 0,
            "sortBy": "TOKENS",
            "sortDirection": "DESC"
        }
        res = requests.get(POSITION_URL, params=params, timeout=5)
        return res.json()
    except Exception as e:
        logging.error(f"获取持仓失败: {e}")
        return []

# ===============================
# 信号生成（核心逻辑）
# ===============================
def generate_signal(positions):
    signals = []

    for p in positions:
        size = float(p.get("size", 0))
        outcome = p.get("outcome")
        condition_id = p.get("conditionId")

        # 👉 大户阈值（你可以调）
        if size > 50:
            signals.append({
                "condition_id": condition_id,
                "side": outcome,
                "size": size
            })

    return signals

# ===============================
# 模拟下单（先用这个，避免真钱）
# ===============================
def execute_trade(signal):
    logging.info(f"🚀 下单信号: {signal}")

# ===============================
# 主循环
# ===============================
def run():
    if not POLY_ADDRESS:
        logging.error("❌ 没有设置 POLY_ADDRESS")
        return

    logging.info("🚀 系统启动成功")

    while True:
        try:
            positions = get_positions(POLY_ADDRESS)

            if not positions:
                logging.warning("⚠️ 没有获取到持仓")
                time.sleep(5)
                continue

            signals = generate_signal(positions)

            if not signals:
                logging.info("😴 无交易信号")
            else:
                # 👉 只选最大仓位（关键优化）
                best = max(signals, key=lambda x: x["size"])
                execute_trade(best)

        except Exception as e:
            logging.error(f"系统异常: {e}")

        time.sleep(10)

# ===============================
if __name__ == "__main__":
    run()
