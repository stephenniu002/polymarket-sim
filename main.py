import os
import asyncio
import logging

# ===== 1. 环境诊断 (最优先执行) =====
print("🔍 --- 系统环境诊断中 ---")
addr = os.getenv("POLY_ADDRESS")
api_key = os.getenv("POLY_API_KEY")
secret = os.getenv("POLY_SECRET")

if not addr:
    print("🚨 警报：代码未读取到 POLY_ADDRESS！请检查 Railway 变量设置。")
else:
    print(f"✅ 成功识别地址: {addr[:6]}...{addr[-4:]}")

if not api_key or not secret:
    print("🚨 警报：API Key 或 Secret 未配置，交易功能将受限。")
print("🔍 --- 诊断结束 ---")

# ===== 2. 导入功能模块与配置日志 =====
from market import get_market
from trader import get_balance, safe_order

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def main():
    logging.info("🚀 龙虾火控系统 V2.0 正式启动！")
    
    while True:
        try:
            # A. 账户状态汇报 (双保险查询)
            balance = get_balance()
            logging.info(f"💰 [状态汇报] 当前账户余额: {balance} USDC")

            # B. 扫描目标市场
            targets = ["Bitcoin", "Ethereum", "Solana", "Trump"]
            for keyword in targets:
                markets = get_market(keyword)
                if markets:
                    logging.info(f"🔍 [监控中] {keyword} 市场发现 {len(markets)} 个活跃合约")

            # C. 策略逻辑入口 (在此处加入买反转等判断)
            # if condition: safe_order(...)

            logging.info("✅ 本次巡检完成。系统进入静默监控，5分钟后汇报。")
            await asyncio.sleep(300)

        except Exception as e:
            logging.error(f"⚠️ 系统运行异常: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 系统已手动停止")
