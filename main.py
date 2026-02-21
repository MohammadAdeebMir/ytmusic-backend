from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from cachetools import TTLCache
import yt_dlp

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- INIT ----------------
yt = YTMusic()
cache = TTLCache(maxsize=500, ttl=300)

# ---------------- HEALTH CHECK ----------------
@app.get("/")
def root():
    return {"status": "ok"}

# ---------------- SEARCH ----------------
@app.get("/search")
def search_music(q: str):
    if q in cache:
        return cache[q]

    results = yt.search(q, filter="songs")[:10]
    cache[q] = results
    return results

# ---------------- SONG INFO ----------------
@app.get("/song")
def song_info(videoId: str):
    return yt.get_song(videoId)

# ---------------- STREAM (RENDER SAFE ULTRA) ----------------
@app.get("/stream")
async def get_stream(videoId: str):
    try:
        url = f"https://www.youtube.com/watch?v={videoId}"

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "noplaylist": True,
            "extract_flat": False,
            "skip_download": True,

            # 🔥 improves Render success
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },

            # 🔥 required for some Render regions
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        audio_url = None

        # Primary
        if isinstance(info, dict):
            audio_url = info.get("url")

        # Fallback — pick best audio format
        if not audio_url and info.get("formats"):
            for f in reversed(info["formats"]):
                if f.get("acodec") != "none" and f.get("url"):
                    audio_url = f["url"]
                    break

        if not audio_url:
            return {"error": "STREAM_UNAVAILABLE"}

        return {
            "audio_url": audio_url,
            "type": "audio"
        }

    except Exception as e:
        return {
            "error": "STREAM_UNAVAILABLE",
            "detail": str(e)[:120]
        }
