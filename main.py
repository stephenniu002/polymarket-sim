import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs

# ================= 修正后的初始化逻辑 =================

# 1. 基础客户端初始化 (对应你的 PRIVATE_KEY)
client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.getenv("PRIVATE_KEY"),  # 修正：从 PK 改为 PRIVATE_KEY
    chain_id=137
)

# 2. 注入 API 凭证 (对应你的 POLY_ 系列变量)
try:
    client.set_api_creds(ApiCreds(
        api_key=os.getenv("POLY_API_KEY"),         # 对应云端 POLY_API_KEY
        api_secret=os.getenv("POLY_SECRET"),       # 对应云端 POLY_SECRET
        api_passphrase=os.getenv("POLY_PASSPHRASE") # 对应云端 POLY_PASSPHRASE
    ))
    logging.info("🔑 API 凭证（POLY_系列）已成功载入")
except Exception as e:
    logging.error(f"❌ 凭证设置失败，请检查 Railway 变量名: {e}")

# 3. 获取测试 Token ID (对应你的 TEST_TOKEN_ID)
BTC_TOKEN_ID = os.getenv("TEST_TOKEN_ID", "21742450893073934336504295323901415510006760017135962002521191060010041285427")
