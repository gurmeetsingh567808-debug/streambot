from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, uuid, re

API_ID = 123456
API_HASH = "API_HASH"
BOT_TOKEN = "BOT_TOKEN"

app = Client("streambot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# DB
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

# /stream command
@app.on_message(filters.command("stream"))
async def stream_cmd(client, message):
    # CASE 2: direct link
    if len(message.command) > 1:
        url = message.command[1]
        vid = str(uuid.uuid4())

        cursor.execute(
            "INSERT INTO videos VALUES (?, ?, ?)",
            (vid, "url", url)
        )
        db.commit()

        watch = f"https://YOUR-SITE.onrender.com/watch/{vid}"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Watch Online", url=watch)]]
        )

        await message.reply("🔴 Streaming link ready:", reply_markup=buttons)
        return

    # CASE 1: wait for video
    await message.reply(
        "🎬 Ab video bhejo jise stream karna hai.\n\n"
        "❗ Sirf is command ke baad hi video accept hogi."
    )

    app.listen(chat_id=message.chat.id, filters=filters.video, timeout=60)

# video after /stream
@app.on_message(filters.video)
async def handle_video(client, message):
    if not message.reply_to_message:
        return

    file_id = message.video.file_id
    vid = str(uuid.uuid4())

    cursor.execute(
        "INSERT INTO videos VALUES (?, ?, ?)",
        (vid, "tg", file_id)
    )
    db.commit()

    watch = f"https://YOUR-SITE.onrender.com/watch/{vid}"
    download = f"https://YOUR-SITE.onrender.com/download/{vid}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Watch Online", url=watch)],
        [InlineKeyboardButton("⬇️ Download", url=download)]
    ])

    await message.reply("✅ Video stream ready:", reply_markup=buttons)

app.run()