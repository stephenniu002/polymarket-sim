import asyncio
import os
import logging
from datetime import datetime

# 导入你仓库里的模块
from market import get_market, get_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance
from config import TELEGRAM_TOKEN, CHAT_ID
import requests

# --- 基础配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LOBSTER-CORE")

def send(msg):
    """战报推送"""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": f"🦞 {msg}"}, timeout=5)
        except Exception as e:
            logger.error(f"TG推送失败: {e}")

# --- 核心猎杀逻辑 ---
async def hunting_filter(t, data):
    """
    火控系统：策略选择 -> 信号评分 -> 市场过滤 -> 仓位计算 -> 下单
    """
    if t != "TRADE":
        return

    try:
        # 1. 动态环境研判 (Strategy Selection)
        # 根据当前市场热度或时间点自动切换策略
        current_strategy = choose_strategy()
        
        # 2. 深度信号评分 (Scoring)
        # 结合成交量、价差、波动率给这一单打分
        score = score_signal(data, current_strategy)
        
        if score < 2:
            # 噪音太大或机会不成熟，放弃
            return

        # 3. 市场热度过滤 (Top Markets Only)
        # 确保只在流动性最好的前几个市场玩，防止无法离场
        token_id = data.get("token_id")
        active_list = top_markets() # 获取当前热门市场列表
        if token_id not in active_list:
            # logger.info(f"🍃 市场 {token_id[:8]} 不在热门列表，跳过")
            return

        # 4. 智能仓位管理 (Dynamic Sizing)
        # 根据当前账户余额和策略风险等级计算下多少手
        balance = get_balance()
        size = calc_size(balance, current_strategy)

        if size <= 0:
            logger.warning("💸 余额不足或仓位计算结果为 0")
            return

        # 5. 精准打击 (Execution)
        price = float(data["price"])
        logger.info(f"🎯 触发高分信号 ({score})! 策略: {current_strategy} | 规模: {size}")
        
        # 异步执行实盘下单
        res = place_order(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY"
        )

        # 6. 实时战报
        if res and "orderID" in str(res):
            send(f"✅ 【实盘成交】\n评分: {score}\n策略: {current_strategy}\n市场: {token_id[:8]}\n价格: {price}\n数量: {size}")
        else:
            logger.error(f"❌ 下单失败响应: {res}")

    except Exception as e:
        logger.error(f"💥 核心循环报错: {e}")

# --- 主守护进程 ---
async def main():
    send("🚀 龙虾火控系统 V2.0 已上线！监控中...")
    
    # 锁定监控目标（比如 Trump 相关的热门市场）
    market = get_market("Trump")
    if not market:
        logger.error("❌ 无法初始化目标市场")
        return

    yes_token, _ = get_tokens(market)
    
    while True:
        try:
            # 挂载 WebSocket 监听，并传入猎杀逻辑回调
            await stream(yes_token, hunting_filter)
        except Exception as e:
            logger.error(f"📡 网络波动，10秒后重连: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 指挥部已撤离。")
