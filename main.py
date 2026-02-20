from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ytmusicapi import YTMusic
from cachetools import TTLCache
import requests
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

@app.get("/search")
def search_music(q: str):
    if q in cache:
        return cache[q]
    results = yt.search(q, filter="songs")[:10]
    cache[q] = results
    return results

@app.get("/song")
def song_info(videoId: str):
    return yt.get_song(videoId)

@app.get("/stream")
def get_stream(videoId: str):
    url = f"https://www.youtube.com/watch?v={videoId}"
    return {"audio_url": url}
