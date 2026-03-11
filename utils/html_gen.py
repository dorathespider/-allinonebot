"""
html_gen.py
──────────────────────────────────────────────────────────────────
TXT content → Beautiful HTML page with Video.js player.
Source: ITsGOLU html_handler.py (best implementation)
Extra: Platform-aware URL conversion added.
──────────────────────────────────────────────────────────────────
"""

from utils.link_detector import LinkType, detect, parse_txt_content
from config import Config


def convert_url_for_html(url: str, ltype: LinkType, pw_token: str = "") -> str:
    """
    Kuch URLs ko browser-playable format mein convert karo.
    """
    if ltype == LinkType.PW_CDN:
        return f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={pw_token}"

    if ltype == LinkType.PW_AKAMAI:
        return f"https://www.khanglobalstudies.com/player?src={url}"

    if ltype == LinkType.YOUTUBE_EMBED:
        vid_id = url.split("/")[-1].split("?")[0]
        return f"https://www.youtube.com/watch?v={vid_id}"

    if ltype in (LinkType.CLASSPLUS_DRM,):
        return f"https://dragoapi.vercel.app/video/{url}"

    return url


def generate_html(batch_name: str, items: list[dict], credit: str = "") -> str:
    """
    items = list of {name, url, type}
    Returns full HTML string.
    """
    credit = credit or Config.CREDIT

    videos = []
    pdfs   = []
    others = []

    for item in items:
        name  = item["name"]
        url   = item["url"]
        ltype = item["type"]

        if ltype in (LinkType.TELEGRAM_LINK, LinkType.BROKEN):
            continue

        conv_url = convert_url_for_html(url, ltype)

        if ltype in (LinkType.PDF, LinkType.WEBSANKUL) or url.lower().endswith(".pdf"):
            pdfs.append((name, conv_url))
        elif ltype == LinkType.IMAGE:
            others.append((name, conv_url))
        elif ltype == LinkType.UNKNOWN:
            others.append((name, conv_url))
        else:
            videos.append((name, conv_url))

    video_links = "".join(
        f'<a href="#" onclick="playVideo(\'{url}\')" class="item-link">▶ {name}</a>'
        for name, url in videos
    )
    pdf_links = "".join(
        f'<a href="{url}" target="_blank" class="item-link">📄 {name}</a>'
        for name, url in pdfs
    )
    other_links = "".join(
        f'<a href="{url}" target="_blank" class="item-link">🔗 {name}</a>'
        for name, url in others
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{batch_name}</title>
<link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet"/>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}}
  body{{background:#0f0f0f;color:#eee}}
  header{{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:18px;text-align:center}}
  header h1{{font-size:20px;color:#00d4ff}}
  header p{{font-size:12px;color:#aaa;margin-top:4px}}
  #player-wrap{{margin:15px auto;width:95%;max-width:720px}}
  .search-bar{{margin:12px auto;width:95%;max-width:500px}}
  .search-bar input{{width:100%;padding:9px 14px;border:1px solid #00d4ff;border-radius:6px;
    background:#1a1a2e;color:#eee;font-size:13px;outline:none}}
  .tabs{{display:flex;justify-content:center;gap:8px;margin:12px auto;width:95%;max-width:500px}}
  .tab{{flex:1;padding:10px;border:none;border-radius:6px;cursor:pointer;
    font-size:13px;font-weight:bold;background:#1a1a2e;color:#aaa;transition:.2s}}
  .tab.active,.tab:hover{{background:#00d4ff;color:#000}}
  .section{{display:none;margin:12px auto;width:95%;max-width:720px;
    background:#1a1a2e;border-radius:8px;padding:14px}}
  .section.visible{{display:block}}
  .section h2{{font-size:14px;color:#00d4ff;margin-bottom:10px}}
  .item-link{{display:block;padding:9px 12px;margin:4px 0;background:#16213e;
    border-radius:5px;text-decoration:none;color:#ccc;font-size:13px;
    border-left:3px solid #00d4ff;transition:.2s}}
  .item-link:hover{{background:#00d4ff;color:#000;border-left-color:#000}}
  .count-badge{{display:inline-block;background:#00d4ff;color:#000;
    border-radius:10px;padding:1px 7px;font-size:11px;margin-left:6px}}
  footer{{text-align:center;padding:15px;font-size:12px;color:#555;margin-top:20px}}
</style>
</head>
<body>
<header>
  <h1>📚 {batch_name}</h1>
  <p>
    🎬 {len(videos)} Videos &nbsp;|&nbsp;
    📄 {len(pdfs)} PDFs &nbsp;|&nbsp;
    🔗 {len(others)} Others
  </p>
</header>

<div id="player-wrap">
  <video id="main-player" class="video-js vjs-default-skin vjs-big-play-centered"
    controls preload="auto" width="100%" height="400"></video>
</div>

<div class="search-bar">
  <input type="text" id="searchInput" placeholder="🔍 Search videos, PDFs..." oninput="filterItems()">
</div>

<div class="tabs">
  <button class="tab active" onclick="showTab('videos',this)">
    🎬 Videos <span class="count-badge">{len(videos)}</span>
  </button>
  <button class="tab" onclick="showTab('pdfs',this)">
    📄 PDFs <span class="count-badge">{len(pdfs)}</span>
  </button>
  <button class="tab" onclick="showTab('others',this)">
    🔗 Others <span class="count-badge">{len(others)}</span>
  </button>
</div>

<div id="videos" class="section visible">
  <h2>🎬 Video Lectures</h2>
  <div class="list">{video_links or '<p style="color:#555;font-size:13px">No videos found.</p>'}</div>
</div>

<div id="pdfs" class="section">
  <h2>📄 PDFs & Documents</h2>
  <div class="list">{pdf_links or '<p style="color:#555;font-size:13px">No PDFs found.</p>'}</div>
</div>

<div id="others" class="section">
  <h2>🔗 Other Resources</h2>
  <div class="list">{other_links or '<p style="color:#555;font-size:13px">No other resources.</p>'}</div>
</div>

<footer>Generated by <b>{credit}</b> | AllInOneBot</footer>

<script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
<script>
const player = videojs('main-player',{{controls:true,autoplay:false,preload:'auto',fluid:true}});

function playVideo(url){{
  const type = url.includes('.m3u8') ? 'application/x-mpegURL' :
               url.includes('.mpd')  ? 'application/dash+xml'  : 'video/mp4';
  try{{
    player.src({{src:url,type:type}});
    player.play();
    window.scrollTo({{top:0,behavior:'smooth'}});
  }}catch(e){{window.open(url,'_blank');}}
}}

function showTab(name, btn){{
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('visible'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(name).classList.add('visible');
  btn.classList.add('active');
  filterItems();
}}

function filterItems(){{
  const q = document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('.item-link').forEach(a=>{{
    a.style.display = a.textContent.toLowerCase().includes(q) ? 'block' : 'none';
  }});
}}
</script>
</body>
</html>"""
    return html
