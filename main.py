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


# ---------------- STREAM (RENDER HARDENED) ----------------
@app.get("/stream")
async def get_stream(videoId: str):
    if not videoId:
        return {"error": "INVALID_VIDEO_ID"}

    try:
        url = f"https://www.youtube.com/watch?v={videoId}"

        # 🔥 Production-grade yt-dlp config for Render
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "noplaylist": True,
            "extract_flat": False,

            # stability
            "geo_bypass": True,
            "force_ipv4": True,
            "retries": 3,
            "fragment_retries": 3,
            "skip_unavailable_fragments": True,

            # 🔥 key anti-block fix
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web", "tv_embedded"]
                }
            },

            # 🔥 mobile user agent
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 13; SM-S918B) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Mobile Safari/537.36"
                )
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # primary URL
        audio_url = info.get("url")

        # 🔥 safer fallback scan
        if not audio_url:
            formats = info.get("formats", [])
            for f in formats:
                if (
                    f.get("acodec") != "none"
                    and f.get("vcodec") == "none"
                    and f.get("url")
                ):
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
            "detail": str(e)[:200]
        }            "error": "STREAM_UNAVAILABLE",
            "detail": str(e)[:200]
