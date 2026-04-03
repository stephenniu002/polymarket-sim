import asyncio
import logging
from market import get_market, get_tokens, top_markets
from trader import place_order, get_balance

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

async def main():
    logging.info("🦞 龙虾火控系统 V2.0 已上线！")
    
    while True:
        try:
            # 1. 汇报账户状态
            balance = get_balance()
            logging.info(f"💰 当前账户余额: {balance} USDC")

            # 2. 扫描目标市场 (解决之前传入 "Trump" 报错的问题)
            targets = ["Bitcoin", "Ethereum", "Solana", "Trump"]
            for keyword in targets:
                markets = get_market(keyword)
                if markets:
                    logging.info(f"🔍 监控中: {keyword} 相关市场发现 {len(markets)} 个")

            # 3. 可以在这里加入你的“最后一分钟反转”交易逻辑判断
            # ... (策略代码) ...

            logging.info("✅ 5分钟巡检汇报完成。系统进入静默监控...")
            
            # 4. 关键：休眠 300 秒 (5分钟)
            await asyncio.sleep(300)

        except Exception as e:
            logging.error(f"⚠️ 循环运行出错: {e}")
            # 出错后等 30 秒再尝试，防止因网络问题导致瞬间刷屏
            await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
