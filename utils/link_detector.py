"""
link_detector.py  ─ v2
──────────────────────────────────────────────────────────────────
Heart of the bot. Koi bhi URL aaye → uska type identify karta hai.
Updated from ITsGOLU main.py — added ALL missing types:
  .mkv, .cdn, cipher/encrypted.m, Appx CDN variants,
  CW Brightcove, Utkarsh JW, acecwply, sec1.pw.live, etc.
──────────────────────────────────────────────────────────────────
"""

import re
from enum import Enum, auto


class LinkType(Enum):
    # ── Direct video files ───────────────────────────────────────
    M3U8              = auto()   # HLS .m3u8
    MPD_NON_DRM       = auto()   # MPEG-DASH no DRM
    MPD_DRM           = auto()   # MPEG-DASH Widevine
    MP4_DIRECT        = auto()   # .mp4
    MKV_DIRECT        = auto()   # .mkv  ← NEW
    WEBM_DIRECT       = auto()   # .webm
    CDN_VIDEO         = auto()   # .cdn extension  ← NEW

    # ── ClassPlus variants ───────────────────────────────────────
    CLASSPLUS_M3U8    = auto()   # media-cdn.classplusapp.com
    CLASSPLUS_DRM     = auto()   # videos.classplusapp.com / /drm/
    CLASSPLUS_VIMEO   = auto()   # tencdn / api.edukemy.com (JW signed)
    CLASSPLUS_TESTBOOK= auto()   # cpvod.testbook.com
    CLASSPLUS_WEB     = auto()   # webvideos.classplusapp.com

    # ── Appx / ClassX CDN variants ───────────────────────────────
    APPX_TRANS_V1     = auto()   # static-trans-v1.classx.co.in  ← NEW
    APPX_TRANS_V2     = auto()   # static-trans-v2.classx.co.in  ← NEW
    APPX_REC          = auto()   # static-rec.classx.co.in/drm/  ← NEW
    APPX_WSB          = auto()   # static-wsb.classx.co.in       ← NEW
    APPX_DB           = auto()   # static-db.classx.co.in        ← NEW
    APPX_DB_V2        = auto()   # static-db-v2.classx.co.in     ← NEW
    APPX_ENCRYPTED    = auto()   # encrypted.m* cipher graphic   ← NEW
    APPX_GENERIC      = auto()   # Other appx akamai CDNs

    # ── Physics Wallah ───────────────────────────────────────────
    PW_CDN            = auto()   # d1d34p8vz63oiq.cloudfront.net / childId
    PW_SEC1           = auto()   # sec1.pw.live  ← NEW
    PW_AKAMAI         = auto()   # akamaized.net / cdn77

    # ── CW / Career Will ─────────────────────────────────────────
    CW_BRIGHTCOVE     = auto()   # edge.api.brightcove.com bcov_auth  ← NEW
    CW_MEDIABKT       = auto()   # cwmediabkt99 Cloudflare PDF  ← NEW

    # ── Utkarsh ──────────────────────────────────────────────────
    UTKARSH_JW        = auto()   # jw-prod apps-s3-jw-prod  ← NEW
    UTKARSH_WS        = auto()   # .ws worksheet files  ← NEW

    # ── Other platforms ──────────────────────────────────────────
    ACE_CW_PLAY       = auto()   # acecwply  ← NEW
    VISION_IAS        = auto()
    GUIDELY           = auto()
    WEBSANKUL         = auto()

    # ── General ──────────────────────────────────────────────────
    YOUTUBE           = auto()
    YOUTUBE_EMBED     = auto()   # embed / nocookie
    INSTAGRAM         = auto()
    GDRIVE            = auto()   # Google Drive  ← NEW

    # ── Documents / Media ────────────────────────────────────────
    PDF               = auto()
    IMAGE             = auto()
    AUDIO             = auto()   # .mp3 .m4a .wav  ← NEW
    ZIP_FILE          = auto()   # .zip  ← NEW

    # ── Encrypted ────────────────────────────────────────────────
    HELPER_ENCRYPTED  = auto()   # helper://xxx AES

    # ── Telegram ─────────────────────────────────────────────────
    TELEGRAM_LINK     = auto()

    # ── Fallback ─────────────────────────────────────────────────
    UNKNOWN           = auto()
    BROKEN            = auto()


