import time
import logging
from trader import execute_trade, get_balance
from scanner import get_active_market_ids  # 👈 导入扫描器
from tg import send_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def lobster_fire_control():
    logging.info("🚀 龙虾火控系统 V3.3 实盘启动！(动态 ID 模式)")
    send_message("🦞 龙虾火控系统 V3.3 已上线！\n监测模式：自动同步动态 ConditionID")

    while True:
        try:
            # 1. 检查账户余额 (0x365B... 地址)
            balance = get_balance()
            logging.info(f"💰 当前账户余额: {balance} USDC")

            if balance < 1.0:
                logging.warning("⚠️ 余额不足 (当前: {} USDC)，系统挂机中...".format(balance))
                time.sleep(60)
                continue

            # 2. 动态同步核心资产盘口
            assets_to_watch = ["Bitcoin", "Ethereum", "Solana", "Dogecoin", "BNB"]
            for asset in assets_to_watch:
                market_data = get_active_market_ids(asset)
                
                if market_data:
                    logging.info(f"📡 监测中: {market_data['question']} (Vol: {market_data['volume']})")
                    
                    # --- 这里接入你的策略触发逻辑 ---
                    # 示例：如果要测试下单 (0.1 USDC 买入 BTC 看涨)
                    # if asset == "Bitcoin":
                    #    execute_trade(market_data['up_id'], price=0.5, size=0.2)
                    # ----------------------------
                else:
                    logging.warning(f"❓ 未能找到活跃的 {asset} 盘口")

            logging.info("✅ 本次巡检完成。系统进入静默监控，5分钟后重新扫描 ID 以防过期。")
            time.sleep(300) # 完美的 5 分钟循环

        except Exception as e:
            logging.error(f"系统运行异常: {e}")
            time.sleep(10)

if __name__ == "__main__":
    lobster_fire_control()
