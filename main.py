import os
import re
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp

app = FastAPI(title="DJ ABHISHEK DADA Music API")

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extraction configuration using Android & iOS clients to bypass bot blocks
BASE_YTDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'extract_flat': False,
    'socket_timeout': 15,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'web_embedded'],
            'player_skip': ['webpage', 'configs']
        }
    },
    'http_headers': {
        'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
        'Accept-Language': 'en-US,en;q=0.9'
    }
}

def extract_video_id(url_or_id: str) -> str:
    """Extract 11 character YouTube video id."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

@app.get("/")
def health_check():
    return {"status": "online", "portal": "DJ ABHISHEK DADA"}

@app.get("/channel-tracks")
def get_channel_tracks():
    """Fetches uploaded mix tracks from the official channel."""
    channel_url = "https://www.youtube.com/@DJABHISHEKDADA/videos"
    opts = {
        'extract_flat': True,
        'quiet': True,
        'playlistend': 50,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(channel_url, download=False)
            entries = res.get('entries', []) or []
            tracks = []
            for entry in entries:
                if entry and entry.get('id'):
                    tracks.append({
                        "id": entry.get('id'),
                        "title": entry.get('title', 'Unknown Track'),
                        "author": entry.get('uploader') or "DJ ABHISHEK DADA"
                    })
            return {"status": "success", "tracks": tracks}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/search")
def search_tracks(q: str = Query(..., min_length=1)):
    """Search remixes on YouTube."""
    opts = {
        'extract_flat': True,
        'quiet': True,
        'default_search': 'ytsearch15',
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch15:{q}", download=False)
            entries = res.get('entries', []) or []
            tracks = []
            for entry in entries:
                if entry and entry.get('id'):
                    tracks.append({
                        "id": entry.get('id'),
                        "title": entry.get('title', 'Unknown Track'),
                        "author": entry.get('uploader') or "YouTube Artist"
                    })
            return {"status": "success", "tracks": tracks}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/download-audio")
def get_audio_stream(url: str = Query(...)):
    """Extracts direct playback/download CDN stream URL for audio (MP3)."""
    vid = extract_video_id(url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = dict(BASE_YTDL_OPTS)
    opts['format'] = 'bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get('url')
            
            # Fallback if top-level url key is missing
            if not stream_url and 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('url')]
                if audio_formats:
                    stream_url = audio_formats[-1]['url']
                else:
                    stream_url = info['formats'][-1].get('url')

            if stream_url:
                return {
                    "status": "success",
                    "stream_url": stream_url,
                    "title": info.get('title', f"DJ_ABHISHEK_{vid}")
                }
            return JSONResponse(status_code=404, content={"status": "error", "message": "Direct audio URL not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/download-video")
def get_video_stream(url: str = Query(...)):
    """Extracts combined MP4 CDN stream URL for video download."""
    vid = extract_video_id(url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = dict(BASE_YTDL_OPTS)
    opts['format'] = 'best[ext=mp4][vcodec!=none][acodec!=none]/best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get('url')

            if not stream_url and 'formats' in info:
                progressive = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url')]
                if progressive:
                    stream_url = progressive[-1]['url']
                else:
                    stream_url = info['formats'][-1].get('url')

            if stream_url:
                return {
                    "status": "success",
                    "stream_url": stream_url,
                    "title": info.get('title', f"DJ_ABHISHEK_{vid}")
                }
            return JSONResponse(status_code=404, content={"status": "error", "message": "Direct video URL not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main.py:app", host="0.0.0.0", port=port, reload=False)
                        
