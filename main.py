import os
import sys
import asyncio
import logging
import time
from dotenv import load_dotenv

# --- 1. 强制环境补丁 ---
sys.path.insert(0, os.path.join(os.getcwd(), ".venv", "lib", "python3.11", "site-packages"))

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 日志与配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.4] %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ApexPredatorV5_4:
    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk: raise ValueError("❌ 环境变量中缺少 PK")
        self.client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137)
        self.hunts = {}
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))

    async def discovery_loop(self):
        """核心改进：放宽匹配条件，只要包含币种和价格特征就抓取"""
        logger.info("📡 发现引擎：深度模糊扫描启动...")
        while True:
            try:
                # 显式使用异步线程处理同步请求
                resp = await asyncio.to_thread(self.client.get_markets)
                markets = resp.get("data", []) if isinstance(resp, dict) else resp
                
                # 扩大关键词库：Polymarket 5min 市场最新的特征词
                # 只要满足 (币种) + (Price) + (at) 的组合就锁定
                found_count = 0
                for m in markets:
                    if not isinstance(m, dict): continue
                    
                    q = str(m.get('question', '')).lower()
                    desc = str(m.get('description', '')).lower()
                    full = q + " " + desc
                    
                    # 匹配逻辑：BTC/ETH/SOL 且 包含 "price" 且 包含 "at"
                    is_crypto_price = any(coin in full for coin in ["btc", "eth", "sol"])
                    is_time_sensitive = "price" in full and "at" in full
                    
                    if is_crypto_price and is_time_sensitive:
                        mid = m.get('condition_id')
                        if mid and mid not in self.hunts:
                            tokens = m.get('tokens')
                            # 确保有两个 Token (Yes/No) 且数据完整
                            if tokens and len(tokens) >= 2:
                                self.hunts[mid] = {
                                    "q": m.get('question'),
                                    "tokens": tokens,
                                    "end": m.get('end_date_iso', '9999-12-31')
                                }
                                found_count += 1
                                logger.info(f"🎯 锁定猎物: {m.get('question')}")

                # 打印当前库存，方便排查
                if found_count == 0 and not self.hunts:
                    logger.info(f"🔎 扫描了 {len(markets)} 个市场，当前库存为 0，等待新盘口...")
                
                # 清理逻辑：移除已过期的市场
                now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}

            except Exception as e:
                logger.error(f"📡 扫描异常: {e}")
            await asyncio.sleep(45)

    async def sniper_loop(self):
        """核心改进：不仅看盘口，更要抢时间"""
        logger.info("⚔️ 狙击手：窗口期轮询就绪...")
        while True:
            now = int(time.time())
            rem = now % 300  # 5分钟周期

            # 锁定收盘前 5-18 秒
            if 282 <= rem <= 295:
                for mid, data in list(self.hunts.items()):
                    try:
                        # 兼容不同 API 版本的 Key 名
                        t0 = data['tokens'][0]
                        token_id = t0.get('tokenId') or t0.get('token_id')
                        
                        ob = await asyncio.to_thread(self.client.get_orderbook, token_id)
                        
                        bids = ob.get("bids", [])[:3]
                        asks = ob.get("asks", [])[:3]
                        
                        b_vol = sum([float(x['size']) for x in bids]) if bids else 0
                        a_vol = sum([float(x['size']) for x in asks]) if asks else 0
                        
                        # V5.4 动态信号：放低门槛至 2.2 倍，增加开仓率
                        if b_vol > a_vol * 2.2:
                            logger.info(f"🔥 [YES 信号确认] 标的: {data['q'][:20]}")
                            await self.fire_order(data['tokens'][0], "YES")
                            await asyncio.sleep(15)
                        elif a_vol > b_vol * 2.2:
                            logger.info(f"🔥 [NO 信号确认] 标的: {data['q'][:20]}")
                            await self.fire_order(data['tokens'][1], "NO")
                            await asyncio.sleep(15)
                    except:
                        continue
            await asyncio.sleep(0.5)

    async def fire_order(self, t_data, side):
        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            # 暴力抢成交价格
            price = 0.52 if side == "YES" else 0.48
            
            order_p = OrderArgs(price=price, size=self.bet_size, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            logger.info(f"💰 [下单反馈] {resp}")
        except Exception as e:
            logger.error(f"❌ [执行失败] {e}")

    async def run(self):
        logger.info(f"🚀 V5.4 APEX Predator 正在就位 | 规模: {self.bet_size} USDC")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(ApexPredatorV5_4().run())
    except KeyboardInterrupt:
        pass
