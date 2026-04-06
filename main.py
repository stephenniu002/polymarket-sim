import os
import asyncio
import requests
import time
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================== 配置 (从环境变量读取) ==================
# 建议在 Railway 设置：MARKET_ID 为具体的 Token ID (例如 BTC 高低预测的 ID)
MARKET_ID = os.getenv("MARKET_ID", "21695712644755057531586361132660542317170423138438635199041119103045656331264")
ORDER_STEP = 0.002  # 阶梯间距
ORDER_SIZE = 1.0    # 每单 1 USDC
SCAN_INTERVAL = 3   # 3秒扫描一次，避开 WS 404 烦恼

# ================== 核心逻辑 ==================
async def lobster_logic():
    # 初始化官方 Client
    client = ClobClient(
        host="https://clob.polymarket.com", 
        key=os.getenv("POLY_PRIVATE_KEY"), 
        chain_id=137
    )
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    print(f"🚀 Lobster 阶梯挂单版启动 | 目标市场 ID: {MARKET_ID[:15]}...")

    while True:
        try:
            # 1. 获取盘口 (代替不稳定的 WebSocket)
            book = client.get_orderbook(MARKET_ID)
            bids = book.bids if hasattr(book, 'bids') else []
            asks = book.asks if hasattr(book, 'asks') else []

            if not bids or not asks:
                print("⏳ 盘口深度不足，跳过此轮...")
                await asyncio.sleep(5)
                continue

            best_bid = float(bids[0].price)
            best_ask = float(asks[0].price)
            print(f"📊 盘口更新: Bid {best_bid} | Ask {best_ask}")

            # 2. 计算阶梯价格 (简单做市逻辑)
            # 我们在买一价下方一点买入，卖一价上方一点卖出
            buy_price = round(best_bid - 0.001, 3)
            sell_price = round(best_ask + 0.001, 3)

            # 3. 执行下单 (使用官方签名逻辑)
            # 注意：此处仅作演示，实盘中建议先 cancel_all 再下单
            try:
                # 尝试挂一个买单
                client.post_order({
                    "price": buy_price,
                    "size": ORDER_SIZE,
                    "side": "BUY",
                    "token_id": MARKET_ID
                })
                print(f"✅ 挂出买单: {buy_price}")
            except Exception as e:
                if "insufficient" in str(e).lower():
                    print("💰 资金已占用，等待成交...")
                else:
                    print(f"❌ 下单失败: {e}")

            await asyncio.sleep(SCAN_INTERVAL)

        except Exception as e:
            print(f"💥 循环异常: {e}")
            await asyncio.sleep(10)

# ================== 余额监控 ==================
def report_balance():
    # 官方推荐的余额获取方式是通过 Web3 或者查询 Proxy 地址
    # 这里简化处理，你可以通过 client 获取
    print(f"⏰ [{time.strftime('%H:%M:%S')}] 机器人运行中，监控盘口数据...")

async def main():
    # 启动主逻辑
    await lobster_logic()

if __name__ == "__main__":
    asyncio.run(main())
