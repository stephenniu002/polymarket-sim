import os
import sys
import asyncio
import logging
import time
import re
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.2.3] %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ApexPredator:
    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk: raise ValueError("❌ 缺失 PK")
        self.client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137)
        self.hunts = {}
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))
        # 匹配 "BTC Price at 1:00 PM" 这种典型的 5min 市场格式
        self.pattern = re.compile(r"(btc|eth|sol)\s+price\s+at\s+\d{1,2}:\d{2}", re.IGNORECASE)

    async def discovery_loop(self):
        logger.info("📡 发现引擎：基于前端特征的精准扫描开启...")
        while True:
            try:
                # 获取全场市场
                resp = await asyncio.to_thread(self.client.get_markets)
                markets = resp.get("data", []) if isinstance(resp, dict) else resp
                
                found_this_round = 0
                for m in markets:
                    if not isinstance(m, dict): continue
                    
                    q_text = str(m.get('question', ''))
                    desc_text = str(m.get('description', ''))
                    full_text = (q_text + " " + desc_text).lower()

                    # 核心改动：正则匹配 5min 市场的标题特征
                    if self.pattern.search(full_text) or "fiveminute" in full_text:
                        mid = m.get('condition_id')
                        if mid and mid not in self.hunts:
                            tokens = m.get('tokens')
                            if tokens and len(tokens) >= 2:
                                self.hunts[mid] = {
                                    "q": q_text,
                                    "tokens": tokens,
                                    "end": m.get('end_date_iso') # 记录结束时间
                                }
                                found_this_round += 1
                                logger.info(f"🎯 发现精准目标: {q_text}")

                if found_this_round == 0 and not self.hunts:
                    logger.info(f"🔎 扫描了 {len(markets)} 个市场，正在等待新盘口生成...")
                
                # 自动剔除已结束的市场
                now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                self.hunts = {k: v for k, v in self.hunts.items() if v.get('end', '9999') > now_iso}

            except Exception as e:
                logger.error(f"📡 扫描异常: {e}")
            await asyncio.sleep(45) # 加快扫描频率

    async def sniper_loop(self):
        logger.info("⚔️ 狙击手：监测窗口已开启...")
        while True:
            now = int(time.time())
            # 5分钟周期的秒数余数
            rem = now % 300
            
            # 我们在 280-295 秒（最后 5-20 秒）进行全力分析
            if 280 <= rem <= 297:
                for mid, data in list(self.hunts.items()):
                    try:
                        # 兼容 tokenId 的不同写法
                        t0 = data['tokens'][0]
                        y_id = t0.get('tokenId') or t0.get('token_id')
                        
                        # 非阻塞获取盘口
                        ob = await asyncio.to_thread(self.client.get_orderbook, y_id)
                        
                        bids, asks = ob.get("bids", [])[:3], ob.get("asks", [])[:3]
                        b_vol = sum([float(x['size']) for x in bids]) if bids else 0
                        a_vol = sum([float(x['size']) for x in asks]) if asks else 0
                        
                        # V5.2.3 信号门槛：3倍压制
                        if b_vol > a_vol * 3.0:
                            await self.fire_order(data['tokens'][0], "YES", data['q'])
                            await asyncio.sleep(20) # 单个市场单次成交后进入冷却
                        elif a_vol > b_vol * 3.0:
                            await self.fire_order(data['tokens'][1], "NO", data['q'])
                            await asyncio.sleep(20)
                            
                    except:
                        continue
            await asyncio.sleep(0.5) # 极速轮询

    async def fire_order(self, t_data, side, q_name):
        try:
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            # 抢单价：YES 给 0.52 确保成交，NO 给 0.48 确保成交
            price = 0.52 if side == "YES" else 0.48
            
            logger.info(f"🔥 [出击] 方向: {side} | 标的: {q_name[:30]}")
            
            order_p = OrderArgs(price=price, size=self.bet_size, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            
            logger.info(f"💰 [成交] 订单反馈: {resp}")
        except Exception as e:
            logger.error(f"❌ [失败] 原因: {e}")

    async def run(self):
        logger.info(f"🚀 V5.2.3 APEX 启动 | 注资: {self.bet_size} USDC")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    try:
        asyncio.run(ApexPredator().run())
    except KeyboardInterrupt:
        pass
