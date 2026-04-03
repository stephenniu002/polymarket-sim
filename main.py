import asyncio
import logging
from market import get_market, get_tokens, top_markets
from trader import place_order, get_balance

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def main():
    logging.info("🚀 龙虾火控系统 V2.0 已上线！")
    
    while True:
        try:
            # 1. 汇报账户状态
            balance = get_balance()
            logging.info(f"💰 [状态汇报] 当前账户余额: {balance} USDC")

            # 2. 扫描目标市场
            # 这里的 get_market("Trump") 现在不会再报错了
            targets = ["Bitcoin", "Ethereum", "Solana", "Trump"]
            for keyword in targets:
                markets = get_market(keyword)
                if markets:
                    logging.info(f"🔍 [监控中] {keyword} 相关市场发现 {len(markets)} 个")

            # 3. 策略逻辑占位 (可以在此加入你的反转交易判断)
            # ...

            logging.info("✅ 本次巡检完成。系统进入静默监控，5分钟后进行下次汇报。")
            
            # 4. 关键：休眠 5 分钟 (300秒)
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
