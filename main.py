async def main():
    try:
        logging.info("🚀 龙虾 V8.2 实盘系统启动中...")
        
        # 1. 先验证环境变量
        if not SIGNER_PK or "0x" not in SIGNER_PK:
            raise ValueError("私钥格式不正确或未读取到")
            
        # 2. 预抓取一次市场 ID (调用你的 market.py 函数)
        global ACTIVE_MARKETS
        ACTIVE_MARKETS = fetch_latest_market_map()
        
        if not ACTIVE_MARKETS:
            logging.warning("⚠️ 初始启动未发现活跃市场，程序将持续尝试...")

        # 3. 进入主循环
        while True:
            try:
                # 你的信号扫描逻辑...
                balance = await get_balance()
                logging.info(f"--- 循环检查中 (余额: {balance}) ---")
                await asyncio.sleep(30)
            except Exception as loop_e:
                logging.error(f"⚠️ 循环内报错 (不退出): {loop_e}")
                await asyncio.sleep(10)

    except Exception as fatal_e:
        logging.error(f"❌ 致命启动错误: {fatal_e}")
        # 发送 TG 报警告诉你为什么挂了
        send_tg(f"🚨 系统启动失败并退出: {fatal_e}")
        # 停顿一下，防止 Railway 无限重启导致封号
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
