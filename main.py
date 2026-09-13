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

ANDROID_USER_AGENT = "com.google.android.youtube/19.29.37 (Linux; U; Android 11; US) gzip"

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
                'player_client': ['android', 'ios']
            }
        },
        'http_headers': {
            'User-Agent': ANDROID_USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)
    return opts

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "online", 
        "portal": "DJ ABHISHEK DADA", 
        "cookies_loaded": COOKIE_FILE.is_file()
    })

@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    opts = get_base_opts()
    opts['extract_flat'] = 'in_playlist'
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Fix: Direct handle URL crash se bachne ke liye stable search pipeline
            res = ydl.extract_info("ytsearch50:DJ ABHISHEK DADA", download=False)
            entries = res.get('entries', []) or []
            tracks = [
                {"id": item.get("id"), "title": item.get("title", "DJ Track"), "author": item.get("uploader", "DJ ABHISHEK DADA")}
                for item in entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_tracks():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"status": "error", "message": "Query missing"}), 400
    opts = get_base_opts()
    opts['extract_flat'] = 'in_playlist'
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch50:{q}", download=False)
            entries = res.get('entries', []) or []
            tracks = [
                {"id": item.get("id"), "title": item.get("title", "YouTube Track"), "author": item.get("uploader", "YouTube Creator")}
                for item in entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download-audio", methods=["GET"])
def download_audio():
    raw_url = request.args.get("url", "").strip()
    vid = extract_video_id(raw_url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = get_base_opts()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            formats = info.get('formats', []) or []
            stream_url = None
            selected_headers = info.get('http_headers', {})

            for f in reversed(formats):
                if f.get('url') and f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    stream_url = f['url']
                    if f.get('http_headers'):
                        selected_headers = f['http_headers']
                    break

            if not stream_url:
                stream_url = info.get('url')

            if not stream_url:
                return jsonify({"status": "error", "message": "Audio stream unavailable"}), 404

            raw_title = info.get('title', f"DJ_ABHISHEK_{vid}")
            clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip() or f"DJ_ABHISHEK_{vid}"

            headers = {
                'User-Agent': selected_headers.get('User-Agent', ANDROID_USER_AGENT),
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            req = requests.get(stream_url, headers=headers, stream=True, timeout=25)
            c_type = req.headers.get('Content-Type', 'audio/mp4')

            return Response(
                stream_with_context(req.iter_content(chunk_size=1024 * 64)),
                content_type=c_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.mp3"',
                    "Accept-Ranges": "bytes"
                }
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download-video", methods=["GET"])
def download_video():
    raw_url = request.args.get("url", "").strip()
    vid = extract_video_id(raw_url)
    target_url = f"https://www.youtube.com/watch?v={vid}"

    opts = get_base_opts()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            formats = info.get('formats', []) or []
            stream_url = None
            selected_headers = info.get('http_headers', {})

            for f in reversed(formats):
                if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    stream_url = f['url']
                    if f.get('http_headers'):
                        selected_headers = f['http_headers']
                    break

            if not stream_url:
                stream_url = info.get('url')

            if not stream_url:
                return jsonify({"status": "error", "message": "Video stream unavailable"}), 404

            raw_title = info.get('title', f"DJ_ABHISHEK_{vid}")
            clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip() or f"DJ_ABHISHEK_{vid}"

            headers = {
                'User-Agent': selected_headers.get('User-Agent', ANDROID_USER_AGENT),
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            req = requests.get(stream_url, headers=headers, stream=True, timeout=25)
            c_type = req.headers.get('Content-Type', 'video/mp4')

            return Response(
                stream_with_context(req.iter_content(chunk_size=1024 * 128)),
                content_type=c_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{clean_title}.mp4"',
                    "Accept-Ranges": "bytes"
                }
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
    
