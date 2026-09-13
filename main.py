import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests
import yt_dlp

app = Flask(__name__)
CORS(app)

# Resolve absolute path to cookies.txt
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

def get_base_opts():
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)
    return opts

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "portal": "DJ ABHISHEK DADA",
        "cookies_found": COOKIE_FILE.is_file()
    })

@app.route("/channel-tracks", methods=["GET"])
def get_channel_tracks():
    opts = get_base_opts()
    opts['extract_flat'] = 'in_playlist'
    opts['playlistend'] = 500
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info("https://www.youtube.com/@dj_abhishek_dada/videos", download=False)
            entries = res.get('entries', []) or []
            tracks = [
                {
                    "id": item.get("id"),
                    "title": item.get("title", "DJ Track"),
                    "author": "DJ ABHISHEK DADA"
                }
                for item in entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_youtube():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing search query"}), 400

    opts = get_base_opts()
    opts['extract_flat'] = 'in_playlist'
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch50:{query}", download=False)
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

@app.route("/download-audio", methods=["GET"])
def handle_audio_download():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url parameter"}), 400

    vid = extract_video_id(raw_url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = get_base_opts()
    opts['format'] = 'bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get('url')

            if not stream_url and 'formats' in info:
                for f in reversed(info['formats']):
                    if f.get('url') and (f.get('vcodec') == 'none' or 'audio' in f.get('format', '')):
                        stream_url = f['url']
                        break
                if not stream_url:
                    stream_url = info['formats'][-1].get('url')

            if not stream_url:
                return jsonify({"status": "error", "message": "Stream URL not available"}), 404

            raw_title = info.get('title', f"DJ_ABHISHEK_{vid}")
            clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip() or f"DJ_ABHISHEK_{vid}"

            # Stream pipe directly to browser download manager
            req = requests.get(stream_url, stream=True, timeout=30)
            return Response(
                stream_with_context(req.iter_content(chunk_size=1024 * 64)),
                content_type="audio/mpeg",
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.mp3"',
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download-video", methods=["GET"])
def handle_video_download():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url parameter"}), 400

    vid = extract_video_id(raw_url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = get_base_opts()
    opts['format'] = 'best[ext=mp4]/best'

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
                    stream_url = info['formats'][-1].get('url')

            if not stream_url:
                return jsonify({"status": "error", "message": "Video stream link not found"}), 404

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
            
