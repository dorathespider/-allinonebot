"""
main.py — AllInOneBot Entry Point (Clean Version)
"""
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler, ChatMemberUpdatedHandler
from aiohttp import web
from config import Config
from logger import LOGGER
import auth

# ── Web server for Railway/Render ─────────────────────────────
async def health_check(request):
    return web.Response(text="AllInOneBot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    LOGGER.info(f"✅ Web server started on port {port}")

# ── Bot client ─────────────────────────────────────────────────
bot = Client(
    "AllInOneBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=Config.WORKERS,
)

# ── Imports ────────────────────────────────────────────────────
from plugins.start       import start_handler, help_handler, stop_handler
from plugins.txt_handler import txt_handler
from plugins.html_handler import html_handler
from plugins.drm_handler import drm_handler
from plugins.channel_auth import channel_member_handler
from plugins.admin       import add_cmd, remove_cmd, users_cmd, settoken_cmd, cookies_cmd, getcookies_cmd, id_cmd

def register_handlers():
    bot.add_handler(MessageHandler(start_handler,  filters.command("start")   & filters.private))
    bot.add_handler(MessageHandler(help_handler,   filters.command("help")    & filters.private))
    bot.add_handler(MessageHandler(stop_handler,   filters.command("stop")    & filters.private))
    bot.add_handler(MessageHandler(txt_handler,    filters.command("txt")     & filters.private))
    bot.add_handler(MessageHandler(html_handler,   filters.command("html")    & filters.private))
    bot.add_handler(MessageHandler(drm_handler,    filters.command("drm")     & filters.private))
    bot.add_handler(MessageHandler(add_cmd,        filters.command("add")     & filters.private))
    bot.add_handler(MessageHandler(remove_cmd,     filters.command("remove")  & filters.private))
    bot.add_handler(MessageHandler(users_cmd,      filters.command("users")   & filters.private))
    bot.add_handler(MessageHandler(settoken_cmd,   filters.command("settoken") & filters.private))
    bot.add_handler(MessageHandler(cookies_cmd,    filters.command("cookies") & filters.private))
    bot.add_handler(MessageHandler(getcookies_cmd, filters.command("getcookies") & filters.private))
    bot.add_handler(MessageHandler(id_cmd,         filters.command("id")))
    # Channel auto-auth
    if Config.AUTH_CHANNEL:
        bot.add_handler(ChatMemberUpdatedHandler(channel_member_handler))
    LOGGER.info("✅ All handlers registered.")

async def main():
    os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
    register_handlers()
    LOGGER.info("🚀 Starting AllInOneBot...")
    await start_web_server()
    await bot.start()
    me = await bot.get_me()
    LOGGER.info(f"✅ Bot started as @{me.username} | {me.first_name}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
