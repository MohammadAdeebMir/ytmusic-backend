from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import yt_dlp
import os

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ytmusic = YTMusic()


# ---------- ROOT ----------
@app.get("/")
def root():
    return {"status": "ok"}


# ---------- SEARCH ----------
@app.get("/search")
def search(q: str):
    try:
        results = ytmusic.search(q, filter="songs")[:20]
        output = []

        for r in results:
            thumbs = r.get("thumbnails") or []
            thumb = None
            if thumbs:
                thumb = max(thumbs, key=lambda x: x.get("width", 0)).get("url")

            output.append({
                "videoId": r.get("videoId"),
                "title": r.get("title"),
                "artists": [a["name"] for a in r.get("artists", [])],
                "album": r.get("album", {}).get("name"),
                "duration": r.get("duration"),
                "thumbnail": thumb,
            })

        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- YTDLP OPTIONS ----------
def ydl_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "geo_bypass": True,
        "force_ipv4": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "retries": 10,
        "fragment_retries": 10,

        # ⭐ CRITICAL: relaxed format
        "format": "bestaudio",

        # ⭐ VERY IMPORTANT in 2026
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android_music",
                    "android",
                    "web",
                    "tv_embedded",
                    "ios"
                ]
            }
        },

        # ⭐ forces yt-dlp to choose best audio
        "format_sort": ["abr", "asr"],

        # ⭐ strong mobile identity
        "http_headers": {
            "User-Agent": (
                "com.google.android.youtube/19.09.37 "
                "(Linux; U; Android 13; en_US; SM-S918B) gzip"
            )
        },
    }

    # ✅ load cookies ALWAYS if present
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"

    return opts


# ---------- STREAM ----------
@app.get("/stream")
def stream(videoId: str):
    try:
        url = f"https://www.youtube.com/watch?v={videoId}"

        with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {"success": False, "error": "NO_INFO"}

        audio_url = info.get("url")

        # ⭐ fallback scan (important)
        if not audio_url:
            formats = info.get("formats") or []
            audio_candidates = [
                f for f in formats
                if f.get("acodec") != "none" and f.get("url")
            ]

            if audio_candidates:
                best = max(audio_candidates, key=lambda f: f.get("abr") or 0)
                audio_url = best["url"]

        if not audio_url:
            return {"success": False, "error": "STREAM_UNAVAILABLE"}

        return {"success": True, "url": audio_url}

    except Exception as e:
        return {
            "success": False,
            "error": "STREAM_UNAVAILABLE",
            "detail": str(e)[:200],
        }


# ---------- DOWNLOAD ----------
@app.get("/download")
def download(videoId: str):
    try:
        url = f"https://www.youtube.com/watch?v={videoId}"

        with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return {"success": False, "error": "NO_INFO"}

        return {
            "success": True,
            "title": info.get("title"),
            "audio_url": info.get("url"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)[:200]}
