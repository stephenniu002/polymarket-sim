import os
import sys
import asyncio
import logging
import time
from dotenv import load_dotenv

# --- 1. 强制环境与路径补丁 ---
sys.path.insert(0, os.path.join(os.getcwd(), ".venv", "lib", "python3.11", "site-packages"))
load_dotenv() # 提前加载

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 日志与变量二次校验 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.6.1] %(message)s')
logger = logging.getLogger(__name__)

# 增加多重尝试，防止环境变量名称大小写不一致
PRIVATE_KEY = os.getenv("PK") or os.getenv("PRIVATE_KEY") or os.getenv("pk") or os.getenv("private_key")

if not PRIVATE_KEY:
    # 打印当前环境变量列表（不含具体值，仅看键名），方便你排查 Railway 到底传了啥
    logger.error(f"❌ 环境变量缺失！当前可用键名: {list(os.environ.keys())}")
    sys.exit(1) # 优雅退出，防止循环报错

class ApexPredatorV5_6_1:
    def __init__(self):
        # 初始化客户端
        self.client = ClobClient("https://clob.polymarket.com", key=PRIVATE_KEY, chain_id=137)
        self.hunts = {}
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))

    async def discovery_loop(self):
        logger.info("📡 2026 高频引擎：寻找猎物中...")
        while True:
            try:
                # 尝试抓取多页，确保不被政治盘刷屏
                all_m = []
                for cursor in ["MA==", "MTAw"]:
                    resp = await asyncio.to_thread(self.client.get_markets, next_cursor=cursor)
                    data = resp.get("data", []) if isinstance(resp, dict) else resp
                    if data: all_m.extend(data)
                
                for m in all_m:
                    if not isinstance(m, dict) or not m.get('active'): continue
                    
                    slug = str(m.get('market_slug', '')).lower()
                    q = str(m.get('question', '')).lower()
                    
                    # 2026 精准匹配逻辑
                    if "up-or-down" in slug or "price at" in q or "5-min" in q:
                        mid = m.get('condition_id')
                        if mid and mid not in self.hunts:
                            tokens = m.get('tokens')
                            if tokens and len(tokens) >= 2:
                                self.hunts[mid] = {
                                    "q": m.get('question'),
                                    "tokens": tokens,
                                    "end": m.get('end_date_iso')
                                }
                                logger.info(f"🎯 锁定活跃目标: {m.get('question')}")

                # 清理过期
                now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}

            except Exception as e:
                logger.error(f"📡 发现异常: {e}")
            await asyncio.sleep(45)

    async def sniper_loop(self):
        logger.info("⚔️ 狙击手：监测中...")
        while True:
            now = int(time.time())
            rem = now % 300 
            if 285 <= rem <= 297:
                for mid, data in list(self.hunts.items()):
                    try:
                        t0 = data['tokens'][0]
                        token_id = t0.get('tokenId') or t0.get('token_id')
                        ob = await asyncio.to_thread(self.client.get_orderbook, token_id)
                        
                        b_vol = sum([float(x['size']) for x in ob.get("bids", [])[:3]])
                        a_vol = sum([float(x['size']) for x in ob.get("asks", [])[:3]])
                        
                        if b_vol > a_vol * 2.5:
                            logger.info(f"🔥 [YES 触发] {data['q']}")
                            await self.fire_order(data['tokens'][0], "YES")
                            await asyncio.sleep(15)
                        elif a_vol > b_vol * 2.5:
                            logger.info(f"🔥 [NO 触发] {data['q']}")
                            await self.fire_order(data['tokens'][1], "NO")
                            await asyncio.sleep(15)
                    except: continue
            await asyncio.sleep(0.5)

    async def fire_order(self, t_data, side):
        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            price = 0.53 if side == "YES" else 0.47
            order_p = OrderArgs(price=price, size=self.bet_size, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            logger.info(f"✅ [成交反馈] {resp}")
        except Exception as e:
            logger.error(f"❌ [订单拦截] {e}")

    async def run(self):
        logger.info(f"🚀 V5.6.1 启动 | 自动注入密钥成功")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(ApexPredatorV5_6_1().run())
    except KeyboardInterrupt:
        pass