def detect(url: str) -> LinkType:
    """Any URL → its LinkType. Order matters — specific first."""
    if not url or not url.strip():
        return LinkType.BROKEN

    url = url.strip()

    if url.startswith("helper://"):
        return LinkType.HELPER_ENCRYPTED

    if "t.me/" in url or "telegram.me/" in url:
        return LinkType.TELEGRAM_LINK

    # ── Appx / ClassX (ITsGOLU main.py logic) ───────────────────
    if "static-trans-v1.classx.co.in" in url:
        return LinkType.APPX_TRANS_V1
    if "static-trans-v2.classx.co.in" in url:
        return LinkType.APPX_TRANS_V2
    if "static-rec.classx.co.in" in url:
        return LinkType.APPX_REC
    if "static-wsb.classx.co.in" in url:
        return LinkType.APPX_WSB
    if "static-db-v2.classx.co.in" in url:
        return LinkType.APPX_DB_V2
    if "static-db.classx.co.in" in url:
        return LinkType.APPX_DB
    if "encrypted.m" in url:                          # cipher graphic/encrypted Appx
        return LinkType.APPX_ENCRYPTED
    if any(x in url for x in [
        "appxcontent.kaxa.in", "appx-content-v2.classx.co.in",
        "appx-transcoded-videos-mcdn.akamai.net.in",
        "appx-recordings-mcdn.akamai.net.in",
        "appx-wsb-gcp-mcdn.akamai.net.in",
        "transcoded-videos-v2.classx.co.in",
    ]):
        return LinkType.APPX_GENERIC

    # ── ClassPlus ────────────────────────────────────────────────
    if "cpvod.testbook.com" in url or "covod.testbook.com" in url:
        return LinkType.CLASSPLUS_TESTBOOK
    if "webvideos.classplusapp.com" in url:
        return LinkType.CLASSPLUS_WEB
    if any(x in url for x in [
        "media-cdn.classplusapp.com",
        "media-cdn-alisg.classplusapp.com",
        "media-cdn-a.classplusapp.com",
    ]):
        return LinkType.CLASSPLUS_M3U8
    if "videos.classplusapp.com" in url or "classplusapp.com/drm/" in url:
        return LinkType.CLASSPLUS_DRM
    if "tencdn.classplusapp.com" in url or "api.edukemy.com/videodetails" in url:
        return LinkType.CLASSPLUS_VIMEO

    # ── PW ───────────────────────────────────────────────────────
    if "d1d34p8vz63oiq.cloudfront.net" in url:
        return LinkType.PW_CDN
    if "sec1.pw.live" in url:
        return LinkType.PW_SEC1
    if "childId" in url and "parentId" in url:
        return LinkType.PW_CDN
    if "akamaized.net" in url or "1942403233.rsc.cdn77.org" in url:
        return LinkType.PW_AKAMAI

    # ── CW Brightcove ────────────────────────────────────────────
    if "edge.api.brightcove.com" in url or "bcov_auth" in url:
        return LinkType.CW_BRIGHTCOVE
    if "cwmediabkt99" in url:
        return LinkType.CW_MEDIABKT

    # ── Utkarsh JW ───────────────────────────────────────────────
    if "jw-prod" in url or "apps-s3-jw-prod" in url or "d1q5ugnejk3zoi.cloudfront.net" in url:
        return LinkType.UTKARSH_JW

    # ── Ace CW ───────────────────────────────────────────────────
    if "acecwply" in url:
        return LinkType.ACE_CW_PLAY

    # ── Vision IAS ───────────────────────────────────────────────
    if "visionias.in" in url:
        return LinkType.VISION_IAS

    # ── Guidely ──────────────────────────────────────────────────
    if "guidely.prepdesk.in" in url or "ibpsguide.prepdesk.in" in url:
        return LinkType.GUIDELY

    # ── WebSankul / Digital Ocean ────────────────────────────────
    if "websankul" in url or "digitaloceanspaces.com" in url:
        u = url.lower().split("?")[0]
        return LinkType.PDF if u.endswith(".pdf") or "/pdf" in u else LinkType.WEBSANKUL

    # ── YouTube ──────────────────────────────────────────────────
    if "youtube-nocookie.com/embed" in url or "youtube.com/embed" in url:
        return LinkType.YOUTUBE_EMBED
    if "youtube.com" in url or "youtu.be" in url:
        return LinkType.YOUTUBE

    # ── Instagram ────────────────────────────────────────────────
    if "instagram.com" in url:
        return LinkType.INSTAGRAM

    # ── Google Drive ─────────────────────────────────────────────
    if "drive.google.com" in url or "file/d/" in url:
        return LinkType.GDRIVE

    # ── File extension matching ───────────────────────────────────
    u = url.lower().split("?")[0].split("#")[0]

    if u.endswith(".m3u8") or ".m3u8" in u:
        return LinkType.M3U8
    if u.endswith(".mpd") or ".mpd" in u:
        drm_hints = ["widevine", "drmcdni", "drm/wv", "drm/common", "encrypted", "bcov"]
        return LinkType.MPD_DRM if any(x in url.lower() for x in drm_hints) else LinkType.MPD_NON_DRM
    if u.endswith(".mkv"):
        return LinkType.MKV_DIRECT
    if u.endswith(".cdn"):
        return LinkType.CDN_VIDEO
    if u.endswith(".webm"):
        return LinkType.WEBM_DIRECT
    if any(u.endswith(e) for e in [".mp4", ".flv", ".avi", ".mov"]):
        return LinkType.MP4_DIRECT
    if u.endswith(".pdf") or "pdf" in u:
        return LinkType.PDF
    if any(u.endswith(e) for e in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
        return LinkType.IMAGE
    if any(u.endswith(e) for e in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]):
        return LinkType.AUDIO
    if u.endswith(".zip") or ".zip" in u:
        return LinkType.ZIP_FILE
    if u.endswith(".ws"):
        return LinkType.UTKARSH_WS

    # DRM patterns anywhere in URL
    if any(x in url for x in ["drmcdni", "drm/wv", "drm/common"]):
        return LinkType.MPD_DRM

    if url.startswith("http://") or url.startswith("https://"):
        return LinkType.UNKNOWN

    return LinkType.BROKEN


