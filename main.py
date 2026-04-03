import os
import asyncio
import logging

# ===== 1. 环境诊断 (最优先执行，确保变量加载) =====
print("🔍 --- 系统环境诊断中 ---")
addr = os.getenv("POLY_ADDRESS")
api_key = os.getenv("POLY_API_KEY")
secret = os.getenv("POLY_SECRET")

if not addr:
    print("🚨 警报：代码未读取到 POLY_ADDRESS！请检查 Railway Variables。")
else:
    print(f"✅ 成功读取地址: {addr[:6]}...{addr[-4:]}")

if not api_key:
    print("🚨 警报：代码未读取到 POLY_API_KEY！")
if not secret:
    print("🚨 警报：代码未读取到 POLY_SECRET！")
print("🔍 --- 诊断结束 ---")

# ===== 2. 导入模块与日志配置 =====
# 确保 market.py 和 trader.py 在同一目录下
from market import get_market, get_tokens, top_markets
from trader import place_order, get_balance, safe_order

# 时区建议在 Railway 设置 TZ=Asia/Shanghai
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== 3. 核心主程序 =====
async def main():
    logging.info("🚀 龙虾火控系统 V2.0 已上线！")
    
    # 统计计数器
    stats = {"success": 0, "failed": 0}
    
    while True:
        try:
            # A. 账户状态汇报 (调用 trader.py 中的双保险查询)
            balance = get_balance()
            logging.info(f"💰 [状态汇报] 当前账户余额: {balance} USDC")

            # B. 扫描目标市场 (调用 market.py)
            targets = ["Bitcoin", "Ethereum", "Solana", "Trump"]
            for keyword in targets:
                markets = get_market(keyword)
                if markets:
                    logging.info(f"🔍 [监控中] {keyword} 相关市场发现 {len(markets)} 个")

            # C. 下单逻辑占位
            # 如果你有特定的交易信号，可以在这里调用 safe_order(...)

            logging.info("✅ 本次巡检完成。系统进入静默监控，5分钟后进行下次汇报。")
            
            # D. 循环休眠 (300秒 = 5分钟)
            await asyncio.sleep(300)

        except Exception as e:
            logging.error(f"⚠️ 系统运行中发生错误: {e}")
            # 出错时缩短休眠时间，快速重试
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 系统已手动停止")
