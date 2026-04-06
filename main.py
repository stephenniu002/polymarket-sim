import os
import asyncio
import requests
import time
import math
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 配置区 =================
BASE = "https://clob.polymarket.com"
MIN_ORDER_SIZE = 1.0       # 最小下单金额 (USDC)
MAX_ORDER_SIZE = 5.0       # 最大单笔限制（保护 10 USDC 本金）
EDGE_THRESHOLD = 0.015     # 触发阈值：Edge > 1.5% (即 Total < 0.985)
REPORT_INTERVAL = 300      # 5分钟固定汇报

profit = 0
trades = 0
last_report = time.time()

# ================= 动态资金分配算法 =================
def calculate_dynamic_size(edge):
    """
    根据利润空间(Edge)动态计算投入金额
    逻辑：Edge 每增加 1%，投入增加 1 USDC
    """
    # 基础投入 1.0 + (超额利润 * 放大倍数)
    suggested_size = MIN_ORDER_SIZE + (edge * 100 * 0.5) 
    return round(min(suggested_size, MAX_ORDER_SIZE), 2)

# ================= 工具函数 =================
def get_markets():
    try:
        r = requests.get(f"{BASE}/sampling-markets", timeout=10).json()
        return r if isinstance(r, list) else r.get("data", [])
    except: return []

def get_book(token_id):
    try:
        r = requests.get(f"{BASE}/book?token_id={token_id}", timeout=5).json()
        asks = r.get("asks", [])
        # 对冲套利只看 Ask (我们要买入)
        return float(asks[0]["price"]) if asks else 1.0
    except: return 1.0

def send_tg(msg):
    token, chat_id = os.getenv("TG_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                           json={"chat_id": chat_id, "text": msg}, timeout=5)
        except: pass

# ================= 主逻辑 =================
async def main():
    global profit, trades, last_report
    print("🚀 Lobster Pro Max 量化对冲版启动")
    
    client = ClobClient(host=BASE, key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            markets = get_markets()[:50] # 深度扫描 50 个市场

            for m in markets:
                tokens = m.get("tokens", [])
                if len(tokens) < 2: continue

                y_token, n_token = tokens[0]["token_id"], tokens[1]["token_id"]
                
                # 获取 YES 和 NO 的当前卖一价 (Ask)
                y_ask = get_book(y_token)
                n_ask = get_book(n_token)
                total_cost = y_ask + n_ask
                edge = 1 - total_cost

                # ================= 判定套利机会 =================
                if edge > EDGE_THRESHOLD:
                    dynamic_size = calculate_dynamic_size(edge)
                    
                    print(f"🔥 发现对冲机会! Edge: {edge:.4f} | 投入: {dynamic_size} USDC")
                    
                    try:
                        # 核心：YES 和 NO 同时买入，完成闭环对冲
                        await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask + 0.001, 3), # 微加价确保成交
                                "size": dynamic_size,
                                "side": "BUY",
                                "token_id": y_token
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(n_ask + 0.001, 3),
                                "size": dynamic_size,
                                "side": "BUY",
                                "token_id": n_token
                            })
                        )

                        # 计算本次确定性利润
                        current_p = edge * dynamic_size
                        profit += current_p
                        trades += 1
                        
                        send_tg(f"💰 对冲套利成功!\nEdge: {edge:.4f}\n投入: {dynamic_size} USDC\n预估锁定利润: +{current_p:.4f}")

                    except Exception as e:
                        print(f"❌ 下单失败: {e}")
                        if "insufficient" in str(e).lower():
                            await asyncio.sleep(60)

                await asyncio.sleep(0.2) # 高频扫描

            # ================= 5分钟固定汇报 =================
            if time.time() - last_report > REPORT_INTERVAL:
                send_tg(f"📊 Lobster 5min 定时报告\n累计锁定利润: {profit:.4f} USDC\n套利总次数: {trades}")
                last_report = time.time()

            await asyncio.sleep(3)

        except Exception as e:
            print(f"💥 循环错误: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
