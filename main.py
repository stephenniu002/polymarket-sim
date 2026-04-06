import os
import asyncio
import requests
import logging
import sys
from web3 import Web3
from web3.middleware import geth_poa_middleware
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 1. 日志与通知配置 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LOBSTER-MASTER")

def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🦞 [实盘状态]\n{msg}"}, timeout=5)
        except: pass

# ================= 2. 链上连接与余额校验 =================
RPCS = [
    "https://rpc.ankr.com/polygon",
    "https://polygon.llamarpc.com",
    "https://1rpc.io/matic"
]

def get_w3():
    for rpc in RPCS:
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 5}))
            if w3.is_connected():
                # Polygon 必须注入 PoA 中间件
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                return w3
        except: continue
    return None

def check_balance(w3):
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        # USDC.e 合约地址
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
            abi=[{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
        )
        matic = w3.eth.get_balance(addr) / 1e18
        usdc = usdc_contract.functions.balanceOf(addr).call() / 1e6
        return usdc, matic
    except Exception as e:
        logger.error(f"❌ 余额读取失败: {e}")
        return 0.0, 0.0

# ================= 3. 盘口数据抓取 =================
def get_best_ask(token_id):
    """获取卖一价，即买入成本"""
    try:
        url = f"https://clob.polymarket.com/book?token_id={token_id}"
        r = requests.get(url, timeout=3).json()
        if r.get('asks') and len(r['asks']) > 0:
            return float(r['asks'][0]['price'])
        return 1.0 # 如果没盘口，返回最大值防止误触发
    except:
        return 1.0

# ================= 4. 核心套利执行 =================
async def run_arbitrage(client, y_id, n_id, y_ask, n_ask, size):
    try:
        logger.info(f"🔥 触发对冲! 成本: {y_ask + n_ask:.3f} | 单量: {size}")
        
        # 构造两个买单任务
        # 增加 0.002 冗余价格，确保吃单成交
        tasks = [
            asyncio.to_thread(client.post_order, {"price": round(y_ask + 0.002, 3), "size": size, "side": "BUY", "token_id": y_id}),
            asyncio.to_thread(client.post_order, {"price": round(n_ask + 0.002, 3), "size": size, "side": "BUY", "token_id": n_id})
        ]
        
        responses = await asyncio.gather(*tasks)
        
        success_count = 0
        for resp in responses:
            if resp.get("success") or resp.get("status") == "OK":
                success_count += 1
        
        if success_count == 2:
            send_tg(f"✅ 对冲成功!\n成本: {y_ask + n_ask:.3f}\n收益预期: {1 - (y_ask+n_ask):.3f}")
        elif success_count == 1:
            send_tg(f"⚠️ 警告: 单边成交! 另一半下单失败，请检查账户。")
        else:
            logger.error(f"❌ 全部下单被拒: {responses}")
            
    except Exception as e:
        logger.error(f"💥 执行异常: {e}")

# ================= 5. 主循环 =================
async def main():
    logger.info("🚀 Lobster-Master 套利系统启动 (实盘 V3)")
    
    # 初始化账户
    client = ClobClient(host="https://clob.polymarket.com", key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            # 1. 状态自检
            w3 = get_w3()
            if not w3:
                logger.error("❌ 无法连接 RPC，等待重试...")
                await asyncio.sleep(10)
                continue
                
            usdc, matic = check_balance(w3)
            logger.info(f"📊 账户余额: {usdc:.2f} USDC.e | {matic:.4f} MATIC")
            
            if matic < 0.1:
                logger.warning("🚫 MATIC 不足，可能导致交易失败！")

            # 2. 获取活跃市场（从采样接口获取）
            resp = requests.get("https://clob.polymarket.com/sampling-markets", timeout=10).json()
            markets = resp if isinstance(resp, list) else resp.get("data", [])
            
            for m in markets[:10]: # 扫描前10个活跃市场
                try:
                    tokens = m.get("tokens", [])
                    if len(tokens) < 2: continue
                    
                    y_id, n_id = tokens[0]["token_id"], tokens[1]["token_id"]
                    q_text = m.get("question", "未知市场")

                    # 3. 获取盘口真实成本
                    y_ask = get_best_ask(y_id)
                    n_ask = get_best_ask(n_id)
                    total_cost = y_ask + n_ask

                    # 4. 套利逻辑触发 (成本 < 0.965)
                    if 0.1 < total_cost < 0.965:
                        logger.info(f"💎 发现机会: {q_text[:20]} | SUM: {total_cost:.3f}")
                        
                        order_size = float(os.getenv("ORDER_SIZE", "5.0"))
                        if usdc < (order_size * 2):
                            logger.warning(f"资金不足，无法执行 {order_size} 规模套利")
                            continue
                            
                        await run_arbitrage(client, y_id, n_id, y_ask, n_ask, order_size)
                        await asyncio.sleep(2) # 下单后冷却

                except Exception as e:
                    continue

            logger.info("⏳ 扫描轮次结束，等待下一次探测...")
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"💥 主循环系统级异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
