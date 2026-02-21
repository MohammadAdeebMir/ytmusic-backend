from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
import yt_dlp
import os

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize YTMusic (use auth file if provided, else default unauthenticated)
try:
    if os.path.exists("headers_auth.json"):
        ytmusic = YTMusic("headers_auth.json")
    else:
        ytmusic = YTMusic()
except Exception:
    ytmusic = YTMusic()

@app.get("/search")
async def search(query: str):
    """
    Search for songs matching the query using YouTube Music.
    Returns up to 20 results with videoId, title, artists, album, thumbnail, duration.
    """
    try:
        results = ytmusic.search(query, filter="songs", limit=20)
        response = []
        for res in results:
            if res.get("resultType") != "song":
                continue
            video_id = res.get("videoId")
            title = res.get("title")
            artists = [artist.get("name") for artist in res.get("artists", [])] if res.get("artists") else []
            album = res.get("album", {}).get("name") if res.get("album") else None
            # Select the largest thumbnail available
            thumbnail = None
            thumbs = res.get("thumbnails") or []
            if thumbs:
                largest = max(thumbs, key=lambda x: x.get("width", 0))
                thumbnail = largest.get("url")
            duration = res.get("duration")
            response.append({
                "videoId": video_id,
                "title": title,
                "artists": artists,
                "album": album,
                "thumbnail": thumbnail,
                "duration": duration
            })
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/song")
async def song_info(videoId: str):
    """
    Return detailed song info for the given videoId, including album thumbnail.
    """
    try:
        song_data = ytmusic.get_song(videoId)
        video_details = song_data.get("videoDetails", {})
        title = video_details.get("title")
        author = video_details.get("author")
        artists = [author] if author else []
        album_name = None
        thumbnail_url = None

        # Attempt to find album ID from song_data (if available)
        album_id = None
        if song_data.get("videoDetails", {}).get("microformat", {}).get("microformatDataRenderer", {}).get("title"):
            # No direct album field in get_song, skip unless stored elsewhere
            album_id = None

        # If album ID is known, get album thumbnails
        if album_id:
            try:
                album_data = ytmusic.get_album(album_id)
                thumbs = album_data.get("thumbnails") or []
                if thumbs:
                    largest = max(thumbs, key=lambda x: x.get("width", 0))
                    thumbnail_url = largest.get("url")
            except Exception:
                thumbnail_url = None

        # Fallback: use video thumbnail at highest resolution
        if not thumbnail_url:
            thumbnail_url = f"https://i.ytimg.com/vi/{videoId}/maxresdefault.jpg"

        duration = int(video_details.get("lengthSeconds", 0)) if video_details.get("lengthSeconds") else None
        return {
            "videoId": videoId,
            "title": title,
            "artists": artists,
            "album": album_name,
            "thumbnail": thumbnail_url,
            "duration": duration
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Song info error: {str(e)}")

@app.get("/stream")
async def stream(videoId: str):
    """
    Return a direct streaming URL for the best audio-only format of the given videoId.
    """
    try:
        url = f"https://www.youtube.com/watch?v={videoId}"
        ydl_opts = {
            "format": "bestaudio[acodec!=none]/bestaudio",
            "quiet": True,
            "noplaylist": True
        }
        if os.path.exists("cookies.txt"):
            ydl_opts["cookiefile"] = "cookies.txt"
        # Set a mobile user-agent
        ydl_opts["user_agent"] = ("Mozilla/5.0 (Linux; Android 10; Mobile; rv:91.0) "
                                  "Gecko/91.0 Firefox/91.0")
        # Try multiple player clients
        player_clients = ["web", "android", "tv"]
        stream_url = None
        for client in player_clients:
            try:
                ydl_opts["extractor_args"] = {"youtube": f"player_client={client}"}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    stream_url = info.get("url")
                if stream_url:
                    break
            except Exception:
                continue
        if not stream_url:
            raise Exception("Unable to extract stream URL")
        return {"url": stream_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream error: {str(e)}")

@app.get("/download")
async def download(videoId: str):
    """
    Return metadata and a direct download URL for the best audio-only format of the given videoId.
    """
    try:
        url = f"https://www.youtube.com/watch?v={videoId}"
        ydl_opts = {
            "format": "bestaudio[acodec!=none]/bestaudio",
            "quiet": True,
            "noplaylist": True
        }
        if os.path.exists("cookies.txt"):
            ydl_opts["cookiefile"] = "cookies.txt"
        ydl_opts["user_agent"] = ("Mozilla/5.0 (Linux; Android 10; Mobile; rv:91.0) "
                                  "Gecko/91.0 Firefox/91.0")
        player_clients = ["web", "android", "tv"]
        info = None
        for client in player_clients:
            try:
                ydl_opts["extractor_args"] = {"youtube": f"player_client={client}"}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                if info:
                    break
            except Exception:
                continue
        if not info:
            raise Exception("Extraction failed")
        download_url = info.get("url")
        return {
            "videoId": videoId,
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "audio_url": download_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
