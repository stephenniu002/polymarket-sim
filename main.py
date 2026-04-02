import os
import sys
import subprocess

# --- 强制路径修正逻辑 ---
# 1. 尝试找到 .venv 路径并加入系统环境
venv_path = "/app/.venv/lib/python3.11/site-packages"
if venv_path not in sys.path:
    sys.path.append(venv_path)

# 2. 暴力重装并指定安装位置
try:
    from clob_client.client import ClobClient
except ImportError:
    print("🚀 正在将库安装到指定路径...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "--target", venv_path, 
        "py-clob-client==0.34.6", "aiohttp", "python-dotenv", "eth-account"
    ])
    from clob_client.client import ClobClient

import asyncio
import json
import logging
import time
import aiohttp
from datetime import datetime
from clob_client.clob_types import OrderArgs

# --- 后面保持之前的 7 种货币和报告逻辑 ---

# 核心实盘库导入
try:
    from clob_client.client import ClobClient
    from clob_client.clob_types import OrderArgs
except ImportError:
    print("❌ 运行环境缺失 py-clob-client")

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("PolymarketPro")

# ======================
# ⚙️ 核心参数配置
# ======================
CONFIG = {
    "PK": os.getenv("PK"),
    "API_KEY": os.getenv("POLY_API_KEY"),
    "API_SECRET": os.getenv("POLY_SECRET"),
    "API_PASSPHRASE": os.getenv("POLY_PASSPHRASE"),
    "TG_TOKEN": os.getenv("TELEGRAM_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "POLY_HOST": "https://clob.polymarket.com",
    "CHAIN_ID": 137
}

# 监控的7种货币
COINS = {
    "BTC":  {"id": "71342", "side": "涨"},
    "ETH":  {"id": "82451", "side": "涨"},
    "SOL":  {"id": "93560", "side": "涨"},
    "XRP":  {"id": "10471", "side": "涨"},
    "DOGE": {"id": "11582", "side": "涨"},
    "BNB":  {"id": "12693", "side": "跌"},
    "HYPE": {"id": "13704", "side": "涨"}
}

BET_AMOUNT = 1.0        # 每单金额
SIGNAL_WINDOW = 300     # 5分钟(300s)开始高频监控
EXECUTE_WINDOW = 60     # 1分钟(60s)内执行下单
REPORT_INTERVAL = 300   # 5分钟汇报一次结果

# 统计状态
stats = {coin: {"trades": 0, "success": 0} for coin in COINS}
executed_ids = set()

class PolymarketBot:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self):
        try:
            return ClobClient(
                host=CONFIG["POLY_HOST"], key=CONFIG["PK"], chain_id=CONFIG["CHAIN_ID"],
                api_key=CONFIG["API_KEY"], api_secret=CONFIG["API_SECRET"], api_passphrase=CONFIG["API_PASSPHRASE"]
            )
        except Exception as e:
            logger.error(f"❌ 鉴权失败: {e}")
            return None

    async def get_balance_safe(self):
        """实时获取钱包 USDC 余额"""
        try:
            # 这里的获取方法取决于具体 SDK 版本，通用方式是获取账户所有余额
            balances = self.client.get_balances()
            # 过滤出 USDC 余额（通常在 Polygon 上）
            for b in balances:
                if b.get('asset_type') == 'ERC20' and 'USDC' in str(b.get('asset_id', '')):
                    return f"{b.get('balance', '0.00')} USDC"
            return "0.00 USDC (未检测到资产)"
        except Exception as e:
            logger.error(f"余额获取异常: {e}")
            return "查询中..."

    async def send_tg(self, text):
        if not CONFIG["TG_TOKEN"]: return
        url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
        payload = {"chat_id": CONFIG["CHAT_ID"], "text": f"🦞 {text}", "parse_mode": "Markdown"}
        async with aiohttp.ClientSession() as session:
            try: await session.post(url, json=payload, timeout=10)
            except: pass

    async def execute_trade(self, coin, token_id):
        try:
            # 价格 0.99 确保抢单成功
            order_args = OrderArgs(price=0.99, size=BET_AMOUNT, side="BUY", token_id=token_id)
            signed_order = self.client.create_order(order_args)
            resp = self.client.post_order(signed_order)

            if resp and resp.get("success"):
                stats[coin]["trades"] += 1
                stats[coin]["success"] += 1
                await self.send_tg(f"✅ *下单成功* | {coin}\n订单ID: `{resp.get('orderID')}`")
                return True
            else:
                logger.error(f"❌ 下单被拒: {resp}")
                await self.send_tg(f"⚠️ *下单失败* | {coin}\n错误: `{resp.get('error')}`")
        except Exception as e:
            logger.error(f"⚠️ 交易执行异常: {e}")
        return False

    async def monitor_market(self, coin, info):
        logger.info(f"📡 启动监控: {coin}")
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    api_url = f"https://gamma-api.polymarket.com/events/{info['id']}"
                    async with session.get(api_url) as r:
                        if r.status != 200:
                            wait_time = 30
                        else:
                            data = await r.json()
                            market = data['markets'][0]
                            end_ts = datetime.fromisoformat(market['endsAt'].replace('Z', '+00:00')).timestamp()
                            time_left = end_ts - time.time()

                            # 1. 还没到 5 分钟：慢速轮询
                            if time_left > SIGNAL_WINDOW:
                                wait_time = 20
                            
                            # 2. 进入 5 分钟尾盘：高频监控 (5秒/次)
                            elif 60 < time_left <= SIGNAL_WINDOW:
                                logger.info(f"👀 {coin} 距离结束 {int(time_left)}s")
                                wait_time = 5
                            
                            # 3. 进入 1 分钟窗口：直接下单
                            elif 0 < time_left <= EXECUTE_WINDOW and info['id'] not in executed_ids:
                                logger.info(f"⚡ {coin} 触发1分钟下单限制！")
                                token_ids = json.loads(market['clobTokenIds'])
                                target_token = token_ids[0] if info['side'] == "涨" else token_ids[1]
                                if await self.execute_trade(coin, target_token):
                                    executed_ids.add(info['id'])
                                wait_time = 10
                            else:
                                wait_time = 60

            except:
                wait_time = 15
            await asyncio.sleep(wait_time)

    async def periodic_report(self):
        """每 5 分钟进行一次资产和交易汇报"""
        while True:
            await asyncio.sleep(REPORT_INTERVAL)
            balance = await self.get_balance_safe()
            
            msg = "📊 *【5分钟实盘报告】*\n"
            msg += f"💰 *钱包余额*: `{balance}`\n"
            msg += "────────────────\n"
            
            has_action = False
            for coin, data in stats.items():
                if data['trades'] > 0:
                    msg += f"• {coin}: 本次成交 {data['success']} 次\n"
                    has_action = True
            
            if not has_action:
                msg += "_当前周期无下单成交_\n_所有监控点运行正常..._"
            
            await self.send_tg(msg)

    async def start(self):
        if not self.client: 
            logger.error("❌ 无法启动: 客户端未初始化")
            return
        
        await self.send_tg("🚀 *Polymarket 尾盘机器人已上线*\n- 策略：5分钟尾盘/1分钟抢单\n- 状态：7种货币并行监控中")
        
        # 并行执行监控和报告
        tasks = [self.monitor_market(c, i) for c, i in COINS.items()]
        tasks.append(self.periodic_report())
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    bot = PolymarketBot()
    asyncio.run(bot.start())
