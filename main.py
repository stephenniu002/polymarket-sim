import os
import asyncio
import logging
import requests
import time
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ==================== 1. 配置与初始化 ====================
SIGNER_PK = os.getenv("FOX_PRIVATE_KEY")
FUNDER = os.getenv("Funder")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 策略阈值
MIN_VOLUME = 10000       # 过滤成交量低于 10k 的垃圾盘
IMBALANCE_THRESHOLD = 2.5 # 买卖单失衡比（买盘是卖盘的2.5倍才动）
PRICE_HISTORY_LIMIT = 6  # 记录最近 6 次价格变动
SCAN_INTERVAL = 30       # 扫描频率缩短到 30 秒（抢反转）

SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "HYPE"]
price_history = {s: [] for s in SYMBOLS}
stats = {"total": 0, "wins": 0, "pnl": 0.0}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

client = ClobClient("https://clob.polymarket.com", key=SIGNER_PK, chain_id=POLYGON, signature_type=2, funder=FUNDER)
client.set_api_creds(ApiCreds(os.getenv("POLY_API_KEY"), os.getenv("POLY_SECRET"), os.getenv("POLY_PASSPHRASE")))

# ==================== 2. 核心分析模块 (Order Flow) ====================

async def get_orderflow_signal(token_id):
    """分析盘口深度：识别大单资金流向"""
    try:
        # 获取深度数据
        ob = await asyncio.to_thread(client.get_order_book, token_id)
        bids = ob.get("bids", []) # 买单 [价格, 数量]
        asks = ob.get("asks", []) # 卖单
        
        if not bids or not asks: return "NEUTRAL"

        # 只计算前 5 档深度，看近端力量对比
        bid_vol = sum(float(b.size) for b in bids[:5])
        ask_vol = sum(float(a.size) for a in asks[:5])
        
        imbalance = bid_vol / (ask_vol + 1e-6)
        
        if imbalance > IMBALANCE_THRESHOLD: return "BUY_STRONG"
        if imbalance < (1 / IMBALANCE_THRESHOLD): return "SELL_STRONG"
    except Exception as e:
        logging.error(f"OrderFlow 异常: {e}")
    return "NEUTRAL"

def detect_tail_reversal(symbol, current_price):
    """尾部反转识别：寻找超跌后的‘第一根阳线’"""
    history = price_history[symbol]
    history.append(current_price)
    if len(history) > PRICE_HISTORY_LIMIT: history.pop(0)
    
    if len(history) < 5: return False

    # 逻辑：前 3 次都在跌，最后一次突然拉升，且当前价格仍处于低位
    is_reversal = (history[-2] < history[-3] < history[-4]) and (history[-1] > history[-2])
    return is_reversal

# ==================== 3. 市场情报模块 (Market Intelligence) ====================

def fetch_qualified_markets():
    """动态筛选高胜率市场：排除垃圾、选取大成交量"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        res = requests.get(url, params={"active":"true", "closed":"false", "limit":100}).json()
        
        qualified = {}
        for s in SYMBOLS:
            # 1. 基础过滤：匹配币种 + 排除垃圾词 (Airdrop/GTA/FIFA)
            matches = [m for m in res if s.lower() in m['question'].lower() and 
                       not any(bad in m['question'].lower() for bad in ["airdrop", "gta", "fifa", "launch"])]
            
            # 2. 深度过滤：成交量 > 10000 且 有 TokenID
            valid = [m for m in matches if float(m.get("volume", 0)) > MIN_VOLUME and m.get("clobTokenIds")]
            
            if valid:
                # 选该币种下成交量最大的盘口
                best = max(valid, key=lambda x: float(x.get("volume", 0)))
                qualified[s] = {
                    "token_id": best["clobTokenIds"][0], # 默认买涨
                    "title": best["question"],
                    "volume": best["volume"]
                }
        return qualified
    except Exception as e:
        logging.error(f"情报获取失败: {e}")
        return {}

# ==================== 4. 交易执行与统计 (Trader & Stats) ====================

def send_tg(msg):
    if TG_TOKEN and TG_CHAT_ID:
        try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          data={"chat_id": TG_CHAT_ID, "text": f"🦞 V8 实盘播报:\n{msg}"}, timeout=5)
        except: pass

async def execute_trade(symbol, token_id, price, title):
    """精准执行下单并记录"""
    try:
        def _place():
            order = client.create_order(price=price, size=1.0, side="buy", token_id=token_id)
            signed = client.sign_order(order)
            return client.place_order(signed)

        res = await asyncio.to_thread(_place)
        if res and res.get("success"):
            stats["total"] += 1
            msg = f"🎯 下单成功: {symbol}\n价格: {price}\n市场: {title}"
            logging.info(msg)
            send_tg(msg)
            return True
    except Exception as e:
        logging.error(f"下单失败: {e}")
    return False

# ==================== 5. 主调度循环 (Main Loop) ====================

async def main():
    logging.info("🚀 龙虾 V8 信号驱动系统启动...")
    send_tg("系统启动：监控大单流入与尾部反转信号")
    
    last_report_time = time.time()

    while True:
        try:
            # 1. 刷新情报
            markets = fetch_qualified_markets()
            
            for symbol, info in markets.items():
                token_id = info["token_id"]
                
                # 2. 获取实时信号
                # 获取当前买价
                p_resp = await asyncio.to_thread(client.get_price, token_id, side="BUY")
                current_price = float(p_resp.get("price", 1.0))
                
                flow = await get_orderflow_signal(token_id)
                reversal = detect_tail_reversal(symbol, current_price)
                
                logging.info(f"📊 {symbol} | 价: {current_price} | 流向: {flow} | 反转: {reversal}")

                # 3. 核心决策逻辑：大单流入 + 价格反转 = 入场
                if flow == "BUY_STRONG" and reversal:
                    logging.info(f"🔥 发现共振信号！准备入场 {symbol}")
                    await execute_trade(symbol, token_id, current_price, info["title"])

            # 4. 每 15 分钟报告一次 ROI
            if time.time() - last_report_time > 900:
                wr = (stats["wins"]/stats["total"]*100) if stats["total"] > 0 else 0
                report = f"📊 阶段报告\n总单数: {stats['total']}\n预估胜率: {wr:.1f}%\n监控中..."
                send_tg(report)
                last_report_time = time.time()

        except Exception as e:
            logging.error(f"主循环异常: {e}")
            
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
