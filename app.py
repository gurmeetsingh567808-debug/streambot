import os
import time
import uuid
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.environ["BOT_TOKEN"]
BASE_URL = os.environ["RENDER_EXTERNAL_URL"]

STREAM_TIMEOUT = 30
STREAM_WAIT = {}   # user_id : timestamp
VIDEOS = {}        # vid : file_id

# ================= BOT HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot is running\n\n"
        "Use /stream and then send ONE video (within 30 sec)"
    )

async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STREAM_WAIT[update.effective_user.id] = time.time()
    await update.message.reply_text("🎬 Send one video within 30 seconds")

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in STREAM_WAIT:
        return

    if time.time() - STREAM_WAIT[uid] > STREAM_TIMEOUT:
        STREAM_WAIT.pop(uid, None)
        await update.message.reply_text("⏱️ Timeout. Use /stream again")
        return

    STREAM_WAIT.pop(uid, None)

    vid = str(uuid.uuid4())
    VIDEOS[vid] = update.message.video.file_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Watch Online", url=f"{BASE_URL}/watch/{vid}")],
        [InlineKeyboardButton("⬇️ Download", url=f"{BASE_URL}/download/{vid}")]
    ])

    await update.message.reply_text("✅ Video ready", reply_markup=keyboard)

# ================= FLASK + WEBHOOK =================

app = Flask(__name__)

application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stream", stream))
application.add_handler(MessageHandler(filters.VIDEO, video))

@app.route("/", methods=["GET"])
def home():
    return "Bot is running ✅"

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# ================= RUN =================

if __name__ == "__main__":
    application.bot.set_webhook(f"{BASE_URL}/webhook")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))