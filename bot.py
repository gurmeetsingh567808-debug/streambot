import os
import uuid
import time
import sqlite3
import asyncio
from flask import Flask, Response, redirect
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== CONFIG ==================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

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

STREAM_WAIT = {}  # user_id : timestamp

# ================== TELEGRAM BOT ==================

tg = Client(
    "streambot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@tg.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply(
        "✅ Bot is running\n\n"
        "Use /stream and then send ONE video (within 30 sec)"
    )

@tg.on_message(filters.command("stream"))
async def stream_cmd(client, message):
    user_id = message.from_user.id

    if user_id in STREAM_WAIT:
        await message.reply("⚠️ Already waiting for a video.")
        return

    STREAM_WAIT[user_id] = time.time()
    await message.reply("🎬 Send one video within 30 seconds")

@tg.on_message(filters.video)
async def video_handler(client, message):
    user_id = message.from_user.id

    if user_id not in STREAM_WAIT:
        return

    if time.time() - STREAM_WAIT[user_id] > STREAM_TIMEOUT:
        STREAM_WAIT.pop(user_id, None)
        await message.reply("⏱️ Timeout. Use /stream again.")
        return

    STREAM_WAIT.pop(user_id, None)

    vid = str(uuid.uuid4())
    file_id = message.video.file_id

    cursor.execute(
        "INSERT INTO videos VALUES (?, ?, ?)",
        (vid, "tg", file_id)
    )
    db.commit()

    base = os.environ.get("RENDER_EXTERNAL_URL", "")
    watch = f"{base}/watch/{vid}"
    download = f"{base}/download/{vid}"

    await message.reply(
        "✅ Video ready",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Watch Online", url=watch)],
            [InlineKeyboardButton("⬇️ Download", url=download)]
        ])
    )

# ================== FLASK APP ==================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

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
    row = cursor.fetchone()

    if not row:
        return "Invalid link", 404

    vtype, value = row

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

# ================== RUN BOTH ==================

async def main():
    await tg.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())