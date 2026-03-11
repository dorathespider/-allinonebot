from pyrogram import Client
from pyrogram.types import Message
import auth

HELP_TEXT = """
🤖 **AllInOneBot — Commands**

📥 **Download**
/txt — TXT file se download karo
/html — TXT to HTML player page
/drm — Manual DRM video download

⚙️ **Settings**
/cookies — YouTube cookies upload
/getcookies — Current cookies dekho
/settoken — PW ya CP token set karo

👑 **Admin**
/add <id> — User add karo
/remove <id> — User remove karo
/users — Sab users dekho
/id — Chat/User ID dekho
/stop — Active task rokho
"""

async def start_handler(client: Client, message: Message):
    uid = message.from_user.id
    status = "✅ Authorized" if auth.is_auth(uid) else "❌ Not Authorized — Contact admin."
    await message.reply(
        f"👋 **Welcome to AllInOneBot!**\n\n"
        f"🔗 Supports ClassPlus, PW, Appx, WebSankul,\n"
        f"encrypted, broken, mixed — every format.\n\n"
        f"🔑 **Access:** {status}\n\n"
        f"Use /help to see all commands."
    )

async def help_handler(client: Client, message: Message):
    await message.reply(HELP_TEXT)

async def stop_handler(client: Client, message: Message):
    from plugins.txt_handler import active_tasks
    uid = message.from_user.id
    if uid in active_tasks:
        active_tasks[uid] = False
        await message.reply("⛔ Stop signal sent.")
    else:
        await message.reply("No active task found.")
