"""
txt_handler.py — /txt command  ─ v2
──────────────────────────────────────────────────────────────────────────
Major update:
- CW token support (for Brightcove)
- Watermark on thumbnail (ITsGOLU send_vid logic)
- Audio / ZIP / WS file upload support
- Stats counter: pdf / img / video / zip / audio / failed
- Auto thumbnail generation with ffmpeg + watermark overlay
- ITsGOLU caption style
──────────────────────────────────────────────────────────────────────────
"""

import os
import re
import time
import asyncio
import subprocess
from pyrogram import Client
from pyrogram.types import Message
from pyromod import listen

from config import Config
from logger import LOGGER
import auth

from utils.link_detector import parse_txt_content, LinkType
from utils.decryptor import decrypt_txt_content
from utils.downloader import download_by_type, split_large_video, get_duration
from utils.progress import progress_bar, humanbytes

QUALITY_OPTIONS = {
    "1": "144", "2": "240", "3": "360",
    "4": "480", "5": "720", "6": "1080", "7": "best"
}

# active download flags per user
active_tasks: dict[int, bool] = {}

# ── VIDEO extensions ──────────────────────────────────────────────────────────
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".flv", ".avi", ".mov"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def gen_thumb_with_watermark(video_path: str, uid: int, watermark: str = "") -> str | None:
    """
    Generate thumbnail from video + optional watermark overlay.
    ITsGOLU send_vid logic — exact implementation.
    """
    os.makedirs("downloads", exist_ok=True)
    thumb = f"downloads/thumb_{uid}.jpg"

    # Extract frame at 10s
    subprocess.run(
        f'ffmpeg -i "{video_path}" -ss 00:00:10 -vframes 1 -q:v 2 -y "{thumb}"',
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    if not os.path.exists(thumb):
        return None

    # Apply watermark if given
    if watermark and watermark.strip() and watermark.strip() != "/d":
        text = watermark.strip()
        try:
            probe = subprocess.check_output(
                f'ffprobe -v error -select_streams v:0 -show_entries stream=width '
                f'-of csv=p=0:s=x "{thumb}"',
                shell=True, stderr=subprocess.DEVNULL
            ).decode().strip()
            img_w = int(probe.split("x")[0]) if "x" in probe else int(probe)
        except Exception:
            img_w = 1280

        base_size  = max(28, int(img_w * 0.075))
        text_len   = len(text)
        font_size  = (int(base_size * 1.25) if text_len <= 3 else
                      int(base_size * 1.0)  if text_len <= 8 else
                      int(base_size * 0.85) if text_len <= 15 else
                      int(base_size * 0.7))
        font_size  = max(32, min(font_size, 120))
        box_h      = max(60, int(font_size * 1.6))
        safe_text  = text.replace("'", "\\'")

        text_cmd = (
            f'ffmpeg -i "{thumb}" -vf '
            f'"drawbox=y=0:color=black@0.35:width=iw:height={box_h}:t=fill,'
            f'drawtext=fontfile=font.otf:text=\'{safe_text}\':fontcolor=white:'
            f'fontsize={font_size}:x=(w-text_w)/2:y=(({box_h})-text_h)/2" '
            f'-c:v mjpeg -q:v 2 -y "{thumb}"'
        )
        subprocess.run(text_cmd, shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return thumb if os.path.exists(thumb) else None


async def txt_handler(client: Client, message: Message):
    uid = message.from_user.id

    if not auth.is_auth(uid):
        return await message.reply(
            "❌ **You are not authorized.**\nContact admin to get access."
        )

    if active_tasks.get(uid):
        return await message.reply("⚠️ Active task running. Use /stop to cancel first.")

    # ── Step 1: TXT file ─────────────────────────────────────────
    ask = await message.reply(
        "📂 **Send your TXT file.**\n\n"
        "Supported link types:\n"
        "• ClassPlus M3U8 / DRM / Vimeo\n"
        "• PW CloudFront / Akamai\n"
        "• Appx CDN variants + Encrypted\n"
        "• CW Brightcove / cwmediabkt\n"
        "• YouTube / Instagram / GDrive\n"
        "• M3U8 / MPD / MP4 / MKV / .cdn\n"
        "• PDF / Image / Audio / ZIP\n"
        "• `helper://` encrypted\n"
        "• VisionIAS / Utkarsh / Guidely\n\n"
        "_/cancel to abort_"
    )
    try:
        txt_msg: Message = await client.listen(message.chat.id, timeout=120)
    except Exception:
        return await ask.edit("⏰ Timeout. Send /txt again.")

    if txt_msg.text and txt_msg.text.strip() == "/cancel":
        return await ask.edit("❌ Cancelled.")

    if not txt_msg.document or not txt_msg.document.file_name.endswith(".txt"):
        return await ask.edit("❌ Send a valid **.txt** file.")

    await ask.edit("⬇️ Reading TXT...")
    txt_path = await txt_msg.download()

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    content = decrypt_txt_content(raw)
    items   = parse_txt_content(content)

    if not items:
        os.remove(txt_path)
        return await ask.edit("❌ No valid links found in TXT.")

    # Stats
    def count_type(types):
        return sum(1 for i in items if i["type"] in types)

    n_total = len(items)
    n_vid   = count_type({LinkType.M3U8, LinkType.MPD_NON_DRM, LinkType.MPD_DRM,
                           LinkType.MP4_DIRECT, LinkType.MKV_DIRECT, LinkType.CDN_VIDEO,
                           LinkType.WEBM_DIRECT, LinkType.CLASSPLUS_M3U8, LinkType.CLASSPLUS_DRM,
                           LinkType.CLASSPLUS_VIMEO, LinkType.CLASSPLUS_TESTBOOK, LinkType.CLASSPLUS_WEB,
                           LinkType.APPX_TRANS_V1, LinkType.APPX_TRANS_V2, LinkType.APPX_REC,
                           LinkType.APPX_WSB, LinkType.APPX_DB, LinkType.APPX_DB_V2,
                           LinkType.APPX_ENCRYPTED, LinkType.APPX_GENERIC,
                           LinkType.PW_CDN, LinkType.PW_SEC1, LinkType.PW_AKAMAI,
                           LinkType.CW_BRIGHTCOVE, LinkType.UTKARSH_JW, LinkType.ACE_CW_PLAY,
                           LinkType.VISION_IAS, LinkType.YOUTUBE, LinkType.YOUTUBE_EMBED,
                           LinkType.INSTAGRAM, LinkType.GDRIVE, LinkType.GUIDELY})
    n_pdf   = count_type({LinkType.PDF, LinkType.WEBSANKUL, LinkType.CW_MEDIABKT})
    n_img   = count_type({LinkType.IMAGE})
    n_audio = count_type({LinkType.AUDIO})
    n_zip   = count_type({LinkType.ZIP_FILE})
    n_mpd   = count_type({LinkType.MPD_DRM, LinkType.MPD_NON_DRM})
    n_m3u8  = count_type({LinkType.M3U8, LinkType.CLASSPLUS_M3U8})
    n_mkv   = count_type({LinkType.MKV_DIRECT, LinkType.CDN_VIDEO, LinkType.APPX_TRANS_V1,
                           LinkType.APPX_TRANS_V2, LinkType.APPX_GENERIC})

    await ask.edit(
        f"✅ **Parsed {n_total} links**\n\n"
        f"```\n"
        f"🎬 Videos  : {n_vid}\n"
        f"📀 M3U8    : {n_m3u8}\n"
        f"📦 MPD     : {n_mpd}\n"
        f"🎞️  MKV/CDN : {n_mkv}\n"
        f"📄 PDFs    : {n_pdf}\n"
        f"🖼️  Images  : {n_img}\n"
        f"🎵 Audio   : {n_audio}\n"
        f"🗜️  ZIP     : {n_zip}\n"
        f"```"
    )
    await asyncio.sleep(1.5)

    # ── Step 2: Start index ───────────────────────────────────────
    q0 = await message.reply(
        f"🔢 **Start from which index?** (1 to {n_total})\nSend `1` to start from beginning:"
    )
    try:
        r0 = await client.listen(message.chat.id, timeout=20)
        start_idx = max(1, int(r0.text.strip())) - 1
    except Exception:
        start_idx = 0
    await q0.delete()

    # ── Step 3: Batch name ────────────────────────────────────────
    q1 = await message.reply("📝 **Batch Name** (or send `/d` for filename):")
    try:
        r1 = await client.listen(message.chat.id, timeout=20)
        raw1 = r1.text.strip() if r1.text else "/d"
    except Exception:
        raw1 = "/d"
    batch_name = os.path.splitext(txt_msg.document.file_name)[0].replace("_", " ") if raw1 == "/d" else raw1
    await q1.delete()

    # ── Step 4: Quality ───────────────────────────────────────────
    q2 = await message.reply(
        "🎥 **Quality:**\n"
        "`1` 144p | `2` 240p | `3` 360p\n"
        "`4` 480p | `5` 720p | `6` 1080p | `7` best"
    )
    try:
        r2 = await client.listen(message.chat.id, timeout=20)
        quality = QUALITY_OPTIONS.get(r2.text.strip(), "720")
    except Exception:
        quality = "720"
    await q2.delete()

    # ── Step 5: Watermark ─────────────────────────────────────────
    q3 = await message.reply("🔡 **Watermark text** (or `/d` for no watermark):")
    try:
        r3 = await client.listen(message.chat.id, timeout=20)
        watermark = "" if r3.text.strip() == "/d" else r3.text.strip()
    except Exception:
        watermark = ""
    await q3.delete()

    # ── Step 6: Credit ────────────────────────────────────────────
    q4 = await message.reply("✍️ **Credit name** (or `/d` for default):")
    try:
        r4 = await client.listen(message.chat.id, timeout=20)
        credit = Config.CREDIT if r4.text.strip() == "/d" else r4.text.strip()
    except Exception:
        credit = Config.CREDIT
    await q4.delete()

    # ── Step 7: Thumbnail ─────────────────────────────────────────
    q5 = await message.reply(
        "🖼 **Thumbnail:**\n"
        "• Send a photo\n"
        "• Send URL\n"
        "• `/d` for auto-generate\n"
        "• `/skip` for no thumbnail"
    )
    thumb_path   = None
    use_auto_thumb = False
    try:
        r5 = await client.listen(message.chat.id, timeout=30)
        if r5.photo:
            os.makedirs("downloads", exist_ok=True)
            thumb_path = f"downloads/thumb_{uid}.jpg"
            await client.download_media(r5.photo, file_name=thumb_path)
        elif r5.text:
            t = r5.text.strip()
            if t == "/d":
                use_auto_thumb = True
            elif t == "/skip":
                thumb_path = None
            elif t.startswith("http"):
                import aiohttp, aiofiles
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(t) as resp:
                        if resp.status == 200:
                            os.makedirs("downloads", exist_ok=True)
                            thumb_path = f"downloads/thumb_{uid}.jpg"
                            async with aiofiles.open(thumb_path, "wb") as tf:
                                await tf.write(await resp.read())
    except Exception:
        use_auto_thumb = True
    await q5.delete()

    # ── Step 8: Channel ───────────────────────────────────────────
    q6 = await message.reply("📡 **Channel ID** to upload (or `/d` for this chat):\nEx: `-100xxxxxxxxxx`")
    try:
        r6 = await client.listen(message.chat.id, timeout=30)
        raw6 = r6.text.strip()
        upload_chat = message.chat.id if raw6 == "/d" else int(raw6)
    except Exception:
        upload_chat = message.chat.id
    await q6.delete()

    # ── Tokens from DB ────────────────────────────────────────────
    pw_token = await db.get_user_token(uid, "pw") or Config.PW_TOKEN
    cp_token = await db.get_user_token(uid, "cp") or Config.CP_TOKEN
    cw_token = tokens.get("cw", "")
    cookies  = "youtube_cookies.txt" if os.path.exists("youtube_cookies.txt") else ""

    # ── Start processing ─────────────────────────────────────────
    active_tasks[uid] = True
    failed_links      = []
    dl_path           = f"downloads/{uid}"
    os.makedirs(dl_path, exist_ok=True)

    prog = await message.reply(
        f"🚀 **Task Started!**\n\n"
        f"📦 `{batch_name}` | 🎯 `{n_total}` links\n"
        f"🎥 Quality: `{quality}p` | Start: `{start_idx + 1}`\n"
        f"📡 Uploading to: `{upload_chat}`"
    )

    done = 0
    for idx, item in enumerate(items[start_idx:], start=start_idx + 1):
        if not active_tasks.get(uid):
            await prog.edit("⛔ **Task stopped.**")
            break

        name  = item["name"]
        url   = item["url"]
        ltype = item["type"]

        if ltype in (LinkType.TELEGRAM_LINK, LinkType.BROKEN):
            failed_links.append(f"[SKIP] {name}: {url}")
            continue

        await prog.edit(
            f"⏳ **{idx}/{n_total}** | ✅ `{done}` | ❌ `{len(failed_links)}`\n\n"
            f"📦 `{batch_name}`\n"
            f"📝 `{name[:60]}`\n"
            f"🔗 `{ltype.name}`"
        )

        # Download
        dl_file = await download_by_type(
            item, dl_path, quality,
            pw_token=pw_token, cp_token=cp_token,
            cw_token=cw_token, cookies=cookies
        )

        if not dl_file or not os.path.exists(dl_file):
            failed_links.append(f"[FAILED] {name}: {url}")
            LOGGER.warning(f"Download failed: {name}")
            continue

        # Caption (ITsGOLU style)
        cc = (
            f"<b>🏷️ Index :</b> {str(idx).zfill(3)}\n\n"
            f"<b>🎞️ Title :</b> {name}\n\n"
            f"<blockquote>📚 Batch : {batch_name}</blockquote>\n\n"
            f"<b>🎓 By : {credit}</b>"
        )

        # Upload
        try:
            ext = os.path.splitext(dl_file)[1].lower()
            up  = await message.reply("📤 Uploading...")
            t   = time.time()

            if ext in VIDEO_EXTS:
                # Auto-generate thumbnail if needed
                actual_thumb = thumb_path
                if use_auto_thumb:
                    actual_thumb = gen_thumb_with_watermark(dl_file, uid, watermark)

                parts = split_large_video(dl_file)
                for pi, part in enumerate(parts, 1):
                    part_cc = cc + (f"\n📁 Part {pi}/{len(parts)}" if len(parts) > 1 else "")
                    dur = int(get_duration(part))
                    try:
                        await client.send_video(
                            chat_id=upload_chat, video=part,
                            caption=part_cc, thumb=actual_thumb,
                            duration=dur, supports_streaming=True,
                            height=720, width=1280,
                            progress=progress_bar, progress_args=(up, t, "upload"),
                        )
                    except Exception:
                        await client.send_document(
                            chat_id=upload_chat, document=part, caption=part_cc,
                            progress=progress_bar, progress_args=(up, t, "upload"),
                        )
                    try:
                        os.remove(part)
                    except Exception:
                        pass

                # cleanup auto-thumb
                if use_auto_thumb and actual_thumb and os.path.exists(actual_thumb):
                    os.remove(actual_thumb)

            elif ext in IMAGE_EXTS:
                await client.send_photo(chat_id=upload_chat, photo=dl_file, caption=cc)
                os.remove(dl_file)

            elif ext in AUDIO_EXTS:
                await client.send_audio(chat_id=upload_chat, audio=dl_file, caption=cc,
                                         progress=progress_bar, progress_args=(up, t, "upload"))
                os.remove(dl_file)

            elif ext == ".zip":
                await client.send_document(chat_id=upload_chat, document=dl_file,
                                            caption=cc.replace("🎞️", "🗜️"),
                                            progress=progress_bar, progress_args=(up, t, "upload"))
                os.remove(dl_file)

            else:  # PDF / HTML / other docs
                await client.send_document(chat_id=upload_chat, document=dl_file,
                                            caption=cc.replace("🎞️", "📄"),
                                            thumb=thumb_path,
                                            progress=progress_bar, progress_args=(up, t, "upload"))
                try:
                    os.remove(dl_file)
                except Exception:
                    pass

            await up.delete()
            done += 1

        except Exception as e:
            LOGGER.error(f"Upload failed: {name} | {e}")
            failed_links.append(f"[UPLOAD_FAIL] {name}: {url}")
            try:
                os.remove(dl_file)
            except Exception:
                pass

    # ── Cleanup & report ─────────────────────────────────────────
    active_tasks.pop(uid, None)

    if failed_links:
        failed_path = f"downloads/failed_{uid}.txt"
        with open(failed_path, "w", encoding="utf-8") as f:
            f.write("\n".join(failed_links))
        await message.reply_document(
            failed_path,
            caption=f"❌ **{len(failed_links)} Failed Links**\n`{batch_name}`"
        )
        try:
            os.remove(failed_path)
        except Exception:
            pass

    try:
        os.remove(txt_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
    except Exception:
        pass

    success = done
    failed  = len(failed_links)
    await prog.edit(
        f"<b>📬 ᴘʀᴏᴄᴇꜱꜱ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>\n\n"
        f"<blockquote><b>📚 Batch :</b> {batch_name}</blockquote>\n"
        f"╭────────────────\n"
        f"├ 🖇️ Total : <code>{n_total}</code>\n"
        f"├ ✅ Done  : <code>{success}</code>\n"
        f"├ ❌ Failed: <code>{failed}</code>\n"
        f"╰────────────────\n\n"
        f"<i>by {credit}</i>"
    )
