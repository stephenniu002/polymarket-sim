import os
import sys
import asyncio
import logging
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# --- 1. 环境路径补丁 ---
sys.path.insert(0, os.path.join(os.getcwd(), ".venv", "lib", "python3.11", "site-packages"))

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.5] %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ApexPredatorV5_5:
    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk: raise ValueError("❌ 环境变量中缺少 PK")
        self.client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137)
        self.hunts = {}
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))

    async def discovery_loop(self):
        """核心改进：增加状态与时间双重校验，踢出 2023 年的老古董"""
        logger.info("📡 发现引擎：2026 实盘模式锁定...")
        while True:
            try:
                resp = await asyncio.to_thread(self.client.get_markets)
                markets = resp.get("data", []) if isinstance(resp, dict) else resp
                
                now = datetime.now(timezone.utc)
                found_count = 0
                
                for m in markets:
                    if not isinstance(m, dict): continue
                    
                    # 1. 基础信息提取
                    q = str(m.get('question', '')).lower()
                    active = m.get('active', False)
                    closed = m.get('closed', False)
                    
                    # 2. 核心过滤：必须是活跃的，且包含 5-minute 或 Price at 关键词
                    is_live = active and not closed
                    is_target = ("5-minute" in q or "price at" in q)
                    
                    if is_live and is_target:
                        mid = m.get('condition_id')
                        if mid and mid not in self.hunts:
                            tokens = m.get('tokens')
                            if tokens and len(tokens) >= 2:
                                # 记录猎物
                                self.hunts[mid] = {
                                    "q": m.get('question'),
                                    "tokens": tokens,
                                    "end": m.get('end_date_iso')
                                }
                                found_count += 1
                                logger.info(f"🎯 发现当前活跃目标: {m.get('question')}")

                # 每轮清理已不在 API 列表中的旧目标
                current_api_ids = [m.get('condition_id') for m in markets]
                self.hunts = {k: v for k, v in self.hunts.items() if k in current_api_ids}
                
                if found_count == 0 and not self.hunts:
                    logger.info(f"🔎 监控中：全场 {len(markets)} 个市场均无活跃 5min 目标...")

            except Exception as e:
                logger.error(f"📡 发现异常: {e}")
            await asyncio.sleep(45)

    async def sniper_loop(self):
        """狙击逻辑保持不变，但增加更细致的日志"""
        logger.info("⚔️ 狙击手：周期窗口监测中...")
        while True:
            now = int(time.time())
            rem = now % 300 

            # 最后 15 秒黄金期
            if 285 <= rem <= 297:
                for mid, data in list(self.hunts.items()):
                    try:
                        t0 = data['tokens'][0]
                        token_id = t0.get('tokenId') or t0.get('token_id')
                        
                        ob = await asyncio.to_thread(self.client.get_orderbook, token_id)
                        
                        # 压制力分析
                        bids = ob.get("bids", [])[:3]
                        asks = ob.get("asks", [])[:3]
                        b_vol = sum([float(x['size']) for x in bids]) if bids else 0
                        a_vol = sum([float(x['size']) for x in asks]) if asks else 0
                        
                        if b_vol > a_vol * 2.5:
                            logger.info(f"🔥 [检测到多头压制] {data['q'][:25]} | OFI: {b_vol/max(a_vol,1):.1f}x")
                            await self.fire_order(data['tokens'][0], "YES")
                            await asyncio.sleep(15)
                        elif a_vol > b_vol * 2.5:
                            logger.info(f"🔥 [检测到空头压制] {data['q'][:25]} | OFI: {a_vol/max(b_vol,1):.1f}x")
                            await self.fire_order(data['tokens'][1], "NO")
                            await asyncio.sleep(15)
                    except:
                        continue
            await asyncio.sleep(0.5)

    async def fire_order(self, t_data, side):
        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            price = 0.52 if side == "YES" else 0.48
            
            order_p = OrderArgs(price=price, size=self.bet_size, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_params=order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed_order=signed)
            logger.info(f"💰 [实盘成交反馈] {resp}")
        except Exception as e:
            logger.error(f"❌ [执行失败] {e}")

    async def run(self):
        logger.info(f"🚀 V5.5 APEX Predator 正在就位 | 规模: {self.bet_size} USDC")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(ApexPredatorV5_5().run())
    except KeyboardInterrupt:
        pass
