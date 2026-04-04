import os
import asyncio
import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

# ========== 核心配置 ==========
ORDER_SIZE = float(os.getenv("ORDER_SIZE", 1.0))
# 这里的搜索词要精准，建议匹配 Gamma API 的常用标题
ASSETS = ["Bitcoin Price Above", "Ethereum Price Above", "Solana Price Above"]
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
# =============================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_tg_msg(msg: str):
    if TG_TOKEN and TG_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg}, timeout=5)
        except Exception as e:
            logging.error(f"TG 通知失败: {e}")

def init_clob_client():
    """初始化客户端，确保 API Key 权限正确"""
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=os.getenv("POLY_PRIVATE_KEY"),
        chain_id=POLYGON
    )
    creds = ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),
        api_secret=os.getenv("POLY_SECRET"),
        api_passphrase=os.getenv("POLY_PASSPHRASE")
    )
    client.set_api_creds(creds)
    return client

client = init_clob_client()

async def get_valid_balance():
    """安全获取余额，处理异常返回"""
    try:
        # 使用线程池执行同步 SDK 调用
        resp = await asyncio.to_thread(client.get_collateral_balance)
        if resp and isinstance(resp, dict):
            val = float(resp.get("balance", 0))
            logging.info(f"💰 账户可用余额: {val} USDC")
            return val
    except Exception as e:
        logging.error(f"❌ 余额读取失败 (请检查 API View 权限): {e}")
    return 0.0

def fetch_latest_token(search_query: str):
    """
    动态抓取最新的 Token ID
    逻辑：只找进行中的(active)、成交量最大的第一个市场
    """
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "search": search_query,
        "limit": 5
    }
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        # 过滤掉没有 clobTokenIds 的条目
        markets = [m for m in resp if m.get("clobTokenIds") and len(m["clobTokenIds"]) >= 2]
        if not markets:
            return None
        
        # 选出成交量最大的市场（通常是最主流的市场）
        top_market = max(markets, key=lambda x: float(x.get("volume", 0)))
        
        # 索引 0 通常是 'Yes' (Above/Up)，索引 1 是 'No' (Below/Down)
        token_id = top_market["clobTokenIds"][0] 
        market_name = top_market.get("question", "未知市场")
        
        logging.info(f"🎯 匹配到市场: {market_name} | ID: {token_id[:15]}...")
        return token_id
    except Exception as e:
        logging.warning(f"🔍 抓取 {search_query} Token 失败: {e}")
        return None

async def safe_execute_buy(token_id: str, asset_label: str):
    """异步执行下单，带重试和错误隔离"""
    try:
        def _place():
            # 生成、签名、发送订单
            order_args = client.create_order(
                price=0.5, # 示例固定 0.5，实盘建议加入价格预测逻辑
                size=ORDER_SIZE,
                side="buy",
                token_id=token_id
            )
            signed = client.sign_order(order_args)
            return client.place_order(signed)

        res = await asyncio.to_thread(_place)
        if res and res.get("success"):
            logging.info(f"✅ {asset_label} 下单成功!")
            return True
    except Exception as e:
        logging.error(f"❌ {asset_label} 下单失败: {e}")
    return False

async def run_trading_round():
    """核心交易轮询"""
    balance = await get_valid_balance()
    
    if balance < ORDER_SIZE:
        logging.warning("🛑 余额不足，跳过本轮")
        return

    success_count = 0
    attempt_count = 0

    for asset in ASSETS:
        token_id = fetch_latest_token(asset)
        if token_id:
            attempt_count += 1
            # 执行下单
            is_ok = await safe_execute_buy(token_id, asset)
            if is_ok: success_count += 1
            # 稍微停顿，避免请求过快被 Polymarket 频控
            await asyncio.sleep(1) 

    if attempt_count > 0:
        msg = f"🦞 龙虾实盘报告\n成功/尝试: {success_count}/{attempt_count}\n当前余额: {balance} USDC"
        send_tg_msg(msg)

async def main():
    logging.info("🚀 龙虾实盘系统 V5.6 启动 (API 权限: View+Trade)")
    send_tg_msg("🚀 龙虾实盘系统已启动，监控资产: " + ", ".join(ASSETS))
    
    while True:
        try:
            await run_trading_round()
        except Exception as e:
            logging.error(f"⚠️ 循环崩溃，正在重启: {e}")
        
        # 每 300 秒执行一次，避免频繁操作手续费损耗
        await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("用户停止程序")
