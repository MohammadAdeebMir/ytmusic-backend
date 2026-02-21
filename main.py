from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from cachetools import TTLCache
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# ---------------- STREAM (FIXED) ----------------
@app.get("/stream")
async def get_stream(videoId: str):
    try:
        url = f"https://www.youtube.com/watch?v={videoId}"

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 10,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get("url") or info["formats"][-1]["url"]

        return {
            "audio_url": audio_url,
            "type": "audio"
        }

    except Exception:
        return {"error": "STREAM_UNAVAILABLE"}
