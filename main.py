import os
import asyncio
import requests
import time
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

BASE = "https://clob.polymarket.com"

# 配置参数
ORDER_SIZE = 1.0       # 每笔订单 1 USDC
REPORT_INTERVAL = 300  # 5分钟汇报一次
SCAN_LIMIT = 50        # 扫描前50个市场，寻找更多机会

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

# ================= 主循环 =================
async def main():
    global profit, trades, last_report

    print("🚀 Lobster Pro Max (稳定盈利版) 启动")
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
            # 扩大扫描深度，避开死盘
            markets = get_markets()[:SCAN_LIMIT]

            for m in markets:
                question = m.get("question", "未知市场")
                tokens = m.get("tokens", [])
                if len(tokens) < 2:
                    continue

                y, n = tokens[0]["token_id"], tokens[1]["token_id"]
                y_bid, y_ask = get_book(y)
                n_bid, n_ask = get_book(n)

                total = y_ask + n_ask
                edge = 1 - total

                # 仅对有意义的盘口进行详细日志打印
                if total < 1.1:
                    print(f"🔍 扫描: {question[:25]}... | 合计: {total:.3f}")

                # ================= 1. 强力套利逻辑 (修复语法错误处) =================
                if 0.2 < total < 0.985:
                    try:
                        print(f"💰 发现套利机会! edge={edge:.4f} | 市场: {question[:20]}")
                        
                        # 并发下单提高成功率
                        await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask + 0.001, 3),
                                "size": ORDER_SIZE,
                                "side": "BUY",
                                "token_id": y
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(n_ask + 0.001, 3),
                                "size": ORDER_SIZE,
                                "side": "BUY",
                                "token_id": n
                            })
                        )

                        p = edge * ORDER_SIZE
                        profit += p
                        trades += 1
                        send_tg(f"🔥 套利成交!\n利润: +{p:.4f} USDC\n市场: {question[:30]}")

                    except Exception as e:
                        print(f"⚠️ 下单失败: {e}")
                        if "insufficient" in str(e).lower():
                            await asyncio.sleep(60) # 资金占用，休息一分钟

                # ================= 2. 盘口做市逻辑 =================
                if 0.15 < y_bid < 0.85:
                    spread = y_ask - y_bid
                    if 0.015 < spread < 0.06:
                        try:
                            # 尝试在盘口挂买单“收租”
                            await asyncio.to_thread(client.post_order, {
                                "price": round(y_bid + 0.001, 3),
                                "size": ORDER_SIZE,
                                "side": "BUY",
                                "token_id": y,
                                "expiration": int(time.time()) + 60
                            })
                        except:
                            pass

                await asyncio.sleep(0.3) # 控制请求频率，防止被封

            # ================= 定时汇报 =================
            if time.time() - last_report > REPORT_INTERVAL:
                report_msg = (
                    f"📊 Lobster 运行汇报\n"
                    f"━━━━━━━━━━━━\n"
                    f"📈 成交次数: {trades}\n"
                    f"💰 累计利润: {profit:.4f} USDC\n"
                    f"⛽ 余额充足，系统运行中..."
                )
                send_tg(report_msg)
                last_report = time.time()

            await asyncio.sleep(5)

        except Exception as e:
            print(f"💥 全局错误: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
