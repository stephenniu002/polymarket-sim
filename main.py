import os, asyncio, json, logging, requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from contextlib import asynccontextmanager

# --- 🎯 1. 基础配置与风控 ---
CONTROL_KEY = os.getenv("CONTROL_KEY", "88888888")
TG_TOKEN = os.getenv("TG_TOKEN")
TRADES_LOG = "trades.json"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LobsterV7")

class BotState:
    is_locked = False
state = BotState()

# --- 🚀 2. Telegram 指令逻辑 ---
def get_markup():
    keyboard = [[InlineKeyboardButton("🔴 紧急停火", callback_data='STOP'),
                 InlineKeyboardButton("🟢 恢复作战", callback_data='START')],
                [InlineKeyboardButton("📊 刷新简报", callback_data='REFRESH')]]
    return InlineKeyboardMarkup(keyboard)

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦞 龙虾 Railway 指挥部已就绪：", reply_markup=get_markup())

async def tg_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cmd = query.data
    if cmd == 'STOP':
        state.is_locked = True
        await query.edit_message_text("🚫 指令下达：机器人已原地待命。", reply_markup=get_markup())
    elif cmd == 'START':
        state.is_locked = False
        await query.edit_message_text("🟢 指令下达：机器人已重新出击！", reply_markup=get_markup())
    elif cmd == 'REFRESH':
        # 这里可以加入读取 trades.json 的逻辑
        await query.edit_message_text("📊 正在统计战果...", reply_markup=get_markup())

# --- 🛰️ 3. FastAPI 接口 (供外部或自测) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时开启 Telegram 轮询
    if TG_TOKEN:
        tg_app = Application.builder().token(TG_TOKEN).build()
        tg_app.add_handler(CommandHandler("start", tg_start))
        tg_app.add_handler(CallbackQueryHandler(tg_button))
        tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_start))
        
        # 异步启动 TG 机器人
        await tg_app.initialize()
        await tg_app.start()
        asyncio.create_task(tg_app.updater.start_polling())
        logger.info("✅ Telegram 监听已在后台启动")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "online", "locked": state.is_locked}

@app.post("/control")
async def control(request: Request):
    data = await request.json()
    if data.get("key") != CONTROL_KEY: return {"msg": "Forbidden"}, 403
    cmd = data.get("cmd")
    if cmd == "STOP": state.is_locked = True
    elif cmd == "START": state.is_locked = False
    return {"msg": f"Action {cmd} executed"}
