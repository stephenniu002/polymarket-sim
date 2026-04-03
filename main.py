import asyncio
import os
import logging
import requests
from datetime import datetime

# 1. 导入仓库模块 (确保这些函数在对应文件里已定义)
from market import get_market, get_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance

# 2. 基础配置：直接对接 Railway 环境变量，不走 config.py
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LOBSTER-CORE")

TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    """战报推送：对接环境变量"""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            payload = {"chat_id": CHAT_ID, "text": f"🦞 {msg}", "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"TG推送失败: {e}")

# 3. 核心猎杀逻辑
async def hunting_filter(t, data):
    """
    火控系统：策略选择 -> 信号评分 -> 市场过滤 -> 仓位计算 -> 下单
    """
    if t != "TRADE":
        return

    try:
        # A. 动态环境研判 (Strategy Selection)
        current_strategy = choose_strategy()
        
        # B. 深度信号评分 (Scoring)
        score = score_signal(data, current_strategy)
        
        if score < 2:
            return

        # C. 市场热度过滤 (Top Markets Only)
        token_id = data.get("token_id")
        active_list = top_markets() 
        if token_id not in active_list:
            return

        # D. 智能仓位管理 (Dynamic Sizing)
        balance = get_balance()
        size = calc_size(balance, current_strategy)

        if size <= 0:
            logger.warning("💸 余额不足或仓位计算结果为 0")
            return

        # E. 精准打击 (Execution)
        price = float(data.get("price", 0))
        logger.info(f"🎯 触发高分信号 ({score})! 策略: {current_strategy} | 规模: {size}")
        
        # 异步执行实盘下单
        res = place_order(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY"
        )

        # F. 实时战报
        if res and ("orderID" in str(res) or "SUCCESS" in str(res)):
            send(f"*【实盘成交】*\n⭐ 评分: {score}\n📈 策略: {current_strategy}\n🏷️ 市场: {token_id[:8]}\n💰 价格: {price}\n📊 数量: {size}")
        else:
            logger.error(f"❌ 下单失败响应: {res}")

    except Exception as e:
        logger.error(f"💥 核心循环报错: {e}")

# 4. 主守护进程
async def main():
    logger.info("🚀 龙虾火控系统 V2.0 已上线！")
    send("🚀 *龙虾系统已上线*！开始监控目标市场...")
    
    # 锁定监控目标（例如 Trump 或 Crypto 相关的盘口）
    # 确保 market.py 里的 get_market 能返回一个 dict
    target_market = get_market("Trump") 
    if not target_market:
        logger.error("❌ 无法初始化目标市场，尝试搜索默认盘口...")
        # 兜底逻辑：如果找不到 Trump，找一个活跃盘口
        active_ids = top_markets()
        if not active_ids:
            return
        yes_token = active_ids[0]
    else:
        yes_token, _ = get_tokens(target_market)
    
    if not yes_token:
        logger.error("❌ 未找到有效的 Token ID")
        return

    while True:
        try:
            # 挂载 WebSocket 监听
            await stream(yes_token, hunting_filter)
        except Exception as e:
            logger.error(f"📡 网络波动，10秒后重连: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 指挥部已撤离。")
