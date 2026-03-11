"""
downloader.py  ─ v2
──────────────────────────────────────────────────────────────────
Sab link types handle karta hai.
Major update: Appx CDN transforms, CW Brightcove, cipher/encrypted,
Utkarsh JW, .mkv, .cdn, acecwply, visionias, audio, zip, gdrive.

Source: ITsGOLU main.py + itsgolu.py (best parts taken)
──────────────────────────────────────────────────────────────────
"""

import os
import re
import asyncio
import aiohttp
import aiofiles
import subprocess
import requests
import cloudscraper
from math import ceil
from pathlib import Path
from logger import LOGGER
from config import Config
from utils.link_detector import LinkType

# ITsGOLU CP API endpoint
CP_API     = "https://itsgolu-cp-api.vercel.app/itsgolu"
# Master API (fallback)
MASTER_API = "http://master-api-v3.vercel.app/"

# CW token for Brightcove (set via /settoken cw)
CW_TOKEN_DEFAULT = ""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_duration(filepath: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        return float(r.stdout)
    except Exception:
        return 0.0


def split_large_video(file_path: str, max_mb: int = None) -> list[str]:
    """
    Split file > max_mb into parts using ffmpeg.
    Taken from ITsGOLU itsgolu.py — best implementation.
    """
    max_mb    = max_mb or Config.MAX_VIDEO_SIZE_MB
    max_bytes = max_mb * 1024 * 1024
    size      = os.path.getsize(file_path)

    if size <= max_bytes:
        return [file_path]

    duration  = get_duration(file_path)
    parts     = ceil(size / max_bytes)
    part_dur  = duration / parts
    base      = file_path.rsplit(".", 1)[0]
    outputs   = []

    for i in range(parts):
        out = f"{base}_part{i + 1}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path,
             "-ss", str(int(part_dur * i)),
             "-t",  str(int(part_dur)),
             "-c",  "copy", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if os.path.exists(out):
            outputs.append(out)

    return outputs or [file_path]


def sanitize(name: str) -> str:
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '{', '}', '(', ')', '\t']:
        name = name.replace(ch, '_')
    return name.strip()[:100]


def run(cmd: str) -> tuple[int, str]:
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode() + p.stderr.decode()


# ─── Appx CDN URL Transforms (ITsGOLU main.py exact logic) ───────────────────

def transform_appx_url(url: str, ltype: LinkType) -> tuple[str, str]:
    """
    Appx CDN URLs ko actual downloadable URL mein transform karo.
    Returns (transformed_url, appx_key)
    ITsGOLU main.py se direct liya.
    """
    appxkey = ""

    if ltype == LinkType.APPX_TRANS_V1:
        base_with_params, signature = url.split("*", 1) if "*" in url else (url, "")
        base_clean = base_with_params.split(".mkv")[0] + ".mkv"
        base_clean = base_clean.replace(
            "https://static-trans-v1.classx.co.in",
            "https://appx-transcoded-videos-mcdn.akamai.net.in"
        )
        return (f"{base_clean}*{signature}" if signature else base_clean), ""

    if ltype == LinkType.APPX_TRANS_V2:
        base_with_params, signature = url.split("*", 1) if "*" in url else (url, "")
        base_clean = base_with_params.split(".mkv")[0] + ".mkv"
        base_clean = base_clean.replace(
            "https://static-trans-v2.classx.co.in",
            "https://transcoded-videos-v2.classx.co.in"
        )
        return (f"{base_clean}*{signature}" if signature else base_clean), ""

    if ltype == LinkType.APPX_REC:
        base_with_params, signature = url.split("*", 1) if "*" in url else (url, "")
        base_clean = base_with_params.split("?")[0]
        base_clean = base_clean.replace(
            "https://static-rec.classx.co.in",
            "https://appx-recordings-mcdn.akamai.net.in"
        )
        return (f"{base_clean}*{signature}" if signature else base_clean), ""

    if ltype == LinkType.APPX_WSB:
        clean = url.split("?")[0].replace(
            "https://static-wsb.classx.co.in",
            "https://appx-wsb-gcp-mcdn.akamai.net.in"
        )
        return clean, ""

    if ltype in (LinkType.APPX_DB, LinkType.APPX_DB_V2):
        old = "https://static-db-v2.classx.co.in" if ltype == LinkType.APPX_DB_V2 else "https://static-db.classx.co.in"
        new = "https://appx-content-v2.classx.co.in" if ltype == LinkType.APPX_DB_V2 else "https://appxcontent.kaxa.in"
        if "*" in url:
            base_url, key = url.split("*", 1)
            base_url = base_url.split("?")[0].replace(old, new)
            return f"{base_url}*{key}", ""
        return url.split("?")[0].replace(old, new), ""

    if ltype == LinkType.APPX_ENCRYPTED:
        if "*" in url:
            appxkey = url.split("*")[1]
            url     = url.split("*")[0]
        return url, appxkey

    return url, appxkey