# ─── TXT Line Parser ─────────────────────────────────────────────────────────

def parse_txt_line(line: str) -> tuple[str, str]:
    """
    Ek TXT line → (name, url)
    Handles every known format.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return "", ""

    if line.startswith("helper://"):
        return "Encrypted", line

    if line.startswith("http://") or line.startswith("https://"):
        return "Video", line

    # "(Category) [Date] Name: URL"  ← WebSankul / ClassPlus
    m = re.match(r"^\(.*?\)\s*(.+?):\s*(https?://\S+)$", line)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Standard "Name: URL" / "Name - URL" / "Name|URL"
    for sep in [":", " - ", "|"]:
        if sep in line:
            idx   = line.index(sep)
            p_url = line[idx + len(sep):].strip()
            if p_url.startswith("http") or p_url.startswith("helper://"):
                name = line[:idx].strip()
                # clean special chars like ITsGOLU
                for ch in ["(", ")", "_", "\t", "/", "+", "#", "|", "@", "*", "."]:
                    name = name.replace(ch, " " if ch in "()_" else "")
                return name.strip()[:100], p_url

    # Last resort: regex find URL
    url_m = re.search(r"(https?://\S+|helper://\S+)", line)
    if url_m:
        url  = url_m.group(1)
        name = line.replace(url, "").strip().rstrip(":-|").strip()
        return (name or "Video")[:100], url

    return "", ""


def parse_txt_content(content: str) -> list[dict]:
    """Full TXT content → list of {name, url, type}"""
    results = []
    for line in content.splitlines():
        name, url = parse_txt_line(line)
        if not url:
            continue
        results.append({"name": name or "Video", "url": url, "type": detect(url)})
    return results
