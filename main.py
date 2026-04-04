import time
import logging
from trader import execute_trade, get_balance
from tg import send_message # 确保你的 tg.py 已经按照之前的建议改好

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def lobster_fire_control():
    logging.info("🚀 龙虾火控系统 V3.2 实盘启动！")
    send_message("🦞 龙虾火控系统 V3.2 已上线，实盘监控中...")

    while True:
        try:
            # 1. 检查弹药
            balance = get_balance()
            logging.info(f"💰 当前账户余额: {balance} USDC")

            if balance < 1.0:
                logging.warning("⚠️ 余额不足，系统挂机中...")
                time.sleep(60)
                continue

            # 2. 策略示例：这里可以接入你的指标，比如 RSI 破位或大户跟单
            # 假设我们现在要对 BTC 进行一次极小额测试
            # test_resp = execute_trade("BTC", side="UP", price=0.45, size=1)
            
            # 3. 轮询监控各币种盘口 (在此处接入你的价格监控逻辑)
            # for symbol in ["BTC", "ETH", "SOL", "HYPE"]:
            #    price = get_market_price(symbol)
            #    if price < 0.3: # 跌过头了，买入反弹
            #        execute_trade(symbol, "UP", price=0.35, size=2)

            logging.info("📡 巡检完成，等待下一轮信号...")
            time.sleep(300) # 每 5 分钟巡检一次

        except Exception as e:
            logging.error(f"系统运行异常: {e}")
            time.sleep(10)

if __name__ == "__main__":
    lobster_fire_control()
