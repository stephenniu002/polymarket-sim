import asyncio
from ws_engine import run_ws
from strategy import generate_signal
from trader import execute_trade

cooldown = {}


async def on_market(market, state):
    if market in cooldown:
        return

    signal = generate_signal(state)

    if not signal:
        return

    # 👉 简单强度计算
    strength = len(state["trades"]) / 50

    token_id = state["trades"][-1]["token_id"]
    price = state["trades"][-1]["price"]

    print(f"🎯 {market} 信号: {signal} | 强度: {strength:.2f}")

    execute_trade(market, token_id, signal, price, strength)

    cooldown[market] = True

    # 冷却60秒
    await asyncio.sleep(60)
    cooldown.pop(market, None)


async def main():
    print("🚀 V30 实时交易系统启动")

    await run_ws(on_market)


if __name__ == "__main__":
    asyncio.run(main())
