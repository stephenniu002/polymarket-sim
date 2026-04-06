import os
import asyncio
import requests
import logging
import sys
from web3 import Web3

# ✅ 完美兼容 Web3 V6+ 
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 1. 日志与通知 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("LOBSTER-ELITE")

def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🦞 [实盘通知]\n{msg}"}, timeout=5)
        except: pass

# ================= 2. 链上连接 (使用你提供的 RPC 组) =================
RPCS = [
    "https://polygon-bor.publicnode.com",
    "https://polygon.blockpi.network/v1/rpc/public",
    "https://rpc-mainnet.maticvigil.com"
]

def get_w3():
    headers = {'User-Agent': 'Mozilla/5.0'}
    for rpc in RPCS:
        try:
            # 增加超时容错
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10, "headers": headers}))
            if w3.is_connected():
                # 注入 Polygon 必须的 PoA 中间件
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                logger.info(f"🔗 节点连接成功: {rpc}")
                return w3
        except:
            continue
    return None

def check_balance(w3):
    try:
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        # USDC.e 合约 (Polygon)
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
            abi=[{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
        )
        matic = w3.eth.get_balance(addr) / 1e18
        usdc = usdc_contract.functions.balanceOf(addr).call() / 1e6
        return usdc, matic
    except Exception as e:
        logger.error(f"❌ 资产读取异常: {e}")
        return 0.0, 0.0

# ================= 3. 主程序 =================
async def main():
    logger.info("🚀 Lobster-Master 实盘系统启动...")
    
    # 初始化账户
    client = ClobClient(host="https://clob.polymarket.com", key=os.getenv("PRIVATE_KEY"), chain_id=137)
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            # 1. 余额同步
            w3 = get_w3()
            if not w3:
                logger.error("❌ RPC 全线故障，15秒后重试...")
                await asyncio.sleep(15)
                continue
                
            usdc, matic = check_balance(w3)
            logger.info(f"💰 实时资产: {usdc:.2f} USDC.e | {matic:.4f} MATIC")
            
            # 2. 获取市场 (使用 Sampling 接口)
            markets_resp = requests.get("https://clob.polymarket.com/sampling-markets", timeout=10).json()
            markets = markets_resp if isinstance(markets_resp, list) else markets_resp.get("data", [])
            
            logger.info(f"🔎 正在扫描 {len(markets[:15])} 个活跃市场...")

            for m in markets[:15]:
                try:
                    tokens = m.get("tokens", [])
                    if len(tokens) < 2: continue
                    
                    y_id, n_id = tokens[0]["token_id"], tokens[1]["token_id"]
                    
                    # 获取卖一价
                    y_book = requests.get(f"https://clob.polymarket.com/book?token_id={y_id}", timeout=5).json()
                    n_book = requests.get(f"https://clob.polymarket.com/book?token_id={n_id}", timeout=5).json()
                    
                    y_ask = float(y_book['asks'][0]['price']) if y_book.get('asks') else 1.0
                    n_ask = float(n_book['asks'][0]['price']) if n_book.get('asks') else 1.0
                    
                    total = y_ask + n_ask
                    
                    # 套利阈值触发
                    if 0.1 < total < 0.965:
                        logger.info(f"🔥 捕获获利机会: SUM={total:.3f}")
                        
                        order_size = float(os.getenv("ORDER_SIZE", "5.0"))
                        if usdc < (order_size * 2):
                            logger.warning("余额不足以支持对冲，跳过。")
                            continue
                            
                        # 双向对冲下单
                        for t_id, price in [(y_id, y_ask), (n_id, n_ask)]:
                            await asyncio.to_thread(client.post_order, {
                                "price": round(price + 0.003, 3), # 覆盖滑点
                                "size": order_size,
                                "side": "BUY",
                                "token_id": t_id
                            })
                        send_tg(f"✅ 套利下单完成\n成本: {total:.3f}\n规模: {order_size} USDC")
                
                except Exception: continue

            await asyncio.sleep(20)

        except Exception as e:
            logger.error(f"💥 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