# ─── ClassPlus Signed URL ─────────────────────────────────────────────────────

def get_classplus_signed_url(url: str, cp_token: str) -> str:
    """
    ClassPlus M3U8 / Vimeo → signed JW URL.
    ITsGOLU main.py exact logic.
    """
    try:
        headers = {
            'host': 'api.classplusapp.com',
            'x-access-token': cp_token,
            'accept-language': 'EN',
            'api-version': '18',
            'app-version': '1.4.73.2',
            'build-number': '35',
            'connection': 'Keep-Alive',
            'content-type': 'application/json',
            'device-details': 'Xiaomi_Redmi 7_SDK-32',
            'device-id': 'c28d3cb16bbdac01',
            'region': 'IN',
            'user-agent': 'Mobile-Android',
            'accept-encoding': 'gzip'
        }
        resp = requests.get(
            'https://api.classplusapp.com/cams/uploader/video/jw-signed-url',
            headers=headers, params={"url": url}, timeout=15
        )
        signed = resp.json().get('url', url)
        return signed if signed else url
    except Exception as e:
        LOGGER.warning(f"CP signed URL failed: {e}")
        return url


def get_classplus_drm_keys(url: str, user_id: str = "0") -> tuple[str, str]:
    """
    CP DRM API → (mpd_url, keys_string)
    ITsGOLU CP API logic.
    """
    try:
        url_norm = url.replace("https://cpvod.testbook.com/", "https://media-cdn.classplusapp.com/drm/")
        api_call = f"{CP_API}?url={url_norm}@ITSGOLU_OFFICIAL&user_id={user_id}"
        resp     = requests.get(api_call, timeout=30)
        data     = resp.json()
        if isinstance(data, dict):
            if "KEYS" in data and "MPD" in data:
                keys_str = " ".join([f"--key {k}" for k in data["KEYS"]])
                return data["MPD"], keys_str
            if "url" in data:
                return data["url"], ""
    except Exception as e:
        LOGGER.warning(f"CP DRM API failed: {e}")
    return url, ""


# ─── Download Functions ───────────────────────────────────────────────────────

async def download_m3u8(url: str, name: str, path: str, quality: str = "720") -> str | None:
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mp4")
    # ffmpeg first
    cmd = f'ffmpeg -y -i "{url}" -c copy -bsf:a aac_adtstoasc "{out}"'
    code, _ = run(cmd)
    if code == 0 and os.path.exists(out):
        return out
    # yt-dlp fallback
    cmd2 = (
        f'yt-dlp --no-check-certificates '
        f'-f "b[height<={quality}]/bv[height<={quality}]+ba/b/bv+ba" '
        f'--merge-output-format mp4 -o "{out}" '
        f'-R 25 --fragment-retries 25 '
        f''
        f'"{url}"'
    )
    code2, _ = run(cmd2)
    return out if (code2 == 0 and os.path.exists(out)) else None


async def download_mpd_non_drm(url: str, name: str, path: str, quality: str = "720") -> str | None:
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mp4")
    cmd = (
        f'yt-dlp --no-check-certificates --no-warnings '
        f'--merge-output-format mp4 '
        f'-f "b[height<={quality}]/bv[height<={quality}]+ba/b/bv+ba" '
        f'-o "{out}" -R 50 --retries 100 --fragment-retries 100 '
        f''
        f'"{url}"'
    )
    code, _ = run(cmd)
    return out if (code == 0 and os.path.exists(out)) else None


