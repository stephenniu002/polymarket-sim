import os
import sys
import asyncio
import logging
import time
from dotenv import load_dotenv

# --- 1. 环境路径修正 (Railway 专用) ---
sys.path.insert(0, os.path.join(os.getcwd(), ".venv", "lib", "python3.11", "site-packages"))

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 系统配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [V5.2-APEX] %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ApexPredatorV5_2:
    def __init__(self):
        pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not pk: raise ValueError("❌ 缺失 PK 环境变量")
        
        # 初始化客户端
        self.client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137)
        
        # 状态空间
        self.hunts = {}             # 活跃猎物
        self.signal_buffer = {}     # 信号确认缓冲区 (V5.2 核心)
        self.consecutive_losses = 0  # 连亏计数
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))
        self.running = True

    # --- 模块 A: 修复分页后的自动发现 ---
    async def discovery_loop(self):
        logger.info("📡 发现引擎启动...")
        while self.running:
            try:
                resp = await asyncio.to_thread(self.client.get_markets)
                markets = resp.get("data", []) if isinstance(resp, dict) else resp
                
                targets = [m for m in markets if "5-minute" in str(m.get('description', '')).lower()]
                
                for m in targets:
                    mid = m.get('condition_id')
                    if mid and mid not in self.hunts:
                        self.hunts[mid] = {
                            "q": m.get('question'),
                            "tokens": m.get('tokens'), # 包含准确的 tokenId
                        }
                
                # 保持库的精简，只追踪最近的 5 个市场
                if len(self.hunts) > 5:
                    self.hunts = dict(list(self.hunts.items())[-5:])
                    
            except Exception as e:
                logger.error(f"📡 发现异常: {e}")
            await asyncio.sleep(60)

    # --- 模块 B: V5.2 信号确认逻辑 ---
    def confirm_signal(self, mid, current_sig):
        """核心提升：连续 3 次信号一致才视为真突破"""
        buf = self.signal_buffer.setdefault(mid, [])
        buf.append(current_sig)
        if len(buf) > 3: buf.pop(0)
        
        if len(buf) == 3 and all(s == current_sig and s is not None for s in buf):
            return True
        return False

    def get_ofi_signal(self, ob):
        """订单流不平衡分析"""
        bids, asks = ob.get("bids", [])[:3], ob.get("asks", [])[:3]
        if not bids or not asks: return None
        
        b_vol = sum([float(x['size']) for x in bids])
        a_vol = sum([float(x['size']) for x in asks])
        
        if b_vol > a_vol * 2.5: return "YES"
        if a_vol > b_vol * 2.5: return "NO"
        return None

    # --- 模块 C: 修正后的狙击逻辑 ---
    async def sniper_loop(self):
        logger.info("⚔️ 狙击手巡逻中 (V5.2 增强版)...")
        while self.running:
            now = int(time.time())
            rem = now % 300 # 5分钟周期进度

            # 锁定最后 5-15 秒 (285s - 295s)
            if 285 <= rem <= 295:
                if self.consecutive_losses >= 3:
                    logger.warning("🛑 触发熔断：连亏 3 单，暂停交易 10 分钟")
                    await asyncio.sleep(600)
                    self.consecutive_losses = 0
                    continue

                for mid, data in list(self.hunts.items()):
                    try:
                        # 修正 tokenId 的大小写读取
                        yes_token_id = data['tokens'][0].get('tokenId')
                        # 非阻塞获取盘口
                        ob = await asyncio.to_thread(self.client.get_orderbook, yes_token_id)
                        
                        raw_sig = self.get_ofi_signal(ob)
                        if self.confirm_signal(mid, raw_sig):
                            logger.info(f"🔥 信号确认! {data['q'][:20]} -> {raw_sig}")
                            
                            # 确定目标 ID
                            t_id = data['tokens'][0]['tokenId'] if raw_sig == "YES" else data['tokens'][1]['tokenId']
                            await self.fire_order(t_id, raw_sig)
                            
                            # 成功触发后清理缓存并冷却
                            self.signal_buffer[mid] = []
                            await asyncio.sleep(15)
                    except Exception as e:
                        logger.debug(f"Sniper cycle skip: {e}")
            await asyncio.sleep(1)

    # --- 模块 D: 修正后的实盘下单流程 ---
    async def fire_order(self, t_id, side):
        try:
            # 抢跑价格：YES 买入稍微设高，NO 买入稍微设低（本质都是为了吃掉对手盘）
            price = 0.52 if side == "YES" else 0.48
            
            # 正确的 Polymarket 签名下单流程
            order_args = OrderArgs(
                price=price,
                size=self.bet_size,
                side="buy",
                token_id=t_id
            )
            
            # 1. 创建订单 -> 2. 签名订单 -> 3. 提交订单
            order = await asyncio.to_thread(self.client.create_order, order_args)
            signed_order = self.client.sign_order(order)
            resp = await asyncio.to_thread(self.client.submit_order, signed_order)
            
            logger.info(f"✅ 下单成功: {resp}")
            # 注意：实际生产中需要对接 get_trades 来更新 self.consecutive_losses
            
        except Exception as e:
            logger.error(f"❌ 下单失败: {e}")

    async def run(self):
        logger.info("🚀 APEX Predator V5.2 启动成功。")
        await asyncio.gather(self.discovery_loop(), self.sniper_loop())

if __name__ == "__main__":
    bot = ApexPredatorV5_2()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        pass
