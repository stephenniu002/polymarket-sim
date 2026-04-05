import os
import time
import requests
import logging
from trade import execute_trade  # 你的交易下单模块
from strategy import generate_signal  # 你的信号策略模块

# ===============================
# 🔹 日志配置
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ===============================
# 🔹 Telegram 配置（可选）
# ===============================
TG_TOKEN = os.getenv("TG_TOKEN") or "your_telegram_bot_token"
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "your_chat_id"

def send_telegram(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg})
    except Exception as e:
        logging.warning(f"⚠️ Telegram 发送失败: {e}")

# ===============================
# 🔹 POLYMARKET 7币 TOKEN_ID 全覆盖
# ===============================
MARKETS = {
    "BTC": {
        "UP": "68033518322462371935856735251001652798688532944534600565715682414078422713363",
        "DOWN": "42290470910454159474303047950885744851262714754899371843021423088168640872907"
    },
    "ETH": {
        "UP": "22697677844037973694672765750606352785901003559149933535427801487665640947803",
        "DOWN": "115090385978773385923886371350527743245393288513466835985021881253014596643630"
    },
    "SOL": {
        "UP": "104603314801857341640835854350038686011870944676564680074680431702449050206849",
        "DOWN": "109356807032619845857448714056328897846193614693799092745423146063644528271739"
    },
    "ARB": {
        "UP": "83969554674239323125534841773025419295324024187242141567151123418758917736351",
        "DOWN": "55696486755928578342776003278410729069499785313927089760850183610072430890445"
    },
    "OP": {
        "UP": "102762789132004280347110241206954008153952900365785095086032215198759595021055",
        "DOWN": "114844319908492689652356903444093235582805928777096660934420753771345312987663"
    },
    "DOGE": {
        "UP": "106625082417191245995145458652026897669356408589941137585886068627196204381551",
        "DOWN": "70904302110360626667376939927906146916424503243022738450880960377487226196037"
    },
    "MATIC": {
        "UP": "113731536206314593343123440641902754070657405235286809042047205745082834474083",
        "DOWN": "70757969820078082396704681961608768251154072300114355273498766356711024291765"
    }
}

# ===============================
# 🔹 POLYMARKET API 基础地址
# ===============================
BASE_URL = "https://clob.polymarket.com"

# ===============================
# 🔹 获取最近成交（可选）
# ===============================
def get_trades(token_id):
    try:
        url = f"{BASE_URL}/trades?token_id={token_id}"
        res = requests.get(url, timeout=5)
        return res.json()
    except Exception as e:
        logging.warning(f"⚠️ 获取成交失败: {e}")
        return []

# ===============================
# 🔹 主逻辑示例
# ===============================
def main():
    logging.info("🦞 实盘系统启动")
    while True:
        try:
            for symbol, tokens in MARKETS.items():
                # 示例：获取最新交易信号
                signal = generate_signal(symbol)  # 返回 "UP" 或 "DOWN"
                token_id = tokens.get(signal)
                if not token_id:
                    logging.warning(f"⚠️ {symbol} {signal} 未配置 TOKEN_ID")
                    continue

                # 执行交易
                execute_trade(symbol, token_id, signal)
                logging.info(f"✅ {symbol} 下单 {signal}")

            time.sleep(5)  # 每 5 秒循环一次，可调
        except Exception as e:
            logging.error(f"❌ 系统异常: {e}")
            send_telegram(f"❌ 系统异常: {e}")
            time.sleep(10)

# ===============================
# 🔹 入口
# ===============================
if __name__ == "__main__":
    main()import os
import time
import requests
import logging
from trade import execute_trade  # 你的交易下单模块
from strategy import generate_signal  # 你的信号策略模块

# ===============================
# 🔹 日志配置
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ===============================
# 🔹 Telegram 配置（可选）
# ===============================
TG_TOKEN = os.getenv("TG_TOKEN") or "your_telegram_bot_token"
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "your_chat_id"

def send_telegram(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg})
    except Exception as e:
        logging.warning(f"⚠️ Telegram 发送失败: {e}")

# ===============================
# 🔹 POLYMARKET 7币 TOKEN_ID 全覆盖
# ===============================
MARKETS = {
    "BTC": {
        "UP": "68033518322462371935856735251001652798688532944534600565715682414078422713363",
        "DOWN": "42290470910454159474303047950885744851262714754899371843021423088168640872907"
    },
    "ETH": {
        "UP": "22697677844037973694672765750606352785901003559149933535427801487665640947803",
        "DOWN": "115090385978773385923886371350527743245393288513466835985021881253014596643630"
    },
    "SOL": {
        "UP": "104603314801857341640835854350038686011870944676564680074680431702449050206849",
        "DOWN": "109356807032619845857448714056328897846193614693799092745423146063644528271739"
    },
    "ARB": {
        "UP": "83969554674239323125534841773025419295324024187242141567151123418758917736351",
        "DOWN": "55696486755928578342776003278410729069499785313927089760850183610072430890445"
    },
    "OP": {
        "UP": "102762789132004280347110241206954008153952900365785095086032215198759595021055",
        "DOWN": "114844319908492689652356903444093235582805928777096660934420753771345312987663"
    },
    "DOGE": {
        "UP": "106625082417191245995145458652026897669356408589941137585886068627196204381551",
        "DOWN": "70904302110360626667376939927906146916424503243022738450880960377487226196037"
    },
    "MATIC": {
        "UP": "113731536206314593343123440641902754070657405235286809042047205745082834474083",
        "DOWN": "70757969820078082396704681961608768251154072300114355273498766356711024291765"
    }
}

# ===============================
# 🔹 POLYMARKET API 基础地址
# ===============================
BASE_URL = "https://clob.polymarket.com"

# ===============================
# 🔹 获取最近成交（可选）
# ===============================
def get_trades(token_id):
    try:
        url = f"{BASE_URL}/trades?token_id={token_id}"
        res = requests.get(url, timeout=5)
        return res.json()
    except Exception as e:
        logging.warning(f"⚠️ 获取成交失败: {e}")
        return []

# ===============================
# 🔹 主逻辑示例
# ===============================
def main():
    logging.info("🦞 实盘系统启动")
    while True:
        try:
            for symbol, tokens in MARKETS.items():
                # 示例：获取最新交易信号
                signal = generate_signal(symbol)  # 返回 "UP" 或 "DOWN"
                token_id = tokens.get(signal)
                if not token_id:
                    logging.warning(f"⚠️ {symbol} {signal} 未配置 TOKEN_ID")
                    continue

                # 执行交易
                execute_trade(symbol, token_id, signal)
                logging.info(f"✅ {symbol} 下单 {signal}")

            time.sleep(5)  # 每 5 秒循环一次，可调
        except Exception as e:
            logging.error(f"❌ 系统异常: {e}")
            send_telegram(f"❌ 系统异常: {e}")
            time.sleep(10)

# ===============================
# 🔹 入口
# ===============================
if __name__ == "__main__":
    main()