async def decrypt_and_merge(mpd_url: str, keys_string: str, name: str,
                             path: str, quality: str = "720") -> str | None:
    """
    DRM decrypt flow — ITsGOLU decrypt_and_merge_video exact logic.
    yt-dlp (encrypted) → mp4decrypt video+audio → ffmpeg merge
    """
    import shutil
    os.makedirs(path, exist_ok=True)
    sname = sanitize(name)
    out_path = Path(path)

    # Step 1: Download encrypted streams
    cmd = (
        f'yt-dlp -f "bv[height<={quality}]+ba/b" '
        f'-o "{path}/file.%(ext)s" '
        f'--allow-unplayable-format --no-check-certificate '
        f'"{mpd_url}"'
    )
    run(cmd)

    # Step 2: Find downloaded files
    vid_file = aud_file = None
    for f in out_path.iterdir():
        if f.suffix == ".mp4" and "video" not in f.name and "audio" not in f.name:
            vid_file = f
        elif f.suffix in (".m4a", ".webm") and "audio" not in f.name:
            aud_file = f

    if not vid_file:
        LOGGER.error(f"DRM: no encrypted video found in {path}")
        return None

    # Step 3: Decrypt
    vid_dec = out_path / "video.mp4"
    aud_dec = out_path / "audio.m4a"
    final   = out_path / f"{sname}.mp4"

    if vid_file:
        run(f'mp4decrypt {keys_string} --show-progress "{vid_file}" "{vid_dec}"')
        vid_file.unlink(missing_ok=True)

    if aud_file:
        run(f'mp4decrypt {keys_string} --show-progress "{aud_file}" "{aud_dec}"')
        aud_file.unlink(missing_ok=True)

    # Step 4: Merge
    if vid_dec.exists() and aud_dec.exists():
        run(f'ffmpeg -y -i "{vid_dec}" -i "{aud_dec}" -c copy "{final}"')
        vid_dec.unlink(missing_ok=True)
        aud_dec.unlink(missing_ok=True)
    elif vid_dec.exists():
        shutil.move(str(vid_dec), str(final))

    return str(final) if final.exists() else None


async def download_mpd_drm(url: str, name: str, path: str,
                            quality: str = "720", keys: str = "") -> str | None:
    """
    DRM video download — agar keys diye hain to decrypt karo,
    warna auto-fetch keys aur decrypt karo.
    """
    if not keys:
        keys = await fetch_drm_keys_remote(url)
    if keys:
        keys_string = " ".join([f"--key {k}" for k in keys.split()]) if "--key" not in keys else keys
        return await decrypt_and_merge(url, keys_string, name, path, quality)
    return await download_mpd_non_drm(url, name, path, quality)


async def fetch_drm_keys_remote(mpd_url: str) -> str:
    """Auto-fetch DRM keys from remote API."""
    try:
        api = "https://app.magmail.eu.org/get_keys"
        async with aiohttp.ClientSession(headers={"user-agent": "okhttp"}) as sess:
            async with sess.post(api, json={"link": mpd_url},
                                 timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    keys = data.get("keys", [])
                    return " ".join([f"--key {k}" for k in keys]) if isinstance(keys, list) else str(keys)
    except Exception as e:
        LOGGER.warning(f"DRM key fetch failed: {e}")
    return ""


async def download_mkv_cdn(url: str, name: str, path: str, quality: str = "720") -> str | None:
    """
    .mkv / .cdn / appx akamai CDN files.
    Use yt-dlp — same as ITsGOLU video download.
    """
    os.makedirs(path, exist_ok=True)
    sname = sanitize(name)
    out   = os.path.join(path, f"{sname}.%(ext)s")

    cmd = (
        f'yt-dlp --no-check-certificates '
        f'-f "b[height<={quality}]/bv[height<={quality}]+ba/b/bv+ba" '
        f'--merge-output-format mkv -o "{out}" '
        f'-R 25 --fragment-retries 25 '
        f''
        f'"{url}"'
    )
    run(cmd)

    # find downloaded file
    for ext in [".mkv", ".mp4", ".webm"]:
        f = os.path.join(path, f"{sname}{ext}")
        if os.path.exists(f):
            return f

    return None


async def download_appx_encrypted(url: str, appxkey: str, name: str, path: str, quality: str = "720") -> str | None:
    """
    Appx encrypted.m* cipher graphic decrypt.
    ITsGOLU main.py: download_and_decrypt_video
    """
    os.makedirs(path, exist_ok=True)
    sname = sanitize(name)
    enc   = os.path.join(path, f"{sname}_enc.mkv")
    dec   = os.path.join(path, f"{sname}.mp4")

    # Download encrypted
    cmd = (
        f'yt-dlp --no-check-certificate '
        f'-f "bv[height<={quality}]+ba/b" '
        f'--allow-unplayable-format -o "{enc}" '
        f'"{url}"'
    )
    run(cmd)

    if not os.path.exists(enc):
        LOGGER.error(f"Appx encrypted: download failed {name}")
        return None

    # Decrypt using mp4decrypt with appxkey
    key_arg = f"--key {appxkey}" if appxkey else ""
    run(f'mp4decrypt {key_arg} --show-progress "{enc}" "{dec}"')

    try:
        os.remove(enc)
    except Exception:
        pass

    return dec if os.path.exists(dec) else None


async def download_cw_brightcove(url: str, name: str, path: str, cw_token: str = "") -> str | None:
    """
    CW / Brightcove CDN.
    ITsGOLU: replace bcov_auth token, then yt-dlp.
    """
    os.makedirs(path, exist_ok=True)
    token = cw_token or CW_TOKEN_DEFAULT

    if "bcov_auth" in url and token:
        url = url.split("bcov_auth")[0] + f"bcov_auth={token}"

    return await download_m3u8(url, name, path)


async def download_vision_ias(url: str, name: str, path: str) -> str | None:
    """
    VisionIAS — scrape page to get actual m3u8.
    ITsGOLU main.py exact headers.
    """
    try:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Referer': 'http://www.visionias.in/',
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36',
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers=headers) as resp:
                text = await resp.text()
        m3u8_match = re.search(r'(https://.*?playlist\.m3u8.*?)"', text)
        if m3u8_match:
            m3u8_url = m3u8_match.group(1)
            return await download_m3u8(m3u8_url, name, path)
    except Exception as e:
        LOGGER.error(f"Vision IAS failed: {e}")
    return None


