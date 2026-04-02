import os
import sys
import asyncio
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# --- 1. 环境与路径补丁 ---
sys.path.insert(0, os.path.join(os.getcwd(), ".venv", "lib", "python3.11", "site-packages"))
load_dotenv()

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [LOBSTER-V5.8] %(message)s')
logger = logging.getLogger(__name__)

# --- 3. 配置常量 ---
PK = os.getenv("PK") or os.getenv("PRIVATE_KEY")
BET_SIZE = float(os.getenv("BET_SIZE", 2.0))      # 建议初次 7 币同做设小点
SHADOW_LIMIT = 5                                  # 连亏 5 次开启影子模式
OFI_THRESHOLD = 2.2                               # 订单流压制倍数
STALL_THRESHOLD = 0.003                           # 价格停滞阈值 (0.3美分)
TARGET_COINS = ["btc", "eth", "sol", "xrp", "doge", "bnb", "hype"] # 7大目标

class LobsterLegion:
    def __init__(self):
        if not PK: raise ValueError("❌ 缺失私钥 PK")
        self.client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        self.hunts = {}          # 活跃市场池
        self.last_prices = {}    # 价格缓存，用于判断停滞
        self.loss_count = 0      # 连亏计数
        self.is_shadow = False   # 影子模式开关

    def is_stalling(self, mid, current_price):
        """核心：判断价格是否在高位/低位涨不动了"""
        last = self.last_prices.get(mid)
        self.last_prices[mid] = current_price
        if last is None: return False
        return abs(current_price - last) < STALL_THRESHOLD

    async def discovery_loop(self):
        """扫描全场，自动锁定 7 个币的 5min 盘口"""
        logger.info(f"📡 军团扫描启动：目标币种 {TARGET_COINS}")
        while True:
            try:
                # 扫描前两页，确保覆盖所有币种
                all_data = []
                for cursor in ["MA==", "MTAw"]:
                    resp = await asyncio.to_thread(self.client.get_markets, next_cursor=cursor)
                    all_data.extend(resp.get("data", []) if isinstance(resp, dict) else resp)
                
                for m in all_data:
                    if not m.get('active'): continue
                    q = str(m.get('question', '')).lower()
                    
                    # 匹配逻辑：标题包含目标币种 + 包含 price/above/5-min
                    is_target = any(coin in q for coin in TARGET_COINS)
                    is_5min = any(k in q for k in ["price at", "above", "5-minute", "up-or-down"])
                    
                    if is_target and is_5min:
                        mid = m.get('condition_id')
                        if mid not in self.hunts:
                            self.hunts[mid] = {
                                "q": m.get('question'),
                                "tokens": m.get('tokens'),
                                "end": m.get('end_date_iso', '2099-12-31')
                            }
                            logger.info(f"🎯 军团锁定目标: {m.get('question')[:40]}...")

                # 清理过期目标
                now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}
                logger.info(f"📊 当前监听池: {len(self.hunts)} 个市场")

            except Exception as e:
                logger.error(f"📡 扫描异常: {e}")
            await asyncio.sleep(45)

    async def sniper_loop(self):
        """反转狙击逻辑：检测过热 -> 等待 -> 确认停滞 -> 反向开火"""
        logger.info("⚔️ 狙击手就位：等待 5min 周期末尾信号...")
        while True:
            now = int(time.time())
            rem = now % 300 
            
            # 锁定每个周期的最后 25 秒（2:49:35 - 2:49:58）
            if 275 <= rem <= 298:
                # 风控自检
                if not self.is_shadow and self.loss_count >= SHADOW_LIMIT:
                    self.is_shadow = True
                    logger.warning(f"🚨 [风控] 连亏达标，已切换至影子模式！")

                for mid, data in list(self.hunts.items()):
                    try:
                        # 1. 获取盘口 (Orderbook)
                        t_yes = data['tokens'][0]
                        tid = t_yes.get('tokenId') or t_yes.get('token_id')
                        ob = await asyncio.to_thread(self.client.get_orderbook, tid)
                        
                        bids, asks = ob.get("bids", []), ob.get("asks", [])
                        if not bids or not asks: continue
                        
                        b_vol = sum([float(x['size']) for x in bids[:3]])
                        a_vol = sum([float(x['size']) for x in asks[:3]])
                        mid_p = (float(bids[0]['price']) + float(asks[0]['price'])) / 2

                        # 2. 逻辑判定：买盘极强 (YES 追多) -> 反向买 NO
                        if b_vol > a_vol * OFI_THRESHOLD:
                            logger.info(f"⚠️ {data['q'][:15]} 多头过热，等待反转信号...")
                            await asyncio.sleep(3) # 关键：等待 3 秒
                            
                            if self.is_stalling(mid, mid_p):
                                logger.info(f"🔥 [反转确认] 买入 NO | {data['q'][:20]}")
                                await self.execute_trade(data['tokens'][1], "NO")
                                await asyncio.sleep(10) # 冷却防止同币重发

                        # 3. 逻辑判定：卖盘极强 (NO 砸盘) -> 反向买 YES
                        elif a_vol > b_vol * OFI_THRESHOLD:
                            logger.info(f"⚠️ {data['q'][:15]} 空头过热，等待反转信号...")
                            await asyncio.sleep(3)
                            
                            if self.is_stalling(mid, mid_p):
                                logger.info(f"🔥 [反转确认] 买入 YES | {data['q'][:20]}")
                                await self.execute_trade(data['tokens'][0], "YES")
                                await asyncio.sleep(10)
                                
                    except Exception as e:
                        continue
                await asyncio.sleep(1) # 循环内微调
            else:
                await asyncio.sleep(1) # 非末尾期低频轮询

    async def execute_trade(self, t_data, side):
        """执行下单：区分影子与实盘"""
        if self.is_shadow:
            logger.info(f"🧪 [影子模拟] {side} 信号达成，观察但不下单。")
            # 影子模式下模拟一次成功，尝试重置连亏
            self.loss_count = 0
            self.is_shadow = False
            return

        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            # 价格微进场：0.52/0.48 确保反转时能成交
            price = 0.52 if side == "YES" else 0.48
            
            order_p = OrderArgs(price=price, size=BET_SIZE, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            
            if resp.get("success"):
                logger.info(f"✅ [实盘成交] {side} | ID: {resp.get('order_id')}")
                self.loss_count = 0
            else:
                logger.error(f"❌ [下单失败] {resp}")
                self.loss_count += 1
        except Exception as e:
            logger.error(f"❌ [执行异常] {e}")
            self.loss_count += 1

    async def run(self):
        logger.info(f"🚀 Lobster Legion V5.8 启动！")
        logger.info(f"💰 初始单笔额度: {BET_SIZE} USDC | 目标池: {TARGET_COINS}")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(LobsterLegion().run())
    except KeyboardInterrupt:
        pass
