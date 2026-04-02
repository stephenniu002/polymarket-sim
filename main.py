import os
import sys
import asyncio
import logging
import time
import json
from dotenv import load_dotenv

# ===== 环境 =====
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.3] %(message)s')
logger = logging.getLogger(__name__)


# ===== 导入 =====
try:
    from py_clob_client.client import ClobClient
except:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient


# ===== 主类 =====
class ApexPredator:

    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk:
            raise ValueError("❌ 缺失 PRIVATE_KEY")

        self.client = ClobClient(
            host="https://clob.polymarket.com",
            key=pk,
            chain_id=137
        )

        self.hunts = {}               # 市场池
        self.signal_buffer = {}       # 连续信号
        self.last_ob = {}             # 上一帧盘口
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))

        self.last_trade_time = 0      # 防止连打

    # =========================
    # 📡 自动发现市场
    # =========================
    async def discovery_loop(self):
        logger.info("📡 Discovery 启动")

        while True:
            try:
                raw = await asyncio.to_thread(self.client.get_markets)

                if isinstance(raw, str):
                    raw = json.loads(raw)

                markets = raw.get("data", []) if isinstance(raw, dict) else raw

                new_count = 0

                for m in markets:
                    if not isinstance(m, dict):
                        continue

                    desc = str(m.get("description", "")).lower()

                    if "5-minute" in desc:
                        mid = m.get("condition_id")

                        if mid and mid not in self.hunts:
                            self.hunts[mid] = {
                                "q": m.get("question"),
                                "tokens": m.get("tokens")
                            }
                            new_count += 1

                if new_count:
                    logger.info(f"🎯 新市场: {new_count} | 总: {len(self.hunts)}")

            except Exception as e:
                logger.error(f"❌ Discovery error: {e}")

            await asyncio.sleep(60)

    # =========================
    # 🧠 信号确认（关键）
    # =========================
    def confirm_signal(self, mid, sig):
        buf = self.signal_buffer.setdefault(mid, [])
        buf.append(sig)

        if len(buf) > 3:
            buf.pop(0)

        return len(buf) == 3 and all(s == sig for s in buf)

    # =========================
    # 🐋 假单过滤
    # =========================
    def stable_ob(self, mid, b, a):
        prev = self.last_ob.get(mid)
        self.last_ob[mid] = (b, a)

        if not prev:
            return True

        pb, pa = prev

        if abs(b - pb) > 500 or abs(a - pa) > 500:
            return False

        return True

    # =========================
    # 💰 动态仓位
    # =========================
    def get_size(self):
        # 简化版（后面可接真实胜率）
        return self.bet_size

    # =========================
    # 🚀 下单
    # =========================
    async def fire_order(self, token_id, side):
        try:
            size = self.get_size()
            price = 0.52 if side == "YES" else 0.48

            logger.info(f"🔥 下单 {side} size={size} price={price}")

            order = await asyncio.to_thread(
                self.client.create_order,
                token_id=token_id,
                price=price,
                size=size,
                side="buy"
            )

            signed = self.client.sign_order(order)

            res = await asyncio.to_thread(
                self.client.submit_order,
                signed
            )

            logger.info(f"✅ 成功: {res}")

            self.last_trade_time = time.time()

        except Exception as e:
            logger.error(f"❌ 下单失败: {e}")

    # =========================
    # ⚔️ 狙击核心
    # =========================
    async def sniper_loop(self):
        logger.info("⚔️ Sniper 启动")

        while True:
            now = int(time.time())
            rem = now % 300

            # 🔥 尾盘 7 秒窗口
            if 288 <= rem <= 295:

                # 防止连续下单
                if time.time() - self.last_trade_time < 20:
                    await asyncio.sleep(1)
                    continue

                fired = False

                for mid, data in list(self.hunts.items()):

                    if fired:
                        break

                    try:
                        tokens = data.get("tokens", [])
                        if not tokens:
                            continue

                        y = tokens[0].get("tokenId")
                        n = tokens[1].get("tokenId")

                        ob = await asyncio.to_thread(
                            self.client.get_orderbook,
                            y
                        )

                        bids = ob.get("bids", [])[:3]
                        asks = ob.get("asks", [])[:3]

                        b_vol = sum(float(x["size"]) for x in bids) if bids else 0
                        a_vol = sum(float(x["size"]) for x in asks) if asks else 0

                        if not self.stable_ob(mid, b_vol, a_vol):
                            continue

                        # ===== 信号 =====
                        if b_vol > a_vol * 2.5:
                            if self.confirm_signal(mid, "YES"):
                                logger.info(f"📈 信号 YES {data['q'][:30]}")
                                await self.fire_order(y, "YES")
                                fired = True

                        elif a_vol > b_vol * 2.5:
                            if self.confirm_signal(mid, "NO"):
                                logger.info(f"📉 信号 NO {data['q'][:30]}")
                                await self.fire_order(n, "NO")
                                fired = True

                    except Exception as e:
                        logger.debug(f"跳过: {e}")

            await asyncio.sleep(1)

    # =========================
    # 💓 心跳（Railway）
    # =========================
    async def heartbeat(self):
        while True:
            logger.info("💓 alive")
            await asyncio.sleep(60)

    # =========================
    # 🚀 启动
    # =========================
    async def run(self):
        logger.info("🚀 APEX V5.3 启动")
        await asyncio.gather(
            self.discovery_loop(),
            self.sniper_loop(),
            self.heartbeat()
        )


# ===== 启动 =====
if __name__ == "__main__":
    bot = ApexPredator()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        pass