async def download_utkarsh_jw(url: str, name: str, path: str) -> str | None:
    """
    Utkarsh JW CDN URL transform + download.
    ITsGOLU: replace apps-s3-jw-prod → d1q5ugnejk3zoi.cloudfront.net
    """
    url = url.replace(
        "https://apps-s3-jw-prod.utkarshapp.com/admin_v1/file_library/videos",
        "https://d1q5ugnejk3zoi.cloudfront.net/ut-production-jw/admin_v1/file_library/videos"
    )
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mp4")
    code, _ = run(f'yt-dlp -o "{out}" "{url}"')
    return out if (code == 0 and os.path.exists(out)) else None


async def download_utkarsh_ws(url: str, name: str, path: str, api_token: str = "") -> str | None:
    """.ws worksheet → HTML via Utkarsh API."""
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.html")
    api = f"{MASTER_API}utkash-ws?url={url}&authorization={api_token}"
    try:
        r = requests.get(api, allow_redirects=True, stream=True, timeout=60)
        with open(out, "wb") as f:
            for chunk in r.iter_content(1024 * 10):
                if chunk:
                    f.write(chunk)
        return out if os.path.exists(out) else None
    except Exception as e:
        LOGGER.error(f"WS download failed: {e}")
        return None


async def download_acecwply(url: str, name: str, path: str, quality: str = "720") -> str | None:
    """acecwply — yt-dlp with hls-prefer-ffmpeg, output mkv."""
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mkv")
    cmd = (
        f'yt-dlp -o "{out}" '
        f'-f "bestvideo[height<={quality}]+bestaudio" '
        f'--hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning '
        f'"{url}"'
    )
    code, _ = run(cmd)
    return out if (code == 0 and os.path.exists(out)) else None


async def download_youtube(url: str, name: str, path: str,
                            quality: str = "720", cookies: str = "") -> str | None:
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mp4")
    # ITsGOLU format string for YouTube
    ytf = f"bv*[height<={quality}][ext=mp4]+ba[ext=m4a]/b[height<=?{quality}]"
    cookie_arg = f'--cookies "{cookies}"' if cookies and os.path.exists(cookies) else ""
    cmd = f'yt-dlp {cookie_arg} -f "{ytf}" -o "{out}" "{url}"'
    code, _ = run(cmd)
    return out if (code == 0 and os.path.exists(out)) else None


async def download_youtube_embed(url: str, name: str, path: str,
                                  quality: str = "720", cookies: str = "") -> str | None:
    # ITsGOLU: youtube-nocookie.com/embed → youtu.be
    url = (url.replace("www.youtube-nocookie.com/embed", "youtu.be")
              .replace("youtube.com/embed/", "youtu.be/")
              .replace("?modestbranding=1", ""))
    # extract video id
    vid_id = url.split("/")[-1].split("?")[0]
    url    = f"https://www.youtube.com/watch?v={vid_id}"
    return await download_youtube(url, name, path, quality, cookies)


