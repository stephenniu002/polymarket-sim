import os
import sys
import asyncio
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# --- 1. 环境兼容性补丁 (解决 Railway 找不到包的问题) ---
current_dir = os.getcwd()
venv_path = os.path.join(current_dir, ".venv", "lib", "python3.11", "site-packages")
if os.path.exists(venv_path):
    sys.path.insert(0, venv_path)
    # 递归兼容其他可能的 Python 版本
    import glob
    for p in glob.glob(os.path.join(current_dir, ".venv", "lib", "python*", "site-packages")):
        if p not in sys.path: sys.path.insert(0, p)

# 强制安装/导入核心库
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
except ImportError:
    import subprocess
    logger_init = logging.getLogger(__name__)
    logger_init.error("检测到环境缺失，正在现场安装 py-clob-client...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs

# --- 2. 系统日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] ⚡ APEX-V5: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
load_dotenv()

class ApexPredatorV5:
    def __init__(self):
        # 核心凭证检查
        self.pk = os.getenv("PK") or os.getenv("PRIVATE_KEY")
        if not self.pk:
            raise ValueError("❌ 错误：环境变量中缺少 PK (私钥)！")
            
        self.host = "https://clob.polymarket.com"
        self.client = ClobClient(self.host, key=self.pk, chain_id=137)
        
        # 状态空间
        self.active_hunts = {}      # 存放当前追踪的市场数据
        self.last_depth_sum = {}    # 盘口总量快照，用于反欺骗
        self.bet_size = float(os.getenv("BET_SIZE", 5.0))
        self.is_running = True

    # --- 模块 A: 自动发现引擎 (Auto-Discovery) ---
    async def discovery_engine(self):
        """每 60 秒扫描一次 Polymarket，自动锁定最新的 5min 高频标的"""
        logger.info("📡 自动发现引擎启动...")
        while self.is_running:
            try:
                # 获取所有活跃市场并筛选 5-minute 类别
                markets = self.client.get_markets()
                found = [m for m in markets if "5-minute" in str(m.get('description', '')).lower()]
                
                new_count = 0
                for m in found:
                    mid = m.get('condition_id')
                    if mid not in self.active_hunts:
                        self.active_hunts[mid] = {
                            "question": m.get('question'),
                            "tokens": m.get('tokens'), # [Yes_ID, No_ID]
                            "end_time": m.get('end_time')
                        }
                        new_count += 1
                
                if new_count > 0:
                    logger.info(f"🎯 扫描完成：新增 {new_count} 个猎物，当前共追踪 {len(self.active_hunts)} 个市场")
                
                # 清理逻辑：只保留 active 列表里的
                current_mids = [m.get('condition_id') for m in markets]
                self.active_hunts = {k: v for k, v in self.active_hunts.items() if k in current_mids}
                
            except Exception as e:
                logger.error(f"📡 发现引擎异常: {e}")
            await asyncio.sleep(60)

    # --- 模块 B: V5 核心信号算法 (OFI + Anti-Spoof) ---
    def get_signal(self, condition_id, ob):
        """分析买卖盘前5档的压制力对比"""
        bids = ob.get("bids", [])[:5]
        asks = ob.get("asks", [])[:5]
        
        if not bids or not asks: return None

        bid_vol = sum([float(b['size']) for b in bids])
        ask_vol = sum([float(a['size']) for a in asks])
        total_depth = bid_vol + ask_vol

        # 1. 假单过滤 (Anti-Spoofing)：对比快照，若深度突变 > 50% 视为诱多/诱空
        prev_depth = self.last_depth_sum.get(condition_id, total_depth)
        self.last_depth_sum[condition_id] = total_depth
        
        if abs(prev_depth - total_depth) / prev_depth > 0.5:
            logger.warning(f"⚠️ 检测到盘口突变，怀疑欺骗性挂单，跳过信号")
            return None

        # 2. OFI 压制力：2.5 倍权重压制
        if bid_vol > ask_vol * 2.5: return "BUY_YES"  # 买盘极强
        if ask_vol > bid_vol * 2.5: return "BUY_NO"   # 卖盘极强
        
        return None

    # --- 模块 C: 尾盘狙击执行 (Sniper Task) ---
    async def sniper_task(self):
        """在每 5 分钟周期的最后 15 秒执行高频盘口扫描与下单"""
        logger.info("⚔️ 狙击手模块就位，锁定最后 15 秒窗口期...")
        while self.is_running:
            now = time.time()
            # 计算 300 秒（5分钟）周期的剩余时间
            remaining = 300 - (now % 300)

            # 仅在收盘前 5 到 15 秒内分析信号
            if 5 <= remaining <= 15:
                for mid, data in list(self.active_hunts.items()):
                    try:
                        # 默认获取 Yes Token 的盘口进行分析
                        yes_token_id = data['tokens'][0].get('token_id')
                        ob = self.client.get_orderbook(yes_token_id)
                        
                        signal = self.get_signal(mid, ob)
                        if signal:
                            # 确定购买的目标 Token
                            target_token = data['tokens'][0].get('token_id') if signal == "BUY_YES" else data['tokens'][1].get('token_id')
                            logger.info(f"🔥 发现信号: {data['question'][:30]}... 方向: {signal}")
                            await self.fire_order(target_token, signal)
                            # 冷却：防止同一窗口期对同一市场重复下单
                            await asyncio.sleep(15) 
                    except Exception as e:
                        continue # 忽略单次网络波动
            
            await asyncio.sleep(1) # 非窗口期低频运行节省资源

    async def fire_order(self, token_id, side_label):
        """执行 Clob 签名下单"""
        try:
            # V5 策略：定在 0.50 左右吃单，size 由 Kelly 逻辑或配置决定
            order_args = OrderArgs(
                price=0.50, 
                size=self.bet_size,
                side="BUY", # Polymarket 下单逻辑：买入对应的 Yes/No Token
                token_id=token_id
            )
            signed_order = self.client.create_order(order_args)
            resp = self.client.post_order(signed_order)
            
            order_id = resp.get('orderID', 'Unknown')
            logger.info(f"✅ [成交成功] 方向: {side_label} | ID: {order_id}")
            
        except Exception as e:
            logger.error(f"❌ 下单失败: {e}")

    # --- 启动流程 ---
    async def run(self):
        logger.info(f"🚀 V5 APEX Predator 正在启动... 初始注资: {self.bet_size} USDC")
        # 并发执行三大核心模块
        await asyncio.gather(
            self.discovery_engine(),
            self.sniper_task()
        )

if __name__ == "__main__":
    try:
        bot = ApexPredatorV5()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("👋 正在安全关闭机器人...")
    except Exception as e:
        logger.critical(f"💥 致命系统崩溃: {e}")
