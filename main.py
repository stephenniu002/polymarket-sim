import os, asyncio, logging, json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from py_clob_client.client import ClobClient

# --- 🎯 1. 基础配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LobsterV7")

TG_TOKEN = os.getenv("TG_TOKEN")
CONTROL_KEY = os.getenv("CONTROL_KEY", "88888888")
PK = os.getenv("POLY_PRIVATE_KEY", "").replace("0x", "") # 自动剥离 0x
FUNDER = os.getenv("FUNDER_ADDRESS")

class BotState:
    is_locked = False # 初始锁定，手动解锁才开火
    client = None

state = BotState()

# --- 🛰️ 2. Polymarket 实盘初始化 ---
def init_poly():
    if not PK:
        logger.error("❌ 未检测到 POLY_PRIVATE_KEY，实盘模块不可用")
        return None
    try:
        # 默认使用 Polygon 主网 (Chain ID 137)
        client = ClobClient("https://clob.polymarket.com", key=PK, chain_id=137)
        if FUNDER:
            client.set_funder_address(FUNDER)
        logger.info("✅ Polymarket 客户端初始化成功")
        return client
    except Exception as e:
        logger.error(f"❌ Polymarket 初始化失败: {e}")
        return None

# --- 🚀 3. Telegram 指令逻辑 ---
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🚫 紧急停火", callback_data='STOP'),
         InlineKeyboardButton("⚔️ 恢复作战", callback_data='START')],
        [InlineKeyboardButton("📊 查看状态", callback_data='STATUS')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦞 龙虾指挥系统已上线！\n当前状态: " + ("🛑 停止中" if state.is_locked else "🟢 运行中"), 
                                   reply_markup=get_main_menu())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cmd = query.data
    
    if cmd == 'STOP':
        state.is_locked = True
        msg = "🚫 指令下达：已紧急停火！"
    elif cmd == 'START':
        state.is_locked = False
        msg = "⚔️ 指令下达：开始猎杀猎物！"
    else:
        msg = f"📊 状态: {'锁定' if state.is_locked else '出击中'}\n💰 账户: 已连接"

    await query.edit_message_text(msg, reply_markup=get_main_menu())

# --- 🔌 4. 后台启动任务 (解决 Railway 关停问题) ---
async def start_telegram():
    if not TG_TOKEN:
        logger.error("❌ 未检测到 TG_TOKEN，无法启动指挥部")
        return
    try:
        tg_app = Application.builder().token(TG_TOKEN).build()
        tg_app.add_handler(CommandHandler("start", tg_start))
        tg_app.add_handler(CallbackQueryHandler(handle_buttons))
        tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_start))
        
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
        logger.info("✅ Telegram 指挥部已成功连接！")
    except Exception as e:
        logger.error(f"❌ Telegram 连接崩溃: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 立即初始化 Polymarket
    state.client = init_poly()
    # 2. 异步启动 Telegram (不阻塞 FastAPI 端口)
    asyncio.create_task(start_telegram())
    yield

app = FastAPI(lifespan=lifespan)

# --- 🛡️ 5. API 接口 ---
@app.get("/")
async def health_check():
    return {"status": "active", "bot": "online", "locked": state.is_locked}

@app.post("/control")
async def api_control(request: Request):
    try:
        data = await request.json()
        if data.get("key") != CONTROL_KEY: return JSONResponse({"msg": "Forbidden"}, 403)
        cmd = data.get("cmd")
        if cmd == "STOP": state.is_locked = True
        elif cmd == "START": state.is_locked = False
        return {"msg": f"Action {cmd} executed via API"}
    except:
        return JSONResponse({"msg": "Invalid Request"}, 400)
