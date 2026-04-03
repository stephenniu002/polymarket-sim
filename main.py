import os
import asyncio
import logging

# ===== 1. 环境诊断逻辑 (放在最顶部，直接打印到控制台) =====
print("🔍 --- 系统环境诊断中 ---")
addr = os.getenv("POLY_ADDRESS")
api_key = os.getenv("POLY_API_KEY")
secret = os.getenv("POLY_SECRET")

if not addr:
    print("🚨 警报：代码未读取到 POLY_ADDRESS！请检查 Railway Variables 是否配置。")
else:
    # 只打印前 6 位和后 4 位，保护隐私
    print(f"✅ 成功读取地址: {addr[:6]}...{addr[-4:]}")

if not api_key:
    print("🚨 警报：代码未读取到 POLY_API_KEY！")
if not secret:
    print("🚨 警报：代码未读取到 POLY_SECRET！")
print("🔍 --- 诊断结束 ---")

# ===== 2. 导入依赖与配置日志 =====
from market import get_market, get_tokens, top_markets
from trader import place_order, get_balance, safe_order

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== 3. 主程序逻辑 =====
async def main():
    logging.info("🚀 龙虾火控系统 V2.0 已上线！")
    
    # 增加一个交易统计计数器（可选）
    stats = {"success": 0, "failed": 0}
    
    while True:
        try:
            # A. 汇报账户状态
            balance = get_balance()
            logging.info(f"💰 [状态汇报] 当前账户余额: {balance} USDC")

            # B. 扫描目标市场
            targets = ["Bitcoin", "Ethereum", "Solana", "Trump"]
            for keyword in targets:
                markets = get_market(keyword)
                if markets:
                    logging.info(f"🔍 [监控中] {keyword} 相关市场发现 {len(markets)} 个")

            # C. 策略占位 (如果你在 strategy.py 有逻辑，可以这里调用)
            # 例如: await run_strategy(stats)

            logging.info("✅ 本次巡检完成。系统进入静默监控，5分钟后进行下次汇报。")
            
            # D. 休眠 5 分钟 (300秒)
            await asyncio.sleep(300)

        except Exception as e:
            logging.error(f"⚠️ 系统运行中发生错误: {e}")
            # 如果出错，等 30 秒再重试，避免报错刷屏
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
