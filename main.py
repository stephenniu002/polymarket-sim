import os
import asyncio
import logging
import time

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
from market import get_tokens  # 使用我们融合后的获取函数
from trader import get_balance, safe_order
from tg import send_message # 假设你有这个函数发通知

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 目标关键词监控
TARGETS = ["Bitcoin", "Ethereum", "Solana", "XRP", "BNB", "Dogecoin"]

async def main():
    logging.info("🚀 龙虾火控系统 V2.0 正式启动！")
    
    # 记录上次看到的 Condition ID，防止重复通知
    last_seen_conditions = set()
    
    while True:
        try:
            # A. 账户状态汇报
            balance = get_balance()
            logging.info(f"💰 [状态汇报] 当前账户余额: {balance} USDC")

            # B. 扫描目标市场并获取结构化 Token ID
            # get_tokens 会返回包含 name, condition_id, up_token, down_token 的列表
            active_markets = get_tokens() 
            
            if not active_markets:
                logging.warning("⚠️ 未发现匹配的活跃市场，请检查 TARGETS 关键词。")
            
            for m_data in active_markets:
                m_name = m_data['name']
                c_id = m_data['condition_id']
                up_id = m_data['up_token']
                down_id = m_data['down_token']

                # C. 发现新市场通知 (可选)
                if c_id not in last_seen_conditions:
                    new_msg = f"🆕 监测到新盘口: {m_name}\nID: {c_id[:12]}..."
                    logging.info(f"✨ {new_msg}")
                    # send_message(new_msg) # 如果配置了TG可以开启
                    last_seen_conditions.add(c_id)

                # D. 策略判断与执行入口
                # 示例逻辑：如果余额充足且满足策略条件
                # 假设你有一个策略函数判断买入方向 (side: 'buy', outcome: 'up'/'down')
                # side, outcome = my_strategy_logic(m_name)
                
                # if side == 'buy':
                #     target_token = up_id if outcome == 'up' else down_id
                #     logging.info(f"🎯 触发信号！准备执行: {m_name} -> {outcome}")
                #     safe_order(target_token, amount=10, side='buy') # 示例下单10U

                logging.info(f"📡 [监控中] {m_name[:30]}... (Vol: {m_data['volume']})")

            logging.info("✅ 本次巡检完成。系统进入静默监控，5分钟后重新扫描 ID。")
            await asyncio.sleep(300) # 5分钟刷新一次市场 ID

        except Exception as e:
            logging.error(f"⚠️ 系统运行异常: {e}")
            await asyncio.sleep(30) # 异常后缩短重试间隔

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 系统已手动停止")
