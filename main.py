import asyncio
import websockets
import json
import logging
import time
import os

# ==========================================
# 1. 核心配置与导入 (对齐 config.py)
# ==========================================
try:
    from trade import execute_trade 
    from strategy import generate_signal
    from config import MARKET_MAP, POLY_ADDRESS
    logging.info("✅ 配置文件 [config.py] 加载成功")
except ImportError as e:
    logging.error(f"❌ 导入失败: {e}。请确认 config.py 中有 MARKET_MAP 变量。")
    MARKET_MAP = {}
    POLY_ADDRESS = "0xd962C11e253e38EB86303F1462818c4aac17CB24"

# 日志格式
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ⚠️ 修复 404 的核心：添加末尾斜杠 / 或 v1 路径
WS_URL = "wss://clob.polymarket.com/ws/" 

# ==========================================
# 2. 资产 ID 预处理 (对齐 UP/DOWN 键)
# ==========================================
WATCH_TOKENS = []
for m in MARKET_MAP.values():
    if "UP" in m: WATCH_TOKENS.append(m["UP"])
    if "DOWN" in m: WATCH_TOKENS.append(m["DOWN"])

# 状态缓存
markets_state = {}
cooldowns = {}
COOLDOWN_SECONDS = 20 

# ==========================================
# 3. 核心事件处理器
# ==========================================
async def handle_market_event(market_id, state):
    now = time.time()

    # 冷却与数据完整性检查
    if market_id in cooldowns and now - cooldowns[market_id] < COOLDOWN_SECONDS:
        return
    
    if not state.get("last_price") or not state.get("last_token"):
        return

    # 信号生成 (strategy.py)
    signal = generate_signal(state)
    if not signal:
        return

    # 匹配币种符号
    symbol = "UNKNOWN"
    token_id = state["last_token"]
    for k, v in MARKET_MAP.items():
        if token_id in [v.get("UP"), v.get("DOWN")]:
            symbol = k
            break
    
    # 强度计算 (成交密度)
    strength = min(len(state.get("trades", [])) / 30, 1.0)
    
    logging.info(f"🎯 [SIGNAL] {symbol} | {signal} | 价格: {state['last_price']} | 强度: {strength:.2f}")
    
    # 执行下单 (trade.py)
    execute_trade(symbol, token_id, signal, state["last_price"], strength)

    cooldowns[market_id] = now

# ==========================================
# 4. WebSocket 链接引擎 (修复 404)
# ==========================================
async def run_lobster_ws():
    logging.info(f"🚀 龙虾系统启动 | 监听钱包: {POLY_ADDRESS}")
    
    if not WATCH_TOKENS:
        logging.error("❌ 监听列表为空！请检查 config.py")
        return

    # 伪装 Header 绕过某些反爬策略
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    while True:
        try:
            async with websockets.connect(WS_URL, extra_headers=headers) as ws:
                logging.info("✅ WebSocket 连接成功 [101 Switching Protocols]")
                
                # 订阅消息
                subscribe_msg = {
                    "type": "subscribe",
                    "channels": ["trades"],
                    "tokens": WATCH_TOKENS
                }
                await ws.send(json.dumps(subscribe_msg))
                logging.info(f"📡 订阅已发送: 正在监控 {len(WATCH_TOKENS)} 个 Token")

                async for msg in ws:
