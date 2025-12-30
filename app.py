import os
import sqlite3
from flask import Flask, Response, redirect
from pyrogram import Client

API_ID = 123456
API_HASH = "API_HASH"
BOT_TOKEN = "BOT_TOKEN"

tg = Client(
    "web",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
tg.start()

app = Flask(__name__)

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

@app.route("/watch/<vid>")
def watch(vid):
    return f"""
    <html>
    <body>
    <h3>Streaming Video</h3>
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
        return "Invalid video", 404

    vtype, value = data

    if vtype == "url":
        return redirect(value)

    file = tg.download_media(value, in_memory=True)
    return Response(file, mimetype="video/mp4")

# 🔴 RENDER PORT FIX
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)