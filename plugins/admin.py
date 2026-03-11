"""
admin.py — Admin commands
"""
import os
from pyrogram import Client
from pyrogram.types import Message
from config import Config
from logger import LOGGER
import auth

# Token storage file
TOKEN_FILE = "tokens.json"

def _load_tokens():
    import json
    if os.path.exists(TOKEN_FILE):
        try:
            return json.load(open(TOKEN_FILE))
        except:
            return {}
    return {}

def _save_tokens(data):
    import json
    json.dump(data, open(TOKEN_FILE, "w"))

async def add_cmd(client: Client, message: Message):
    if not auth.is_owner(message.from_user.id):
        return await message.reply("❌ Only owner.")
    if len(message.command) < 2:
        return await message.reply("Usage: `/add <user_id>`")
    try:
        uid = int(message.command[1])
        auth.add_user(uid)
        await message.reply(f"✅ User `{uid}` added.")
    except ValueError:
        await message.reply("❌ Invalid user ID.")

async def remove_cmd(client: Client, message: Message):
    if not auth.is_owner(message.from_user.id):
        return await message.reply("❌ Only owner.")
    if len(message.command) < 2:
        return await message.reply("Usage: `/remove <user_id>`")
    try:
        uid = int(message.command[1])
        auth.remove_user(uid)
        await message.reply(f"✅ User `{uid}` removed.")
    except ValueError:
        await message.reply("❌ Invalid user ID.")

async def users_cmd(client: Client, message: Message):
    if not auth.is_owner(message.from_user.id):
        return await message.reply("❌ Only owner.")
    users = auth.get_all_users()
    if not users:
        return await message.reply("No authorized users.")
    text = f"**👥 Users ({len(users)})**\n\n"
    for u in users:
        text += f"• `{u}`\n"
    await message.reply(text)

async def settoken_cmd(client: Client, message: Message):
    if not auth.is_owner(message.from_user.id):
        return await message.reply("❌ Only owner.")
    if len(message.command) < 3:
        return await message.reply("Usage: `/settoken <pw|cp> <token>`")
    platform = message.command[1].lower()
    token = message.command[2]
    tokens = _load_tokens()
    tokens[platform] = token
    _save_tokens(tokens)
    await message.reply(f"✅ `{platform.upper()}` token saved.")

async def cookies_cmd(client: Client, message: Message):
    if not auth.is_owner(message.from_user.id):
        return await message.reply("❌ Only owner.")
    await message.reply("📎 Send your cookies.txt file now.")
    try:
        from pyromod import listen
        resp = await client.listen(message.chat.id, timeout=60)
        if resp.document:
            await resp.download("cookies.txt")
            await message.reply("✅ cookies.txt saved!")
        else:
            await message.reply("❌ No file received.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

async def getcookies_cmd(client: Client, message: Message):
    if not auth.is_owner(message.from_user.id):
        return await message.reply("❌ Only owner.")
    if os.path.exists("cookies.txt"):
        await message.reply_document("cookies.txt")
    else:
        await message.reply("No cookies.txt found.")

async def id_cmd(client: Client, message: Message):
    uid = message.from_user.id
    cid = message.chat.id
    await message.reply(f"👤 **User ID:** `{uid}`\n💬 **Chat ID:** `{cid}`")
