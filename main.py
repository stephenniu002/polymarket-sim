import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.models import OrderArgs

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从环境变量获取私钥 (确保 Railway 中已配置 FOX_PRIVATE_KEY)
PK = os.getenv("FOX_PRIVATE_KEY")
client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=POLYGON)

# 精准锁定的市场数据
MARKETS = {
    "BTC": {
        "condition_id": "0x63957bd199b03ae3278a819c2f2c5dbea198b0a33622652e20073a022ed27844",
        "yes_token": "19504533038661601614761427845353594073359048386377758376510344406121408103328",
        "no_token": "100412809796016629994645229606869400277259451189445103473130635478442994474328"
    },
    "ETH": {
        "condition_id": "0x34d1e361b687eb4e21195dc26fc4038eb7161a92c9808cab4a231db700518cd6",
        "yes_token": "788258604446295397235532874107583110586500769147124826906354098610006126507532",
        "no_token": "10541732733121203809508085133354500369364398888463402012720267766816224605314"
    }
}

def execute_real_trade(symbol="BTC", side="BUY", token_type="YES", amount_usd=1.0):
    """
    强制执行一笔真实订单
    """
    market = MARKETS.get(symbol)
    token_id = market["yes_token"] if token_type == "YES" else market["no_token"]
    
    logger.info(f"🚀 准备下单: {symbol} | 类型: {token_type} | 金额: {amount_usd}U")
    
    try:
        # 获取当前买一卖一价以确保订单成交 (这里演示直接下限价单)
        # 提示：实际操作中建议先 get_orderbook 确认价格，这里为了演示直接设一个极具竞争力的价格
        order_args = OrderArgs(
            price=0.99,   # 这里的价格需根据市场实际情况调整，0.99 几乎肯定成交（如果是买入）
            size=amount_usd,
            side=side,
            token_id=token_id,
        )
        
        # 下单
        resp = client.create_order(order_args)
        
        # 彻底解决之前的 'str' object 报错：先判断类型
        if isinstance(resp, str):
            logger.error(f"❌ API 返回错误字符串: {resp}")
            return
            
        if resp.get("success"):
            logger.info(f"✅ 【真实下单成功】 订单ID: {resp.get('orderID')}")
        else:
            logger.warning(f"⚠️ 下单未成功: {resp}")
            
    except Exception as e:
        logger.error(f"🔥 运行时致命错误: {e}")

if __name__ == "__main__":
    # 立即对 BTC 市场下一单测试
    execute_real_trade(symbol="BTC", token_type="YES", amount_usd=1.0)
