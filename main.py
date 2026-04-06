import os
import asyncio
import requests
import logging
import sys
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

# ================= 1. 环境与日志配置 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Lobster-Pro")

def send_tg(msg):
    token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": f"🦞 [实盘监控]\n{msg}"}, timeout=5)
        except: pass

# ================= 2. 链上余额校验 (Web3) =================
RPC_URL = "https://polygon-rpc.com"
USDC_E_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # USDC.e
ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def get_onchain_balance():
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        addr = Web3.to_checksum_address(os.getenv("POLY_ADDRESS"))
        contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_CONTRACT), abi=ERC20_ABI)
        
        # 检查 MATIC (Gas)
        matic_balance = w3.eth.get_balance(addr) / 1e18
        # 检查 USDC.e
        raw_usdc = contract.functions.balanceOf(addr).call()
        usdc_balance = raw_usdc / 1e6
        
        logger.info(f"📊 链上状态: {usdc_balance:.2f} USDC | {matic_balance:.4f} MATIC")
        return usdc_balance, matic_balance
    except Exception as e:
        logger.error(f"❌ 余额校验失败: {e}")
        return 0, 0

# ================= 3. 市场与价格获取 =================
def get_active_markets():
    try:
        # 使用采样接口获取活跃交易对
        resp = requests.get("https://clob.polymarket.com/sampling-markets", timeout=10).json()
        markets = resp if isinstance(resp, list) else resp.get("data", [])
        return [m for m in markets if "tokens" in m and len(m["tokens"]) >= 2][:10]
    except: return []

def get_price(token_id):
    try:
        r = requests.get(f"https://clob.polymarket.com/price?token_id={token_id}", timeout=5).json()
        return float(r.get("price", 0))
    except: return 0

# ================= 4. 主套利逻辑 =================
async def main():
    logger.info("🚀 实盘套利系统启动 [强制 Polygon 137 模式]")
    
    # 环境自检
    usdc, matic = get_onchain_balance()
    if matic < 0.1:
        msg = f"❌ 严重警告: MATIC 不足 ({matic:.4f})，无法支付 Gas！"
        logger.error(msg)
        send_tg(msg)
    if usdc < 1.0:
        logger.warning("⚠️ 余额过低，请确认资金是否在 Polygon 链的 USDC.e 合约中。")

    # 初始化 CLOB
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("PRIVATE_KEY"),
        chain_id=137 # ✅ 强制锁定 Polygon
    )
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    ))

    while True:
        try:
            markets = get_active_markets()
            logger.info(f"🔎 扫描中... 活跃市场: {len(markets)}")

            for m in markets:
                q = m.get("question", "未知")
                y_id, n_id = m["tokens"][0]["token_id"], m["tokens"][1]["token_id"]
                
                y_p, n_p = get_price(y_id), get_price(n_id)
                if y_p <= 0 or n_p <= 0: continue
                
                total = y_p + n_p
                # logger.info(f"⚖️ {q[:15]} | SUM: {total:.3f}")

                # 套利触发: 理论总价应为 1，若远低于 0.97 则存在无风险机会
                if 0.1 < total < 0.965:
                    logger.info(f"🔥 发现机会! {q[:20]} | SUM: {total:.3f}")
                    
                    order_size = float(os.getenv("ORDER_SIZE", "1.0"))
                    # 尝试双向吃单
                    for t_id, price in [(y_id, y_p), (n_id, n_p)]:
                        # 稍微加价 0.005 确保吃单成交
                        await asyncio.to_thread(client.post_order, {
                            "price": round(price + 0.005, 3),
                            "size": order_size,
                            "side": "BUY",
                            "token_id": t_id
                        })
                    
                    send_tg(f"✅ 执行套利\n市场: {q[:15]}\nSUM: {total:.3f}\n单量: {order_size} USDC")
                
                await asyncio.sleep(0.5)

            await asyncio.sleep(30) # 轮询间隔

        except Exception as e:
            logger.error(f"💥 循环异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
