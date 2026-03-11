"""
drm_handler.py — /drm command
─────────────────────────────────────────────────────────────────
Manual DRM video download:
User deta hai → MPD URL + Kid:Key → decrypt → upload

Source: NarujatDRM-Bot-2 (best DRM flow)
─────────────────────────────────────────────────────────────────
"""

import os
import time
from pyrogram import Client
from pyrogram.types import Message
from pyromod import listen

import auth
from utils.downloader import download_mpd_drm, download_mpd_non_drm, split_large_video, get_duration
from utils.progress import progress_bar
from config import Config
from logger import LOGGER


async def drm_handler(client: Client, message: Message):
    uid = message.from_user.id

    if not auth.is_auth(uid):
        return await message.reply("❌ Not authorized.")

    # ── Ask MPD URL ───────────────────────────────────────────────
    q1 = await message.reply(
        "🔐 **DRM Video Downloader**\n\n"
        "**Step 1/4:** Send the **MPD URL**\n"
        "_(e.g. https://....mpd)_"
    )
    try:
        r1 = await client.listen(message.chat.id, timeout=60)
        mpd_url = r1.text.strip()
    except Exception:
        return await q1.edit("⏰ Timeout.")
    await q1.delete()

    # ── Ask video name ────────────────────────────────────────────
    q2 = await message.reply("**Step 2/4:** Enter **Video Name**:")
    try:
        r2   = await client.listen(message.chat.id, timeout=60)
        name = r2.text.strip()
    except Exception:
        name = "DRM_Video"
    await q2.delete()

    # ── Ask quality ───────────────────────────────────────────────
    q3 = await message.reply(
        "**Step 3/4:** Select **Quality**:\n\n"
        "`144` `240` `360` `480` `720` `1080`\n"
        "_(send number or send `best`)_"
    )
    try:
        r3      = await client.listen(message.chat.id, timeout=30)
        quality = r3.text.strip() or "720"
    except Exception:
        quality = "720"
    await q3.delete()

    # ── Ask DRM keys ──────────────────────────────────────────────
    q4 = await message.reply(
        "**Step 4/4:** Send **DRM Keys** _(or send `.` to auto-fetch)_\n\n"
        "Format: `kid1:key1 kid2:key2`\n"
        "Multiple keys space-separated."
    )
    try:
        r4   = await client.listen(message.chat.id, timeout=60)
        keys = "" if r4.text.strip() == "." else r4.text.strip()
    except Exception:
        keys = ""
    await q4.delete()

    # ── Download ──────────────────────────────────────────────────
    status = await message.reply(
        f"⚙️ **Processing DRM Video...**\n\n"
        f"📝 `{name}`\n"
        f"🎥 Quality: `{quality}p`\n"
        f"🔑 Keys: `{'Manual' if keys else 'Auto-fetch'}`"
    )

    path   = f"downloads/{uid}_drm"
    result = await download_mpd_drm(mpd_url, name, path, quality, keys)

    if not result or not os.path.exists(result):
        return await status.edit("❌ Download failed. Check URL or keys.")

    # ── Upload ────────────────────────────────────────────────────
    await status.edit("📤 Uploading to Telegram...")
    parts = split_large_video(result)

    for i, part in enumerate(parts, 1):
        caption = (
            f"🎬 **{name}**\n"
            f"🔐 DRM Decrypted\n"
            f"🎥 Quality: `{quality}p`\n"
            + (f"📁 Part {i}/{len(parts)}\n" if len(parts) > 1 else "")
            + f"⚡ _by {Config.CREDIT}_"
        )
        try:
            dur = int(get_duration(part))
            t   = time.time()
            up  = await message.reply("📤 Uploading part...")
            await client.send_video(
                chat_id=message.chat.id,
                video=part,
                caption=caption,
                duration=dur,
                supports_streaming=True,
                progress=progress_bar,
                progress_args=(up, t, "upload"),
            )
            await up.delete()
        except Exception as e:
            LOGGER.error(f"DRM upload failed: {e}")
        finally:
            try:
                os.remove(part)
            except Exception:
                pass

    await status.delete()
