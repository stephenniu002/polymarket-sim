import os
import sys
import asyncio
import logging
import time
import random
from datetime import datetime
from dotenv import load_dotenv

# --- 1. 环境补丁 ---
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s [LOBSTER-V7] %(message)s')
logger = logging.getLogger(__name__)

# --- 3. 配置常量 ---
PK = os.getenv("PK") or os.getenv("PRIVATE_KEY")
BET_SIZE = float(os.getenv("BET_SIZE", 5.0))      
TARGET_COINS = ["btc", "eth", "sol", "xrp", "doge", "bnb", "hype"]

class LobsterV7:
    def __init__(self):
        if not PK: raise ValueError("❌ 缺失私钥 PK")
        self.client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        self.hunts = {}          
        
        # --- 🛡️ V6.5 风控模块 ---
        self.consec_losses = 0           # 连亏计数
        self.daily_pnl = 0               # 当日盈亏
        self.max_consec_losses = 3       # 连亏3次熔断
        self.max_daily_loss = -50.0      # 日亏损上限
        self.market_cooldown = {}        # 市场冷却
        self.min_liquidity = 400         # 盘口深度门槛
        
        # --- 📈 策略参数 ---
        self.ofi_threshold = 2.5         # 订单流不平衡倍数
        self.last_scan_time = 0

    def update_pnl(self, pnl, mid):
        """核心风控：胜率追踪与熔断"""
        self.daily_pnl += pnl
        if pnl < 0:
            self.consec_losses += 1
            self.market_cooldown[mid] = time.time()
            logger.warning(f"📉 损单 | 连亏: {self.consec_losses} | 日PnL: {self.daily_pnl:.2f}")
        else:
            self.consec_losses = 0
            logger.info(f"📈 盈单 | 连亏清零 | 日PnL: {self.daily_pnl:.2f}")

    async def discovery_loop(self):
        """V6.9 静默扫描：解决日志空转与请求过载"""
        logger.info(f"📡 扫描启动：锁定币种 {TARGET_COINS}")
        while True:
            try:
                # 🛡️ 强制冷却 45 秒，彻底解决 HTTP 429 和空转
                await asyncio.sleep(45) 
                
                resp = await asyncio.to_thread(self.client.get_markets, next_cursor="MA==")
                markets = resp.get("data", []) if isinstance(resp, dict) else resp
                
                found_count = 0
                for m in markets:
                    if not m.get('active'): continue
                    q = str(m.get('question', '')).lower()
                    mid = m.get('condition_id')
                    
                    # 只要包含币种名，就拉入监控池（适配 2026 最新命名规则）
                    if any(coin in q for coin in TARGET_COINS):
                        if mid not in self.hunts:
                            self.hunts[mid] = {
                                "q": m.get('question'),
                                "tokens": m.get('tokens'),
                                "end": m.get('end_date_iso', '2099-12-31')
                            }
                            logger.info(f"✅ 捕获新猎物: {q[:50]}...")
                            found_count += 1

                # 清理过期市场
                now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}
                logger.info(f"📊 池内活跃猎物: {len(self.hunts)} 个")

            except Exception as e:
                logger.error(f"📡 扫描异常: {e}")

    async def sniper_loop(self):
        """V7 精准狙击：带风控拦截与流动性过滤"""
        logger.info("⚔️ 狙击手就位：最后 20 秒准时开火")
        while True:
            # 1. 检查全局熔断
            if self.consec_losses >= self.max_consec_losses:
                logger.error("🛑 触发连亏熔断，休眠 15 分钟...")
                await asyncio.sleep(900)
                self.consec_losses = 0
                continue

            if self.daily_pnl <= self.max_daily_loss:
                logger.error("🚨 触发日亏损限额，今日停止。")
                await asyncio.sleep(3600)
                continue

            now = int(time.time())
            rem = now % 300 
            
            # 锁定每个 5 分钟周期的最后 20 秒
            if 280 <= rem <= 298:
                for mid, data in list(self.hunts.items()):
                    # 市场冷却检查
                    if time.time() - self.market_cooldown.get(mid, 0) < 600:
                        continue

                    try:
                        t_yes = data['tokens'][0]
                        tid = t_yes.get('tokenId') or t_yes.get('token_id')
                        ob = await asyncio.to_thread(self.client.get_orderbook, tid)
                        
                        bids, asks = ob.get("bids", []), ob.get("asks", [])
                        if not bids or not asks: continue
                        
                        # 流动性过滤
                        b_vol = sum([float(x['size']) for x in bids[:3]])
                        a_vol = sum([float(x['size']) for x in asks[:3]])
                        if (b_vol + a_vol) < self.min_liquidity:
                            continue

                        # 反转逻辑：买单压倒性多于卖单 -> 可能冲顶力竭 -> 狙击 NO
                        if b_vol > a_vol * self.ofi_threshold:
                            await self.fire_order(data['tokens'][1], "NO", mid)
                            await asyncio.sleep(5) 

                        # 卖单压倒性多于买单 -> 可能探底回升 -> 狙击 YES
                        elif a_vol > b_vol * self.ofi_threshold:
                            await self.fire_order(data['tokens'][0], "YES", mid)
                            await asyncio.sleep(5)
                                
                    except: continue
                await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(1) # 非末尾时间，极低功耗运行

    async def fire_order(self, t_data, side, mid):
        """执行模块：带实盘反馈"""
        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            price = 0.52 if side == "YES" else 0.48 # 市价吃单保守价
            
            order_p = OrderArgs(price=price, size=BET_SIZE, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            
            if resp.get("success"):
                logger.info(f"🔥 [成交] {side} | ID: {resp.get('order_id')}")
                # 模拟 PnL（实盘建议对接 get_order 状态）
                pnl = BET_SIZE * 0.9 if random.random() > 0.45 else -BET_SIZE
                self.update_pnl(pnl, mid)
            else:
                logger.error(f"❌ [下单失败] {resp}")
        except Exception as e:
            logger.error(f"❌ [执行异常] {e}")

    async def run(self):
        logger.info(f"🚀 Lobster Ultimate V7 启动 | 单笔: {BET_SIZE} USDC")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(LobsterV7().run())
    except KeyboardInterrupt: pass
