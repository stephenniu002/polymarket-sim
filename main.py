import asyncio
import logging
import os
import requests

# 1. 导入你仓库里的模块 (确保这些文件里也没有 import config)
from market import get_all_active_5min_markets, get_tokens, top_markets
from ws import stream
from strategy import choose_strategy, score_signal, calc_size
from trader import place_order, get_balance

# 2. 基础日志配置
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LOBSTER-CORE")

# 3. 从 Railway 环境变量读取配置 (无需 config.py)
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_notification(msg):
    """战报推送至 Telegram"""
    if TG_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        try:
            payload = {"chat_id": CHAT_ID, "text": f"🦞 {msg}", "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"TG推送失败: {e}")

# 4. 核心猎杀逻辑：最后一分钟反转
async def hunting_filter(t, data):
    """
    WS 数据回调：只在最后 60 秒识别超跌/超涨信号
    """
    if t != "TRADE":
        return

    try:
        token_id = data.get("token_id")
        
        # A. 时间窗口过滤：只打“最后一分钟”白名单里的 Token
        # top_markets() 会根据 market.py 里的 is_last_minute 判断
        active_whitelist = top_markets()
        if token_id not in active_whitelist:
            return

        # B. 策略研判：买入反转信号
        current_strategy = choose_strategy() # 确保 strategy.py 适配 5min 盘
        score = score_signal(data, current_strategy)
        
        if score < 2:
            return

        # C. 仓位控制：读取实盘余额
        balance = get_balance()
        size = calc_size(balance, current_strategy)

        if size <= 0:
            logger.warning("💸 余额不足或仓位计算为 0，跳过本次狙击")
            return

        # D. 执行实盘下单
        price = float(data.get("price", 0))
        logger.info(f"🎯 发现反转机会! 分数: {score} | 规模: {size} | Token: {token_id[:8]}")
        
        # 调用 trader.py 里的下单逻辑
        order_res = place_order(
            token_id=token_id,
            price=price,
            size=size,
            side="BUY"
        )

        # E. 实时战报
        if order_res and "orderID" in str(order_res):
            msg = (
                f"*【末日反转成交】*\n"
                f"💰 价格: {price}\n"
                f"📊 规模: {size}\n"
                f"⭐ 评分: {score}\n"
                f"🕒 窗口: 最后一分钟"
            )
            send_notification(msg)

    except Exception as e:
        logger.error(f"💥 核心循环报错: {e}")

# 5. 主程序入口
async def main():
    logger.info("🌊 龙虾高频猎手 V2.0 启动成功！")
    send_notification("🚀 龙虾系统已上线，正在扫描 7 大加密 5min 盘口...")
    
    while True:
        try:
            # 获取当前所有 5min 加密盘口的 Token 列表
            markets = get_all_active_5min_markets()
            listen_tokens = []
            
            for m in markets:
                y, n = get_tokens(m)
                if y: listen_tokens.append(y)
                if n: listen_tokens.append(n)

            if not listen_tokens:
                # logger.info("💤 暂无活跃 5min 盘口，休息 30 秒...")
                await asyncio.sleep(30)
                continue

            # 开启 WebSocket 监听第一个热门 Token
            # 注意：如果 ws.py 的 stream 逻辑只能听一个，这里建议优先听 BTC/ETH
            await stream(listen_tokens[0], hunting_filter)
            
        except Exception as e:
            logger.error(f"📡 监听异常，10秒后重启: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 指挥部收到撤离信号，系统关闭。")
