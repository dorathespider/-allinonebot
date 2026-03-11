"""
channel_auth.py — Channel join se auto user add
"""
from pyrogram.types import ChatMemberUpdated
import auth
from logger import LOGGER

async def channel_member_handler(client, update: ChatMemberUpdated):
    try:
        if update.new_chat_member and update.new_chat_member.status.value in ("member", "administrator"):
            uid = update.new_chat_member.user.id
            auth.add_user(uid)
            LOGGER.info(f"Auto-added user {uid} from channel")
    except Exception as e:
        LOGGER.error(f"Channel auth error: {e}")
