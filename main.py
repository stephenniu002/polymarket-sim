import os
import sys
import asyncio

print("🚀 启动中...")

# ====== 环境检查 ======
print("Python路径:", sys.executable)
print("当前路径:", os.getcwd())

# ====== 正确 import ======
try:
    from py_clob_client.client import ClobClient
    print("✅ py_clob_client 导入成功")
except Exception as e:
    print("❌ 导入失败:", e)
    exit(1)


# ====== 你的 API 配置 ======
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

if not PRIVATE_KEY:
    print("❌ 没有 PRIVATE_KEY")
else:
    print("✅ 环境变量读取成功")


# ====== 初始化 client ======
def init_client():
    try:
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=PRIVATE_KEY,
            chain_id=137  # Polygon
        )
        print("✅ ClobClient 初始化成功")
        return client
    except Exception as e:
        print("❌ 初始化失败:", e)
        return None


# ====== 测试 API ======
async def test():
    client = init_client()
    if not client:
        return

    try:
        markets = client.get_markets()
        print("📊 获取市场成功:", len(markets))
    except Exception as e:
        print("❌ API 调用失败:", e)


# ====== 主程序 ======
async def main():
    while True:
        await test()
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
