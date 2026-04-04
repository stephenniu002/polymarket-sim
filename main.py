import time
import logging
from trader import execute_trade, get_balance
from scanner import get_live_market
from tg import send_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def lobster_fire_control():
    logging.info("🚀 龙虾火控系统 V3.3 实盘动态版启动")
    send_message("🦞 龙虾火控系统 V3.3 已上线！\n监测模式：实盘余额 + 动态 ID 同步")

    while True:
        try:
            # 1. 检查实盘余额 (确保那 9.00 USDC 到账)
            balance = get_balance()
            logging.info(f"💰 账户余额: {balance} USDC")

            if balance < 1.0:
                logging.warning(f"⚠️ 余额不足 ({balance} USDC)，系统挂机中...")
                time.sleep(60)
                continue

            # 2. 动态轮询资产，解决 ConditionID 变化问题
            for asset in ["Bitcoin", "Ethereum", "Solana"]:
                market = get_live_market(asset)
                if market:
                    logging.info(f"📡 监测中: {market['question']}")
                    
                    # --- 示例：在此处接入你的交易信号 ---
                    # if 策略满足:
                    #    execute_trade(market['up_id'], price=0.5, size=2.0)
                
            logging.info("✅ 巡检完成。5 分钟后将重新扫描新 ConditionID 防止过期。")
            time.sleep(300) # 每 5 分钟循环一次

        except Exception as e:
            logging.error(f"系统运行异常: {e}")
            time.sleep(10)

if __name__ == "__main__":
    lobster_fire_control()
