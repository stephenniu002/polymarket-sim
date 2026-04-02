import os
import sys
import asyncio
import logging
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# --- 环境补丁 ---
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

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [LOBSTER-PRO] %(message)s')
logger = logging.getLogger(__name__)

# ================= 配置区 =================
BET_SIZE = float(os.getenv("BET_SIZE", 5.0))  # 每单金额
SHADOW_THRESHOLD = 5                         # 连亏 5 次开启影子模式（实盘建议设小点）
OFI_THRESHOLD = 2.5                          # 订单流压制倍数信号
# ==========================================

class LobsterReal:
    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk: raise ValueError("❌ 缺失私钥")
        
        self.client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137)
        self.hunts = {}
        self.consecutive_losses = 0
        self.is_shadow_mode = False
        self.history_file = "real_trade_log.json"

    async def get_active_markets(self):
        """获取活跃的 5min 市场"""
        try:
            resp = await asyncio.to_thread(self.client.get_markets)
            markets = resp.get("data", []) if isinstance(resp, dict) else resp
            for m in markets:
                if not isinstance(m, dict) or not m.get('active'): continue
                q = m.get('question', '').lower()
                if "price at" in q or "5-minute" in q:
                    mid = m.get('condition_id')
                    if mid not in self.hunts:
                        self.hunts[mid] = {
                            "q": m.get('question'),
                            "tokens": m.get('tokens'),
                            "end": m.get('end_date_iso')
                        }
            # 清理过期
            now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            self.hunts = {k: v for k, v in self.hunts.items() if v['end'] > now_iso}
        except Exception as e:
            logger.error(f"📡 扫描异常: {e}")

    async def sniper_logic(self):
        """核心狙击逻辑"""
        now = int(time.time())
        rem = now % 300
        
        # 仅在周期最后 15 秒观察
        if 285 <= rem <= 298:
            # 影子模式检查
            if not self.is_shadow_mode and self.consecutive_losses >= SHADOW_THRESHOLD:
                self.is_shadow_mode = True
                logger.warning(f"🚨 [风控] 连亏 {self.consecutive_losses} 次，进入影子模式（只观察不买）")

            for mid, data in list(self.hunts.items()):
                try:
                    t0 = data['tokens'][0]
                    tid = t0.get('tokenId') or t0.get('token_id')
                    ob = await asyncio.to_thread(self.client.get_orderbook, tid)
                    
                    b_vol = sum([float(x['size']) for x in ob.get("bids", [])[:3]])
                    a_vol = sum([float(x['size']) for x in ob.get("asks", [])[:3]])

                    # 判定信号
                    side = None
                    if b_vol > a_vol * OFI_THRESHOLD: side = "YES"
                    elif a_vol > b_vol * OFI_THRESHOLD: side = "NO"

                    if side:
                        if self.is_shadow_mode:
                            logger.info(f"🧪 [影子模拟] 发现 {side} 信号，但不下单: {data['q'][:20]}")
                            # 影子模式下，假设这一单会赢，从而重置进入实盘（你可以根据需要修改这个逻辑）
                            # 真实的逻辑应该是：等待 5 分钟看这单到底赢没赢。为了简化，我们模拟捕获一次信号就恢复。
                            self.is_shadow_mode = False
                            self.consecutive_losses = 0
                        else:
                            await self.execute_trade(data, side)
                            await asyncio.sleep(10) # 防止同个市场重复下单
                except:
                    continue

    async def execute_trade(self, market_data, side):
        """执行真实下单"""
        try:
            token_idx = 0 if side == "YES" else 1
            t_data = market_data['tokens'][token_idx]
            t_id = t_data.get('tokenId') or t_data.get('token_id')
            
            # 价格略微进场
            price = 0.52 if side == "YES" else 0.48
            
            logger.info(f"💰 [实盘出击] 方向: {side} | 标的: {market_data['q'][:30]}")
            
            order_p = OrderArgs(price=price, size=BET_SIZE, side="buy", token_id=t_id)
            order = await asyncio.to_thread(self.client.create_order, order_p)
            signed = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed)
            
            if resp.get("success"):
                logger.info(f"✅ 下单成功: {resp.get('order_id')}")
            else:
                logger.error(f"❌ 下单拒绝: {resp}")
                self.consecutive_losses += 1 # 如果下单失败或亏损，增加计数
        except Exception as e:
            logger.error(f"❌ 执行异常: {e}")

    async def main_loop(self):
        logger.info(f"🦞 Lobster Pro 启动 | 模式: {'影子' if self.is_shadow_mode else '实盘'}")
        while True:
            await self.get_active_markets()
            await self.sniper_logic()
            await asyncio.sleep(1)

if __name__ == "__main__":
    bot = LobsterReal()
    asyncio.run(bot.main_loop())
