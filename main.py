from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ytmusic = YTMusic()

@app.get("/search")
async def search_songs(q: str):
    try:
        results = ytmusic.search(q, filter="songs")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    songs = []
    for r in results:
        songs.append({
            "videoId": r.get("videoId"),
            "title": r.get("title"),
            "artists": [artist.get("name") for artist in r.get("artists", [])],
            "album": r.get("album", {}).get("name"),
            "albumId": r.get("album", {}).get("id"),
            "duration": r.get("duration"),
        })
    return {"success": True, "results": songs}

@app.get("/song")
async def get_song(video_id: str):
    try:
        data = ytmusic.get_song(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    song_details = {
        "videoId": video_id,
        "title": data.get("videoDetails", {}).get("title"),
        "artists": [data.get("videoDetails", {}).get("author")],
        "duration": data.get("videoDetails", {}).get("lengthSeconds"),
    }
    # Fetch album thumbnail (highest quality)
    album_thumb_url = None
    audio_playlist_id = data.get("audioPlaylistId")
    if audio_playlist_id:
        album_browse_id = ytmusic.get_album_browse_id(audio_playlist_id)
        if album_browse_id:
            album_data = ytmusic.get_album(album_browse_id)
            thumbs = album_data.get("thumbnails") or []
            # Use other_versions if needed
            if not thumbs:
                for v in album_data.get("other_versions", []):
                    thumbs = v.get("thumbnails") or []
                    if thumbs:
                        break
            if thumbs:
                # pick highest resolution thumbnail
                best_thumb = max(thumbs, key=lambda t: t.get("width", 0))
                album_thumb_url = best_thumb.get("url")
    # Fallback to video thumbnail if no album art
    if not album_thumb_url:
        thumbs = data.get("microformat", {}).get("thumbnail", {}).get("thumbnails") or []
        if thumbs:
            best_thumb = max(thumbs, key=lambda t: t.get("width", 0))
            album_thumb_url = best_thumb.get("url")
    song_details["thumbnail"] = album_thumb_url
    return {"success": True, "song": song_details}

@app.get("/stream")
async def stream_video(video_id: str):
    ydl_opts = {
        "format": "bestaudio",
        "force_ipv4": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 10,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36"
        }
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    audio_url = info.get("url")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio URL not found")
    return {"success": True, "url": audio_url}

@app.get("/download")
async def download_video(video_id: str):
    ydl_opts = {
        "format": "bestaudio",
        "force_ipv4": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 10,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36"
        }
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    audio_url = info.get("url")
    title = info.get("title")
    ext = info.get("ext")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio URL not found")
    return {"success": True, "title": title, "ext": ext, "url": audio_url}
