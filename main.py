# ... 前面 import 部分保持不变 ...

# ================= 环境变量 =================
# 建议加上 POLY_PRIVATE_KEY 的兼容，防止 Railway 变量名填错
PK = os.getenv("PRIVATE_KEY") or os.getenv("POLY_PRIVATE_KEY")
FUNDER = os.getenv("Funder") or os.getenv("POLY_ADDRESS")

if not PK or not PK.startswith("0x"):
    raise Exception("🛑 PRIVATE_KEY 未正确配置（必须0x开头）")

# 防止 FUNDER 为空导致切片报错 [:10]
addr_log = FUNDER[:10] if FUNDER else "未知地址"
logging.info(f"🔗 正在为地址 {addr_log}... 激活链路...")

# ================= 客户端 =================
client = ClobClient(
    host="https://clob.polymarket.com",
    key=PK,
    chain_id=137,
    funder=FUNDER
)

# 🔥 核心修复：手动注入 Signer
client.signer = Signer(PK, chain_id=137)

# ================= 余额获取（加固版） =================
async def get_balance():
    try:
        # 优先使用 get_user_balances (复数版)，它能返回详细资产列表
        res = await asyncio.to_thread(client.get_user_balances)
        
        # Polymarket 账户里通常有多种资产，我们要找 collateral (通常是 USDC)
        if isinstance(res, list):
            for asset in res:
                if asset.get("asset_type") == "collateral":
                    return float(asset.get("balance", 0))
        
        # 备选方案：单数版接口
        if hasattr(client, "get_balance"):
            res = await asyncio.to_thread(client.get_balance)
            return float(res.get("balance", 0))
            
        return 0.0
    except Exception as e:
        logging.error(f"❌ 余额解析失败 (可能钱包里没USDC): {e}")
        return -1

# ================= 初始化（增加凭证注入） =================
def init_engine():
    try:
        logging.info("🔧 V17.1 启动：标准初始化模式...")

        creds = client.create_or_derive_api_creds()
        if creds:
            client.set_api_creds(creds)
            # 补丁：显式注入，防止底层 SDK 没更新属性
            client.api_key = creds.api_key
            client.api_secret = creds.api_secret
            client.api_passphrase = creds.api_passphrase
        
        try:
            # 这一步在没有 USDC 时极易报错，我们捕获它
            client.update_balance_allowance()
        except Exception as e:
            logging.warning(f"⚠️ Allowance 刷新跳过 (通常因为USDC余额为0): {e}")

        logging.info("✅ 引擎初始化完成")
        return True

    except Exception as e:
        logging.error(f"❌ 引擎初始化失败: {e}")
        return False

# ... 后面 execute, step, main 保持你提供的逻辑不变 ...
