import os
import asyncio
import requests
import time
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

BASE = "https://clob.polymarket.com"

ORDER_SIZE = 1.0
REPORT_INTERVAL = 300

profit = 0
trades = 0
last_report = time.time()

# ================= RPC（彻底修复版） =================
async def get_w3():
    while True:
        try:
            rpc = os.getenv("ALCHEMY_RPC_URL")

            if not rpc:
                raise Exception("❌ ALCHEMY_RPC_URL 未配置")

            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))

            # 强制检测连接
            w3.eth.get_block_number()

            print("✅ RPC连接成功")
            return w3

        except Exception as e:
            print("❌ RPC错误:", e)
            await asyncio.sleep(5)

# ================= 工具 =================
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

# ================= 主逻辑 =================
async def main():
    global profit, trades, last_report

    print("🚀 Lobster 稳定版启动")

    # ✅ 初始化 RPC
    w3 = await get_w3()

    # ✅ 初始化交易客户端
    client = ClobClient(host=BASE, key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            markets = get_markets()[:8]

            for m in markets:
                tokens = m.get("tokens", [])
                if len(tokens) < 2:
                    continue

                y = tokens[0]["token_id"]
                n = tokens[1]["token_id"]

                y_bid, y_ask = get_book(y)
                n_bid, n_ask = get_book(n)

                total = y_ask + n_ask

                print(f"📈 {y_ask:.3f} + {n_ask:.3f} = {total:.3f}")

                # ================= 套利 =================
                if 0.2 < total < 0.97:
                    try:
                        await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask + 0.002, 3),
                                "size": ORDER_SIZE,
                                "side": "BUY",
                                "token_id": y
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(n_ask + 0.002, 3),
                                "size": ORDER_SIZE,
                                "side": "BUY",
                                "token_id": n
                            })
                        )

                        p = (1 - total) * ORDER_SIZE
                        profit += p
                        trades += 1

                        send_tg(f"💰 套利成功 +{p:.3f}")

                    except Exception as e:
                        print("套利失败:", e)

                # ================= 做市 =================
                spread = y_ask - y_bid

                if 0.01 < spread < 0.08:
                    try:
                        await asyncio.gather(
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_bid + 0.001, 3),
                                "size": ORDER_SIZE,
                                "side": "BUY",
                                "token_id": y,
                                "expiration": int(time.time()) + 60
                            }),
                            asyncio.to_thread(client.post_order, {
                                "price": round(y_ask - 0.001, 3),
                                "size": ORDER_SIZE,
                                "side": "SELL",
                                "token_id": y,
                                "expiration": int(time.time()) + 60
                            })
                        )
                    except:
                        pass

                # ================= 趋势对冲 =================
                if total > 1.97:
                    try:
                        await asyncio.to_thread(client.post_order, {
                            "price": n_ask,
                            "size": 0.5,
                            "side": "BUY",
                            "token_id": n
                        })
                    except:
                        pass

                await asyncio.sleep(0.5)

            # ================= 电报汇报 =================
            if time.time() - last_report > REPORT_INTERVAL:
                msg = f"""
📊 Lobster 运行报告
📈 交易次数: {trades}
💰 累计利润: {profit:.2f} USDC
"""
                send_tg(msg)
                last_report = time.time()

            await asyncio.sleep(10)

        except Exception as e:
            print("💥 主循环错误:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
