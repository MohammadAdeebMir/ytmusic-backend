from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
import os

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- INIT ----------------
ytmusic = YTMusic()


# ---------------- ROOT (optional but nice) ----------------
@app.get("/")
async def root():
    return {"status": "Music backend running"}


# ---------------- SEARCH ----------------
@app.get("/search")
async def search_songs(q: str):
    try:
        results = ytmusic.search(q, filter="songs")[:20]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    songs = []
    for r in results:
        songs.append({
            "videoId": r.get("videoId"),
            "title": r.get("title"),
            "artists": [a.get("name") for a in r.get("artists", [])],
            "album": r.get("album", {}).get("name"),
            "duration": r.get("duration"),
            "thumbnail": (r.get("thumbnails") or [{}])[-1].get("url")
        })

    return {"success": True, "results": songs}


# ---------------- SONG INFO ----------------
@app.get("/song")
async def get_song(video_id: str):
    try:
        data = ytmusic.get_song(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    thumbs = (
        data.get("microformat", {})
        .get("thumbnail", {})
        .get("thumbnails", [])
    )

    best_thumb = max(thumbs, key=lambda t: t.get("width", 0))["url"] if thumbs else None

    return {
        "success": True,
        "song": {
            "videoId": video_id,
            "title": data.get("videoDetails", {}).get("title"),
            "artists": [data.get("videoDetails", {}).get("author")],
            "duration": data.get("videoDetails", {}).get("lengthSeconds"),
            "thumbnail": best_thumb,
        },
    }


# ---------------- STREAM (99% SUCCESS VERSION) ----------------
@app.get("/stream")
async def stream_video(video_id: str):
    if not video_id:
        return {"success": False, "error": "INVALID_VIDEO_ID"}

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        # 🔥 MUCH SAFER FORMAT STRATEGY
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extract_flat": False,

        # stability
        "geo_bypass": True,
        "force_ipv4": True,
        "nocheckcertificate": True,
        "prefer_insecure": True,
        "retries": 5,
        "fragment_retries": 5,
        "skip_unavailable_fragments": True,

        # strong client spoof
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "android_music",
                    "android_creator",
                    "web",
                    "tv_embedded"
                ]
            }
        },

        # mobile UA
        "http_headers": {
            "User-Agent": (
                "com.google.android.youtube/19.09.37 "
                "(Linux; U; Android 13; en_US; SM-S918B) gzip"
            )
        },
    }

    # ✅ cookie support
    import os
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"

    try:
        from yt_dlp import YoutubeDL

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # 🔥 NEW SAFE EXTRACTION
        audio_url = None

        # direct url first
        if info.get("url"):
            audio_url = info["url"]

        # otherwise scan formats
        if not audio_url:
            formats = info.get("formats", [])
            for f in formats:
                if (
                    f.get("acodec") != "none"
                    and f.get("url")
                ):
                    audio_url = f["url"]
                    break

        if not audio_url:
            return {"success": False, "error": "STREAM_UNAVAILABLE"}

        return {
            "success": True,
            "url": audio_url
        }

    except Exception as e:
        return {
            "success": False,
            "error": "STREAM_UNAVAILABLE",
            "detail": str(e)[:200]
        }

# ---------------- DOWNLOAD ----------------
@app.get("/download")
async def download_video(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio",
        "quiet": True,
        "no_warnings": True,
        "force_ipv4": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "success": True,
            "title": info.get("title"),
            "url": info.get("url"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)[:180]}
