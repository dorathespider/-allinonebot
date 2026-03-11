"""
progress.py
─────────────────────────────────────────────────────────
Upload/Download progress bar for Telegram messages.
ITsGOLU + Saini-txt repos se combine kiya.
─────────────────────────────────────────────────────────
"""

import time
import math


def humanbytes(size: int) -> str:
    if not size:
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {units[i]}"


def time_formatter(seconds: int) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes   = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


async def progress_bar(current: int, total: int, message, start_time: float, action: str = ""):
    """
    Pyrogram upload/download progress callback.
    """
    try:
        now     = time.time()
        elapsed = now - start_time

        if elapsed < 1:
            return

        percent  = current * 100 / total
        speed    = current / elapsed if elapsed > 0 else 0
        eta      = (total - current) / speed if speed > 0 else 0

        filled   = int(percent / 5)
        bar      = "█" * filled + "░" * (20 - filled)

        text = (
            f"**{'📤 Uploading' if 'up' in action.lower() else '📥 Downloading'}**\n\n"
            f"`[{bar}]` **{percent:.1f}%**\n\n"
            f"**Done:** `{humanbytes(current)}` / `{humanbytes(total)}`\n"
            f"**Speed:** `{humanbytes(int(speed))}/s`\n"
            f"**ETA:** `{time_formatter(int(eta))}`"
        )

        await message.edit(text)
    except Exception:
        pass
