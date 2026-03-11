"""
html_handler.py — /html command
─────────────────────────────────────────────────
TXT file → Beautiful HTML player page → send to user
Source: ITsGOLU html_handler.py (improved)
─────────────────────────────────────────────────
"""

import os
from pyrogram import Client
from pyrogram.types import Message
from pyromod import listen

import auth
from utils.link_detector import parse_txt_content
from utils.decryptor import decrypt_txt_content
from utils.html_gen import generate_html
from config import Config


async def html_handler(client: Client, message: Message):
    uid = message.from_user.id

    if not auth.is_auth(uid):
        return await message.reply("❌ Not authorized.")

    ask = await message.reply(
        "📂 **Send your TXT file** to generate an HTML player page.\n\n"
        "All video links will be playable in browser.\n"
        "PDFs will be directly openable.\n\n"
        "_Send /cancel to abort._"
    )

    try:
        txt_msg: Message = await client.listen(message.chat.id, timeout=120)
    except Exception:
        return await ask.edit("⏰ Timeout.")

    if txt_msg.text and txt_msg.text.strip() == "/cancel":
        return await ask.edit("❌ Cancelled.")

    if not txt_msg.document or not txt_msg.document.file_name.endswith(".txt"):
        return await ask.edit("❌ Please send a valid .txt file.")

    await ask.edit("⚙️ Generating HTML page...")

    txt_path = await txt_msg.download()
    filename = os.path.splitext(txt_msg.document.file_name)[0]

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    content = decrypt_txt_content(raw)
    items   = parse_txt_content(content)

    if not items:
        os.remove(txt_path)
        return await ask.edit("❌ No valid links found.")

    html_content = generate_html(filename, items, Config.CREDIT)
    html_path    = txt_path.replace(".txt", ".html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    videos = sum(1 for i in items if "m3u8" in i["url"].lower() or "mp4" in i["url"].lower()
                 or i["type"].name in ("CLASSPLUS_M3U8","M3U8","YOUTUBE","PW_CDN","MPD_NON_DRM"))
    pdfs   = sum(1 for i in items if i["type"].name == "PDF")

    await message.reply_document(
        html_path,
        caption=(
            f"🌐 **HTML Player Ready!**\n\n"
            f"📦 `{filename}`\n"
            f"🎬 Videos: `{videos}` | 📄 PDFs: `{pdfs}`\n"
            f"🔗 Total Links: `{len(items)}`\n\n"
            f"⚡ _by {Config.CREDIT}_"
        )
    )

    os.remove(txt_path)
    os.remove(html_path)
    await ask.delete()
