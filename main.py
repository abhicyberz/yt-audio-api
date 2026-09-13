import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests
import yt_dlp

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
COOKIE_FILE = BASE_DIR / "cookies.txt"

def extract_video_id(url_or_id: str) -> str:
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return url_or_id

def get_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android'],
                'player_skip': ['configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)
    return opts

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "mode": "DJ API", "cookies": COOKIE_FILE.is_file()})

# 1. Latest Uploads Sabse Upar
@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    channel_url = "https://www.youtube.com/@dj_abhishek_dada/videos"
    opts = get_opts()
    opts['extract_flat'] = 'in_playlist'
    opts['playlistend'] = 100

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(channel_url, download=False)
            entries = res.get('entries', []) or []
            
            tracks = []
            for item in entries:
                if item and item.get("id"):
                    tracks.append({
                        "id": item.get("id"),
                        "title": item.get("title", "DJ Track"),
                        "author": item.get("uploader") or "DJ ABHISHEK DADA"
                    })
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 2. Search Engine
@app.route("/search", methods=["GET"])
def search_tracks():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"status": "error", "message": "Query required"}), 400

    opts = get_opts()
    opts['extract_flat'] = 'in_playlist'
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch50:{q}", download=False)
            entries = res.get('entries', []) or []
            tracks = [
                {
                    "id": item.get("id"),
                    "title": item.get("title", "YouTube Track"),
                    "author": item.get("uploader", "YouTube Creator")
                }
                for item in entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 3. Separate MP4 Video Downloader
@app.route("/download-video", methods=["GET"])
def download_video():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url"}), 400

    vid = extract_video_id(raw_url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = get_opts()
    opts['format'] = '18/22/best[ext=mp4]/best'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get('url')

            if not stream_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        stream_url = f['url']
                        break

            if not stream_url:
                return jsonify({"status": "error", "message": "Progressive stream link not found"}), 404

            raw_title = info.get('title', f"DJ_ABHISHEK_{vid}")
            clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip() or f"DJ_ABHISHEK_{vid}"

            req = requests.get(stream_url, stream=True, timeout=30)
            return Response(
                stream_with_context(req.iter_content(chunk_size=1024 * 128)),
                content_type="video/mp4",
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.mp4"',
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
    
