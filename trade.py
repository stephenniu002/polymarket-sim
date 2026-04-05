import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===============================
# 核心修复：绕过参数名冲突
# ===============================
def get_lobster_client():
    # 1. 创建空实例 (不传可能报错的参数)
    try:
        c = ClobClient(host="https://clob.polymarket.com")
    except:
        c = ClobClient()
    
    # 2. 强行注入 2026 最新属性名
    c.host = "https://clob.polymarket.com"
    c.api_key = os.getenv("POLY_API_KEY")
    c.api_secret = os.getenv("POLY_SECRET")
    c.api_passphrase = os.getenv("POLY_PASSPHRASE")
    c.private_key = os.getenv("PRIVATE_KEY")
    c.chain_id = POLYGON
    return c

client = get_lobster_client()

# 尝试激活 API
try:
    # 部分版本需要，部分版本不需要
    if hasattr(client, 'derive_api_key'):
        client.derive_api_key()
        logging.info("✅ API 鉴权协议已激活")
except Exception as e:
    logging.warning(f"⚠️ API 激活尝试跳过: {e}")
