import os, asyncio, logging, time, requests, traceback
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds

# --- 1. 基础日志配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 全局客户端占位
client = None

def init_v17_1():
    global client
    try:
        logging.info("🔧 V17.1 启动：深度属性注入模式...")
        
        # --- 变量对齐：严格匹配你的 Railway 截图 ---
        pk = os.getenv("POLY_PRIVATE_KEY")
        funder = os.getenv("POLY_ADDRESS")
        api_key = os.getenv("POLY_API_KEY")
        api_secret = os.getenv("POLY_SECRET")
        api_pass = os.getenv("POLY_PASSPHRASE")

        # 1. 预检变量是否存在
        if not all([pk, funder, api_key, api_secret, api_pass]):
            logging.error("❌ 严重错误：Railway 变量读取不全！")
            logging.error(f"检查状态: PK:{bool(pk)}, Addr:{bool(funder)}, Key:{bool(api_key)}")
            return False

        # 2. 实例化客户端
        # 注意：这里必须传入正确的 chain_id (Polygon 是 137)
        client = ClobClient(
            host="https://clob.polymarket.com", 
            key=pk, 
            chain_id=137, 
            funder=funder
        )

        # 3. 构造并注入 ApiCreds
        creds = ApiCreds(
            api_key=api_key, 
            api_secret=api_secret, 
            api_passphrase=api_pass
        )
        
        # 强制补全 SDK 内部可能遗失的 signature_type (2 代表常规钱包)
        creds.signature_type = 2
        client.set_api_creds(creds)
        
        # 强制同步内部属性，防止 SDK 内部逻辑因变量名大小写导致 NoneType
        client.funder = funder
        client.chain_id = 137
        
        # 4. 激活链路
        logging.info(f"🔗 正在为地址 {funder[:10]}... 激活链路...")
        client.update_balance_allowance()
        
        logging.info("✅ 链路已激活 (深度注入模式)")
        return True
    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        logging.error(traceback.format_exc()) # 打印具体的报错行数
        return False

# --- 3. 交易循环 ---
async def main():
    logging.info("🚀 polymarket-sim: V17.1 (全变量对齐版) 启动")
    
    # 执行初始化
    if not init_v17_1():
        logging.critical("🛑 初始化失败，程序退出。请检查 Railway 环境变量！")
        return

    while True:
        try:
            # 使用 asyncio 运行同步库方法获取余额
            resp = await asyncio.to_thread(client.get_balance)
            
            # 处理不同版本的返回格式
            if isinstance(resp, dict):
                balance = float(resp.get("balance", 0))
            else:
                balance = float(resp)
                
            logging.info(f"💰 实时余额: {balance} USDC.e")
            
            # 每 5 分钟轮询一次
            await asyncio.sleep(300)
        except Exception as e:
            logging.error(f"⚠️ 守护异常: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 机器人已手动停止")
