import os
import time
import requests
import logging

# ===============================
# 基础配置
# ===============================
BASE = "https://clob.polymarket.com"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 从环境变量读取
TOKENS = {
    "BTC": os.getenv("BTC_TOKEN_ID"),
    "ETH": os.getenv("ETH_TOKEN_ID"),
    "SOL": os.getenv("SOL_TOKEN_ID"),
    "ARB": os.getenv("ARB_TOKEN_ID"),
    "OP": os.getenv("OP_TOKEN_ID"),
    "DOGE": os.getenv("DOGE_TOKEN_ID"),
    "MATIC": os.getenv("MATIC_TOKEN_ID"),
}

# ===============================
# 获取成交数据
# ===============================
def get_trades(token_id):
    try:
        url = f"{BASE}/trades?token_id={token_id}"
        res = requests.get(url, timeout=5)
        data = res.json()

        if not isinstance(data, list):
            return []

        return data[-20:]  # 最近20笔
    except Exception as e:
        logging.error(f"❌ 获取 trades 失败: {e}")
        return []

# ===============================
# 信号生成（核心策略）
# ===============================
def generate_signal(trades):
    buy = 0
    sell = 0

    for t in trades:
        side = t.get("side", "")
        size = float(t.get("size", 0))

        if side == "buy":
            buy += size
        elif side == "sell":
            sell += size

    # 防止除0
    if buy == 0 and sell == 0:
        return "HOLD"

    # ===== 核心逻辑 =====
    if sell > buy * 1.5:
        return "SELL"
    elif buy > sell * 1.5:
        return "BUY"
    else:
        return "HOLD"

# ===============================
# 模拟下单（你可以换真实API）
# ===============================
def execute_trade(symbol, signal):
    if signal == "HOLD":
        return

    logging.info(f"🚀 {symbol} 信号: {signal}")

    # 👉 实盘这里替换为真实下单
    # 例如：clob_client.create_order(...)
    # 当前先打印
    logging.info(f"📈 模拟下单: {symbol} -> {signal}")

# ===============================
# 主循环
# ===============================
def run():
    logging.info("🦞 实盘系统启动成功")

    while True:
        for symbol, token_id in TOKENS.items():

            if not token_id:
                logging.warning(f"⚠️ {symbol} 未配置 TOKEN_ID")
                continue

            trades = get_trades(token_id)

            if not trades:
                logging.warning(f"⚠️ {symbol} 无交易数据")
                continue

            signal = generate_signal(trades)

            logging.info(f"{symbol} → {signal}")

            execute_trade(symbol, signal)

        time.sleep(10)  # 每10秒跑一轮


# ===============================
# 启动
# ===============================
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(f"❌ 崩溃: {e}")
        time.sleep(5)
