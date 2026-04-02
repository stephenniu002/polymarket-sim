import os
import asyncio
import time
import json
import websockets
from dotenv import load_dotenv

# --- 依赖 ---
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs


# =========================
# 初始化
# =========================
load_dotenv()

PK = os.getenv("PRIVATE_KEY")
if not PK:
    raise ValueError("❌ 请设置 PRIVATE_KEY")

BET_SIZE = float(os.getenv("BET_SIZE", 5))


# =========================
# Binance 实时价格
# =========================
class BinanceWS:
    def __init__(self):
        self.price = {}

    async def run(self):
        url = "wss://stream.binance.com:9443/ws/ethusdt@trade"

        while True:
            try:
                async with websockets.connect(url) as ws:
                    while True:
                        msg = json.loads(await ws.recv())
                        self.price["ETHUSDT"] = float(msg["p"])
            except:
                await asyncio.sleep(2)

    def get(self, symbol="ETHUSDT"):
        return self.price.get(symbol)


# =========================
# 主系统
# =========================
class ApexV7Lite:

    def __init__(self):
        self.client = ClobClient(
            "https://clob.polymarket.com",
            key=PK,
            chain_id=137
        )

        self.binance = BinanceWS()

        self.markets = {}
        self.poly_price = {}

        self.last_trade = 0

    # ---------------------
    # 市场发现（简化）
    # ---------------------
    async def discover(self):
        while True:
            try:
                resp = await asyncio.to_thread(self.client.get_markets)
                markets = resp.get("data", [])

                for m in markets:
                    q = (m.get("question") or "").lower()

                    if "ethereum" in q and "price" in q:
                        mid = m["condition_id"]

                        if mid not in self.markets:
                            self.markets[mid] = m
                            print("🎯 发现市场:", m["question"])

            except Exception as e:
                print("❌ discover error:", e)

            await asyncio.sleep(60)

    # ---------------------
    # Spot Lag（极简）
    # ---------------------
    def check_spot_lag(self, mid):
        spot = self.binance.get()
        poly = self.poly_price.get(mid)

        if not spot or not poly:
            return None

        if spot > poly * 1.0015:
            return "YES"

        if spot < poly * 0.9985:
            return "NO"

        return None

    # ---------------------
    # 风控
    # ---------------------
    def can_trade(self):
        return time.time() - self.last_trade > 60

    # ---------------------
    # 下单
    # ---------------------
    async def fire(self, token_id, side):
        try:
            ob = await asyncio.to_thread(
                self.client.get_orderbook,
                token_id
            )

            bid = float(ob["bids"][0]["price"])
            ask = float(ob["asks"][0]["price"])

            if side == "YES":
                price = min(ask, 0.49)
            else:
                price = max(bid, 0.51)

            order = OrderArgs(
                price=price,
                size=BET_SIZE,
                side="buy",
                token_id=token_id
            )

            o = await asyncio.to_thread(self.client.create_order, order)
            signed = self.client.sign_order(o)

            resp = await asyncio.to_thread(
                self.client.submit_order,
                signed
            )

            print("💰 下单成功:", resp)

            self.last_trade = time.time()

        except Exception as e:
            print("❌ 下单失败:", e)

    # ---------------------
    # 狙击逻辑
    # ---------------------
    async def sniper(self):
        while True:
            now = int(time.time())
            rem = now % 300
            tte = 300 - rem

            # 最后10秒
            if tte <= 10:

                for mid, m in self.markets.items():

                    if not self.can_trade():
                        continue

                    try:
                        token = m["tokens"][0]
                        token_id = token.get("tokenId") or token.get("token_id")

                        ob = await asyncio.to_thread(
                            self.client.get_orderbook,
                            token_id
                        )

                        ask = float(ob["asks"][0]["price"])
                        self.poly_price[mid] = ask

                        sig = self.check_spot_lag(mid)

                        if sig:
                            print(f"🚀 信号: {sig}")
                            await self.fire(token_id, sig)

                    except:
                        continue

            await asyncio.sleep(0.5)

    # ---------------------
    # 启动
    # ---------------------
    async def run(self):
        print("🚀 Apex V7 Lite 启动")

        await asyncio.gather(
            self.binance.run(),
            self.discover(),
            self.sniper()
        )


# =========================
# 启动
# =========================
if __name__ == "__main__":
    bot = ApexV7Lite()
    asyncio.run(bot.run())
