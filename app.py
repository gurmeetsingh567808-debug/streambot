import os
import uuid
import time
import sqlite3
from flask import Flask, Response, redirect
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== CONFIG ==================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# 🔐 ADMIN IDS (Telegram user IDs)
ADMINS = {
    6690196088,   # <-- apna Telegram user ID yahan daalo
}

STREAM_TIMEOUT = 30  # seconds

# ================== DATABASE ==================

db = sqlite3.connect("videos.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    type TEXT,
    value TEXT
)
""")
db.commit()

# ================== STATE ==================

# user_id : timestamp
STREAM_WAIT = {}

# ================== BOT ==================

tg = Client(
    "streambot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================== FLASK ==================

app = Flask(__name__)

# ================== BOT LOGIC ==================

@tg.on_message(filters.command("stream"))
async def stream_cmd(client, message):
    user_id = message.from_user.id

    # 🔐 Admin only
    if user_id not in ADMINS:
        await message.reply("❌ You are not allowed to use this command.")
        return

    # ❌ Already waiting (block multiple)
    if user_id in STREAM_WAIT:
        await message.reply("⚠️ Pehle wala /stream cancel hone do.")
        return

    # ⏱️ set waiting state
    STREAM_WAIT[user_id] = time.time()

    # CASE: direct link
    if len(message.command) > 1:
        url = message.command[1]
        vid = str(uuid.uuid4())

        cursor.execute(
            "INSERT INTO videos VALUES (?, ?, ?)",
            (vid, "url", url)
        )
        db.commit()

        STREAM_WAIT.pop(user_id, None)

        watch = f"{BASE_URL}/watch/{vid}"

        await message.reply(
            "▶️ Stream ready",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Watch Online", url=watch)]]
            )
        )
        return

    await message.reply("🎬 Ab 30 sec ke andar ek video bhejo")

@tg.on_message(filters.video)
async def video_handler(client, message):
    user_id = message.from_user.id

    # ❌ Not in stream mode
    if user_id not in STREAM_WAIT:
        return

    # ⏱️ Timeout check
    if time.time() - STREAM_WAIT[user_id] > STREAM_TIMEOUT:
        STREAM_WAIT.pop(user_id, None)
        await message.reply("⏱️ Timeout ho gaya. Dobara /stream use karo.")
        return

    # ✅ Accept only one video
    STREAM_WAIT.pop(user_id, None)

    vid = str(uuid.uuid4())
    file_id = message.video.file_id

    cursor.execute(
        "INSERT INTO videos VALUES (?, ?, ?)",
        (vid, "tg", file_id)
    )
    db.commit()

    watch = f"{BASE_URL}/watch/{vid}"
    download = f"{BASE_URL}/download/{vid}"

    await message.reply(
        "✅ Video ready",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Online", url=watch)],
            [InlineKeyboardButton("⬇️ Download", url=download)]
        ])
    )

# ================== WEBSITE ==================

@app.route("/watch/<vid>")
def watch(vid):
    return f"""
    <html>
    <body>
    <h3>Streaming</h3>
    <video controls width="100%">
        <source src="/stream/{vid}">
    </video>
    </body>
    </html>
    """

@app.route("/stream/<vid>")
def stream(vid):
    cursor.execute("SELECT type, value FROM videos WHERE id=?", (vid,))
    data = cursor.fetchone()

    if not data:
        return "Invalid link", 404

    vtype, value = data

    if vtype == "url":
        return redirect(value)

    file = tg.download_media(value, in_memory=True)
    return Response(file, mimetype="video/mp4")

@app.route("/download/<vid>")
def download(vid):
    cursor.execute("SELECT value FROM videos WHERE id=?", (vid,))
    file_id = cursor.fetchone()[0]
    path = tg.download_media(file_id)
    return open(path, "rb").read()

# ================== RUN ==================

if __name__ == "__main__":
    BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
    tg.start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)