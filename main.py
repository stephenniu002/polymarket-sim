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
BET_SIZE = float(os.getenv("BET_SIZE", 2.0))      # 单笔额度
SHADOW_LIMIT = 5                                  # 连亏影子模式阈值
OFI_THRESHOLD = 2.2                               # 订单流压制倍数
STALL_THRESHOLD = 0.003                           # 价格停滞阈值
TARGET_COINS = ["btc", "eth", "sol", "xrp", "doge", "bnb", "hype"] # 7大目标

class LobsterLegion:
    def __init__(self):
        if not PK: raise ValueError("❌ 缺失私钥 PK")
        self.client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        self.hunts = {}          
        self.last_prices = {}    
        self.loss_count = 0      
        self.is_shadow = False   

    def is_stalling(self, mid, current_price):
        """核心判断：检测价格是否在高位/低位力竭"""
        last = self.last_prices.get(mid)
        self.last_prices[mid] = current_price
        if last is None: return False
        return abs(current_price - last) < STALL_THRESHOLD

    async def discovery_loop(self):
        """深挖模式：自动捕捉 7 个币种的 5min 盘口"""
        logger.info(f"📡 军团扫描启动：锁定币种 {TARGET_COINS}")
        while True:
            try:
                all_data = []
                for cursor in ["MA==", "MTAw"]:
                    resp = await asyncio.to_thread(self.client.get_markets, next_cursor=cursor)
                    all_data.extend(resp.get("data", []) if isinstance(resp, dict) else resp)
                
                for m in all_data:
                    if not m.get('active'): continue
                    q = str(m.get('question', '')).lower()
                    
                    # 模糊匹配逻辑：币种 + 特征词
                    is_target = any(coin in q for coin in TARGET_COINS)
                    is_5min = any(k in q for k in ["price at", "above", "5-minute", "up-or-down", "at"])
                    
                    if is_target and is_5min:
                        mid = m.get('condition_id')
                        if mid not in self.hunts:
                            self.hunts[mid] = {
                                "q": m.get('question'),
                                "tokens": m.get('tokens'),
                                "end": m.get('end_date_iso', '2099-12-31')
                            }
                            logger.info(f"🎯 军团锁定目标: {m.get('question')[:45]}...")

                now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}
                logger.info(f"📊 监听池状态: {len(self.hunts)} 个活跃市场")

            except Exception as e:
                logger.error(f"📡 扫描异常: {e}")
            await asyncio.sleep(30) # 缩短扫描间隔，确保不漏单

    async def sniper_loop(self):
        """尾部反转狙击逻辑"""
        logger.info("⚔️ 狙击手就位：等待周期末尾信号...")
        while True:
            now = int(time.time())
            rem = now % 300 
            
            # 锁定最后 25 秒
            if 275 <= rem <= 298:
                if not self.is_shadow and self.loss_count >= SHADOW_LIMIT:
                    self.is_shadow = True
                    logger.warning("🚨 [风控] 连亏触发，开启影子模式。")

                for mid, data in list(self.hunts.items()):
                    try:
                        t_yes = data['tokens'][0]
                        tid = t_yes.get('tokenId') or t_yes.get('token_id')
                        ob = await asyncio.to_thread(self.client.get_orderbook, tid)
                        
                        bids, asks = ob.get("bids", []), ob.get("asks", [])
                        if not bids or not asks: continue
                        
                        b_vol = sum([float(x['size']) for x in bids[:3]])
                        a_vol = sum([float(x['size']) for x in asks[:3]])
                        mid_p = (float(bids[0]['price']) + float(asks[0]['price'])) / 2

                        # 逻辑：多头过热 -> 3秒确认 -> 买入 NO
                        if b_vol > a_vol * OFI_THRESHOLD:
                            logger.info(f"⚠️ {data['q'][:15]} 疑似冲顶，观察中...")
                            await asyncio.sleep(3)
                            if self.is_stalling(mid, mid_p):
                                logger.info(f"🔥 [反转信号确认] 买入 NO | {data['q'][:20]}")
                                await self.execute_trade(data['tokens'][1], "NO")
                                await asyncio.sleep(8) 

                        # 逻辑：空头过热 -> 3秒确认 -> 买入 YES
                        elif a_vol > b_vol * OFI_THRESHOLD:
                            logger.info(f"⚠️ {data['q'][:15]} 疑似探底，观察中...")
                            await asyncio.sleep(3)
                            if self.is_stalling(mid, mid_p):
                                logger.info(f"🔥 [反转信号确认] 买入 YES | {data['q'][:20]}")
                                await self.execute_trade(data['tokens'][0], "YES")
                                await asyncio.sleep(8)
                                
                    except: continue
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(1)

    async def execute_trade(self, t_data, side):
        """执行模块：支持影子与实盘切换"""
        if self.is_shadow:
            logger.info(f"🧪 [影子模拟] {side} 信号达成，观察中。")
            self.loss_count = 0
            self.is_shadow = False # 模拟成功后恢复实盘
            return

        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            price = 0.52 if side == "YES" else 0.48
            
            order_p = OrderArgs(price=price, size=BET_SIZE, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            
            if resp.get("success"):
                logger.info(f"✅ [实盘成交] {side} | {resp.get('order_id')}")
                self.loss_count = 0
            else:
                logger.error(f"❌ [下单失败] {resp}")
                self.loss_count += 1
        except Exception as e:
            logger.error(f"❌ [执行异常] {e}")
            self.loss_count += 1

    async def run(self):
        logger.info(f"🚀 Lobster Legion V5.8 启动！单笔 {BET_SIZE} USDC")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(LobsterLegion().run())
    except KeyboardInterrupt: pass
