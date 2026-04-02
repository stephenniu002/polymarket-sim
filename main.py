import os
import sys

# --- 核心修复：强制扫描虚拟环境路径 ---
# 获取当前目录下的虚拟环境 site-packages 路径
current_dir = os.getcwd()
venv_path = os.path.join(current_dir, ".venv", "lib", "python3.11", "site-packages")

# 只要路径存在，就把它插到搜索列表的第一位
if os.path.exists(venv_path):
    sys.path.insert(0, venv_path)
    print(f"✅ 已强插路径: {venv_path}")
else:
    # 尝试递归查找 site-packages (防止版本号对不上)
    import glob
    found_paths = glob.glob(os.path.join(current_dir, ".venv", "lib", "python*", "site-packages"))
    for p in found_paths:
        sys.path.insert(0, p)
        print(f"🔍 自动寻路成功: {p}")

# --- 现在尝试导入 ---
try:
    from clob_client.client import ClobClient
    print("🚀 ClobClient 导入成功！")
except ImportError:
    print(f"❌ 导入失败。当前 sys.path 为: {sys.path}")
    # 如果还是失败，最后尝试用 pip 现场补课（仅作为最后手段）
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "py-clob-client==0.34.6"])
    from clob_client.client import ClobClient

import asyncio
import logging
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from eth_account import Account

# 配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

CONFIG = {
    "PK": os.getenv("PK"),
    "TG_TOKEN": os.getenv("TG_TOKEN"),
    "CHAT_ID": os.getenv("CHAT_ID"),
    "CLOB_ENDPOINT": "https://clob.polymarket.com",
    "RPC_URL": "https://polygon-rpc.com",
    "USDC_ADDRESS": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "CHAIN_ID": 137
}

async def send_tg_msg(text):
    url = f"https://api.telegram.org/bot{CONFIG['TG_TOKEN']}/sendMessage"
    payload = {"chat_id": CONFIG['CHAT_ID'], "text": text, "parse_mode": "Markdown"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"TG 发送失败: {e}")

async def get_usdc_balance(wallet_address):
    payload = {
        "jsonrpc": "2.0", "method": "eth_call", "id": 1,
        "params": [{"to": CONFIG["USDC_ADDRESS"], "data": "0x70a08231000000000000000000000000" + wallet_address[2:]}, "latest"]
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(CONFIG["RPC_URL"], json=payload) as resp:
                result = await resp.json()
                return int(result["result"], 16) / 10**6 if "result" in result else 0.0
        except: return 0.0

async def run_bot():
    try:
        # 这里只是初始化，不涉及网络请求
        client = ClobClient(CONFIG["CLOB_ENDPOINT"], key=CONFIG["PK"], chain_id=CONFIG["CHAIN_ID"])
        account = Account.from_key(CONFIG["PK"])
        
        # 真正干活
        balance = await get_usdc_balance(account.address)
        
        msg = (
            f"💰 **环境已打通 - 余额查询成功**\n\n"
            f"🏠 地址: `{account.address[:6]}...{account.address[-4:]}`\n"
            f"💵 USDC: `{balance:.2f}`\n"
            f"⏰ 时间: {datetime.now().strftime('%H:%M:%S')}"
        )
        await send_tg_msg(msg)
        logger.info(f"查询成功: {balance}")
    except Exception as e:
        logger.error(f"报错了: {e}")
        await send_tg_msg(f"❌ 运行报错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_bot())