async def download_instagram(url: str, name: str, path: str, cookies: str = "") -> str | None:
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mp4")
    cookie_arg = f'--cookies "{cookies}"' if cookies and os.path.exists(cookies) else ""
    code, _ = run(f'yt-dlp {cookie_arg} -o "{out}" "{url}"')
    return out if (code == 0 and os.path.exists(out)) else None


async def download_gdrive(url: str, name: str, path: str) -> str | None:
    """Google Drive — convert share URL + yt-dlp."""
    url = (url.replace("file/d/", "uc?export=download&id=")
              .replace("/view?usp=sharing", ""))
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.mp4")
    code, _ = run(f'yt-dlp -o "{out}" "{url}"')
    return out if (code == 0 and os.path.exists(out)) else await _async_download(url, name, path)


async def download_pdf(url: str, name: str, path: str) -> str | None:
    """PDF / direct file async download."""
    os.makedirs(path, exist_ok=True)
    ext = ".pdf"
    out = os.path.join(path, f"{sanitize(name)}{ext}")
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    async with aiofiles.open(out, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            await f.write(chunk)
                    return out
    except Exception as e:
        LOGGER.error(f"PDF download failed: {e}")
    return None


async def download_cw_pdf(url: str, name: str, path: str) -> str | None:
    """CW media bucket PDF — Cloudflare bypass via cloudscraper."""
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}.pdf")
    try:
        scraper = cloudscraper.create_scraper()
        resp    = scraper.get(url.replace(" ", "%20"))
        if resp.status_code == 200:
            with open(out, "wb") as f:
                f.write(resp.content)
            return out
    except Exception as e:
        LOGGER.error(f"CW PDF failed: {e}")
    return None


async def _async_download(url: str, name: str, path: str, ext: str = ".bin") -> str | None:
    os.makedirs(path, exist_ok=True)
    file_ext = Path(url.split("?")[0]).suffix or ext
    out = os.path.join(path, f"{sanitize(name)}{file_ext}")
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    async with aiofiles.open(out, "wb") as f:
                        async for chunk in resp.content.iter_chunked(128 * 1024):
                            await f.write(chunk)
                    return out
    except Exception as e:
        LOGGER.error(f"Async download failed: {e}")
    return None


async def download_zip(url: str, name: str, path: str) -> str | None:
    return await _async_download(url, name, path, ".zip")


async def download_audio(url: str, name: str, path: str) -> str | None:
    ext = Path(url.split("?")[0]).suffix or ".mp3"
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, f"{sanitize(name)}{ext}")
    cmd = f'yt-dlp -x --audio-format {ext.lstrip(".")} -o "{out}" "{url}" -R 25 --fragment-retries 25'
    code, _ = run(cmd)
    return out if (code == 0 and os.path.exists(out)) else None


# ─── Master Dispatcher ────────────────────────────────────────────────────────

