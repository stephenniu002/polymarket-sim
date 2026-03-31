# --- 在配置部分增加 ---
MAX_DRAWDOWN = 0.3  # 最大亏损 30% 就关机
STOP_LOSS_LIMIT = INITIAL_BALANCE * (1 - MAX_DRAWDOWN)

# --- 在 run_trade_cycle 逻辑中增加 ---
async def run_trade_cycle():
    global balance
    
    # 🛑 止损检查：如果余额跌破 7000U，立即停止
    if balance <= STOP_LOSS_LIMIT:
        error_msg = f"🛑 【系统熔断】当前余额 {balance:.2f}U 已触及止损线 {STOP_LOSS_LIMIT}U，程序已紧急停止！"
        send_telegram(error_msg)
        print(error_msg)
        os._exit(0) # 强制关闭进程

    # ... 原有的 7 币种并发逻辑 ...
