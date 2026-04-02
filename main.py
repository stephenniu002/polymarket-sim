import os
import sys
import asyncio
import logging
import time
from dotenv import load_dotenv

# --- 1. 生产环境补丁 ---
sys.path.insert(0, os.path.join(os.getcwd(), ".venv", "lib", "python3.11", "site-packages"))

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.6-2026] %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ApexPredatorV5_6:
    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk: raise ValueError("❌ 环境变量 PK 缺失")
        # 2026 核心：使用 Gamma API 作为发现引擎补充 (如果 CLOB 延迟)
        self.client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137)
        self.hunts = {}
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))

    async def discovery_loop(self):
        """核心改进：多维度特征匹配 + 分页扫描"""
        logger.info("📡 2026 高频发现引擎启动...")
        while True:
            try:
                # 尝试抓取前两页，确保覆盖到最新生成的 5min 盘口
                all_markets = []
                for cursor in ["MA==", "MTAw"]: # 第一页和第二页的 Base64 游标
                    resp = await asyncio.to_thread(self.client.get_markets, next_cursor=cursor)
                    data = resp.get("data", []) if isinstance(resp, dict) else resp
                    if data: all_markets.extend(data)
                    else: break
                
                found_count = 0
                for m in all_markets:
                    if not isinstance(m, dict) or not m.get('active'): continue
                    
                    # 2026 年 5min 市场的三大特征特征
                    slug = str(m.get('market_slug', '')).lower()
                    q = str(m.get('question', '')).lower()
                    tags = [str(t).lower() for t in m.get('tags', [])]
                    
                    # 特征 A: 包含 "up-or-down" (BTC 5min 专属)
                    # 特征 B: 标签里有 "5min" 或 "crypto"
                    # 特征 C: 标题包含 "price at"
                    is_5min = ("up-or-down" in slug or 
                               "5min" in tags or 
                               "price at" in q)
                    
                    if is_5min:
                        mid = m.get('condition_id')
                        if mid and mid not in self.hunts:
                            tokens = m.get('tokens')
                            if tokens and len(tokens) >= 2:
                                self.hunts[mid] = {
                                    "q": m.get('question'),
                                    "tokens": tokens,
                                    "end": m.get('end_date_iso')
                                }
                                found_count += 1
                                logger.info(f"🎯 捕获 2026 实时目标: {m.get('question')}")

                # 打印扫描报告
                logger.info(f"🔎 扫描完成：当前库中活跃猎物: {len(self.hunts)} 个")
                
                # 自动清理过期猎物
                now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}

            except Exception as e:
                logger.error(f"📡 发现异常: {e}")
            await asyncio.sleep(40)

    async def sniper_loop(self):
        """保持毫秒级监测"""
        while True:
            now = int(time.time())
            rem = now % 300 
            if 285 <= rem <= 297:
                for mid, data in list(self.hunts.items()):
                    try:
                        t0 = data['tokens'][0]
                        token_id = t0.get('tokenId') or t0.get('token_id')
                        ob = await asyncio.to_thread(self.client.get_orderbook, token_id)
                        
                        bids, asks = ob.get("bids", [])[:3], ob.get("asks", [])[:3]
                        b_vol = sum([float(x['size']) for x in bids]) if bids else 0
                        a_vol = sum([float(x['size']) for x in asks]) if asks else 0
                        
                        if b_vol > a_vol * 2.5:
                            logger.info(f"🔥 [YES 压制触发] {data['q']}")
                            await self.fire_order(data['tokens'][0], "YES")
                            await asyncio.sleep(15)
                        elif a_vol > b_vol * 2.5:
                            logger.info(f"🔥 [NO 压制触发] {data['q']}")
                            await self.fire_order(data['tokens'][1], "NO")
                            await asyncio.sleep(15)
                    except: continue
            await asyncio.sleep(0.5)

    async def fire_order(self, t_data, side):
        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            price = 0.53 if side == "YES" else 0.47 # 2026 波动大，稍微提高滑点确保成交
            
            order_p = OrderArgs(price=price, size=self.bet_size, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_params=order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed_order=signed)
            logger.info(f"✅ [成交] {side} | {resp}")
        except Exception as e:
            logger.error(f"❌ [订单拦截] {e}")

    async def run(self):
        logger.info("🚀 V5.6 APEX (2026 Edition) 准备就绪")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try: asyncio.run(ApexPredatorV5_6().run())
    except KeyboardInterrupt: pass
