import os
import asyncio
import requests
import time
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

BASE = "https://clob.polymarket.com"
TARGET_PROFIT = 1.0       # 每5分钟目标收益 $1
SCAN_LIMIT = 50            # 扫描前50个市场
MAX_COINS = 7              # 支持同时计算7个币种
REPORT_INTERVAL = 300      # 每5分钟汇报一次
EDGE_THRESHOLD = 0.005     # Edge 最小触发值
MIN_EDGE_STOP = 0.002      # Edge 过低暂停交易
ORDER_SIZE = 1.0           # 每笔订单默认 1 USDC（备用）

profit = 0
trades = 0
last_report = time.time()

# ================= RPC 连接 =================
async def get_w3():
    while True:
        try:
            rpc = os.getenv("ALCHEMY_RPC_URL")
            if not rpc:
                raise Exception("❌ ALCHEMY_RPC_URL 未配置")
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
            w3.eth.get_block_number()
            print("✅ RPC连接成功")
            return w3
        except Exception as e:
            print(f"❌ RPC错误: {e}")
            await asyncio.sleep(5)

# ================= 工具函数 =================
def get_markets():
    try:
        r = requests.get(f"{BASE}/sampling-markets", timeout=10).json()
        return r if isinstance(r, list) else r.get("data", [])
    except:
        return []

def get_book(token_id):
    try:
        r = requests.get(f"{BASE}/book?token_id={token_id}", timeout=5).json()
        bids = r.get("bids", [])
        asks = r.get("asks", [])
        bid = float(bids[0]["price"]) if bids else 0
        ask = float(asks[0]["price"]) if asks else 1
        return bid, ask
    except:
        return 0, 1

def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=5
            )
        except:
            pass

# ================= 动态资金计算 =================
def calc_funds(p_yes, p_no):
    edge = 1 - (p_yes + p_no)
    if edge < MIN_EDGE_STOP:
        return 0, 0, edge  # Edge过低暂停
    total_invest = TARGET_PROFIT / max(edge, EDGE_THRESHOLD)
    i_yes = total_invest * p_no / (p_yes + p_no)
    i_no = total_invest - i_yes
    return i_yes, i_no, edge

# ================= 主循环 =================
async def main():
    global profit, trades, last_report

    print("🚀 Lobster REAL PROFIT 启动")
    send_tg("🟢 Lobster 机器人已上线，开始监控前50个市场...")

    # 初始化
    w3 = await get_w3()
    client = ClobClient(host=BASE, key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            markets = get_markets()[:SCAN_LIMIT]

            for m in markets[:MAX_COINS]:
                question = m.get("question", "未知市场")
                tokens = m.get("tokens", [])
                if len(tokens) < 2:
                    continue

                y_id, n_id = tokens[0]["token_id"], tokens[1]["token_id"]
                y_bid, y_ask = get_book(y_id)
                n_bid, n_ask = get_book(n_id)

                i_yes, i_no, edge = calc_funds(y_ask, n_ask)

                if edge >= EDGE_THRESHOLD:
                    print(f"💰 Edge={edge:.4f} | 市场: {question[:30]} | 投入: YES {i_yes:.2f}, NO {i_no:.2f}")
                    try:
                        # 并发下单，吃单模式
                        await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask + 0.001, 3),
                                "size": i_yes,
                                "side": "BUY",
                                "token_id": y_id
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(n_ask + 0.001, 3),
                                "size": i_no,
                                "side": "BUY",
                                "token_id": n_id
                            })
                        )
                        profit += edge * (i_yes + i_no)
                        trades += 1
                        send_tg(f"🔥 套利成交!\n利润: +{edge*(i_yes+i_no):.4f} USDC\n市场: {question[:30]}")

                    except Exception as e:
                        print(f"⚠️ 下单失败: {e}")
                        if "insufficient" in str(e).lower():
                            await asyncio.sleep(60)  # 资金不足，休息一分钟

                await asyncio.sleep(0.3)

            # ================= 定时汇报 =================
            if time.time() - last_report > REPORT_INTERVAL:
                report_msg = (
                    f"📊 Lobster 运行汇报\n"
                    f"━━━━━━━━━━━━\n"
                    f"📈 成交次数: {trades}\n"
                    f"💰 累计利润: {profit:.4f} USDC\n"
                    f"⛽ 系统正常运行中..."
                )
                send_tg(report_msg)
                last_report = time.time()

            await asyncio.sleep(5)

        except Exception as e:
            print(f"💥 全局错误: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