async def download_by_type(item: dict, path: str, quality: str = "720",
                            pw_token: str = "", cp_token: str = "",
                            cw_token: str = "", cookies: str = "",
                            api_token: str = "") -> str | None:
    """
    item = {name, url, type: LinkType}
    Detect type → call correct download function.
    """
    url   = item["url"]
    name  = item["name"]
    ltype = item["type"]

    LOGGER.info(f"[{ltype.name}] {name[:60]}")

    try:
        # ── Appx transforms ──────────────────────────────────────
        if ltype in (LinkType.APPX_TRANS_V1, LinkType.APPX_TRANS_V2,
                     LinkType.APPX_REC, LinkType.APPX_WSB,
                     LinkType.APPX_DB, LinkType.APPX_DB_V2):
            t_url, _ = transform_appx_url(url, ltype)
            return await download_mkv_cdn(t_url, name, path, quality)

        if ltype == LinkType.APPX_ENCRYPTED:
            t_url, appxkey = transform_appx_url(url, ltype)
            return await download_appx_encrypted(t_url, appxkey, name, path, quality)

        if ltype == LinkType.APPX_GENERIC:
            return await download_mkv_cdn(url, name, path, quality)

        # ── ClassPlus M3U8 (signed URL) ──────────────────────────
        if ltype == LinkType.CLASSPLUS_M3U8:
            signed = get_classplus_signed_url(url, cp_token) if cp_token else url
            return await download_m3u8(signed, name, path, quality)

        if ltype == LinkType.CLASSPLUS_WEB:
            return await download_m3u8(url, name, path, quality)

        if ltype in (LinkType.CLASSPLUS_DRM, LinkType.CLASSPLUS_TESTBOOK):
            mpd, keys = get_classplus_drm_keys(url)
            if keys:
                return await decrypt_and_merge(mpd, keys, name, path, quality)
            return await download_mpd_non_drm(mpd or url, name, path, quality)

        if ltype == LinkType.CLASSPLUS_VIMEO:
            signed = get_classplus_signed_url(url, cp_token) if cp_token else url
            return await download_youtube(signed, name, path, quality, cookies)

        # ── PW ───────────────────────────────────────────────────
        if ltype in (LinkType.PW_CDN, LinkType.PW_SEC1):
            pw_url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={pw_token}"
            return await download_m3u8(pw_url, name, path, quality)

        if ltype == LinkType.PW_AKAMAI:
            return await download_m3u8(url, name, path, quality)

        # ── CW Brightcove ────────────────────────────────────────
        if ltype == LinkType.CW_BRIGHTCOVE:
            return await download_cw_brightcove(url, name, path, cw_token)

        if ltype == LinkType.CW_MEDIABKT:
            return await download_cw_pdf(url, name, path)

        # ── Utkarsh ──────────────────────────────────────────────
        if ltype == LinkType.UTKARSH_JW:
            return await download_utkarsh_jw(url, name, path)

        if ltype == LinkType.UTKARSH_WS:
            return await download_utkarsh_ws(url, name, path, api_token)

        # ── ACE CW ───────────────────────────────────────────────
        if ltype == LinkType.ACE_CW_PLAY:
            return await download_acecwply(url, name, path, quality)

        # ── Vision IAS ───────────────────────────────────────────
        if ltype == LinkType.VISION_IAS:
            return await download_vision_ias(url, name, path)

        # ── Generic M3U8 / MPD ───────────────────────────────────
        if ltype == LinkType.M3U8:
            return await download_m3u8(url, name, path, quality)

        if ltype == LinkType.MPD_NON_DRM:
            return await download_mpd_non_drm(url, name, path, quality)

        if ltype == LinkType.MPD_DRM:
            keys = await fetch_drm_keys_remote(url)
            if keys:
                return await decrypt_and_merge(url, keys, name, path, quality)
            return await download_mpd_non_drm(url, name, path, quality)

        # ── Direct files ─────────────────────────────────────────
        if ltype in (LinkType.MKV_DIRECT, LinkType.CDN_VIDEO, LinkType.WEBM_DIRECT):
            return await download_mkv_cdn(url, name, path, quality)

        if ltype == LinkType.MP4_DIRECT:
            return await _async_download(url, name, path, ".mp4")

        # ── YouTube ──────────────────────────────────────────────
        if ltype == LinkType.YOUTUBE:
            return await download_youtube(url, name, path, quality, cookies)

        if ltype == LinkType.YOUTUBE_EMBED:
            return await download_youtube_embed(url, name, path, quality, cookies)

        # ── Instagram ────────────────────────────────────────────
        if ltype == LinkType.INSTAGRAM:
            return await download_instagram(url, name, path, cookies)

        # ── Google Drive ─────────────────────────────────────────
        if ltype == LinkType.GDRIVE:
            return await download_gdrive(url, name, path)

        # ── Documents ────────────────────────────────────────────
        if ltype == LinkType.PDF:
            return await download_pdf(url, name, path)

        if ltype == LinkType.IMAGE:
            return await _async_download(url, name, path)

        if ltype == LinkType.AUDIO:
            return await download_audio(url, name, path)

        if ltype == LinkType.ZIP_FILE:
            return await download_zip(url, name, path)

        # ── WebSankul (PDFs / other direct files) ────────────────
        if ltype == LinkType.WEBSANKUL:
            return await download_pdf(url, name, path)

        # ── Guidely / Unknown → yt-dlp generic ───────────────────
        if ltype in (LinkType.GUIDELY, LinkType.UNKNOWN):
            return await download_youtube(url, name, path, quality, cookies)

        LOGGER.warning(f"Skipped [{ltype.name}]: {url[:80]}")
        return None

    except Exception as e:
        LOGGER.error(f"Download error [{ltype.name}] {name}: {e}")
        return None
