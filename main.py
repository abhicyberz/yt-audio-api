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

def get_smart_ydl_opts(client_type="ios"):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'socket_timeout': 15,
        'extractor_args': {
            'youtube': {
                'player_client': [client_type],
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
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
        "portal": "DJ ABHISHEK DADA API Pro",
        "cookies_loaded": COOKIE_FILE.is_file()
    })

@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
        'playlistend': 50
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)

    try:
        target = "https://www.youtube.com/results?search_query=DJ+ABHISHEK+DADA&sp=CAI"
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(target, download=False)
            entries = res.get('entries', []) or []
            tracks = [
                {
                    "id": item.get("id"),
                    "title": item.get("title", "DJ Track"),
                    "author": item.get("uploader") or "DJ ABHISHEK DADA"
                }
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

    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
        'playlistend': 40
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)

    try:
        is_url = q.startswith("http://") or q.startswith("https://") or "youtube.com" in q or "youtu.be" in q
        target = q if is_url else f"ytsearch30:{q}"

        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(target, download=False)
            raw_entries = res.get('entries', []) if 'entries' in res else [res]
            tracks = [
                {
                    "id": item.get("id"),
                    "title": item.get("title", "YouTube Track"),
                    "author": item.get("uploader") or item.get("channel") or q
                }
                for item in raw_entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def _extract_stream(target_url, format_type):
    # Multi-client fallback matrix to bypass bot detection & format missing issues
    clients = ['ios', 'android', 'mweb', 'web_creator'] if format_type == 'audio' else ['ios', 'android', 'web']
    last_err = None

    for client in clients:
        try:
            ydl_opts = get_smart_ydl_opts(client)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                formats = info.get('formats') or []
                selected_url = None
                headers = info.get('http_headers') or {}

                if format_type == 'audio':
                    # Best standalone audio stream
                    audio_candidates = [
                        f for f in formats 
                        if f.get('url') and f.get('acodec') != 'none' and (f.get('vcodec') == 'none' or 'audio' in f.get('format', '').lower())
                    ]
                    if audio_candidates:
                        best_audio = sorted(audio_candidates, key=lambda x: x.get('abr') or 0, reverse=True)[0]
                        selected_url = best_audio.get('url')
                        if best_audio.get('http_headers'):
                            headers = best_audio['http_headers']
                else:
                    # Video + Audio progressive stream (prevents silent video issues)
                    video_candidates = [
                        f for f in formats 
                        if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none'
                    ]
                    if video_candidates:
                        best_video = sorted(video_candidates, key=lambda x: x.get('height') or 0, reverse=True)[0]
                        selected_url = best_video.get('url')
                        if best_video.get('http_headers'):
                            headers = best_video['http_headers']

                if not selected_url and formats:
                    selected_url = formats[-1].get('url')

                if selected_url:
                    return selected_url, headers, info.get('title', 'Media')
        except Exception as err:
            last_err = err
            continue

    raise Exception(f"All extraction clients blocked: {last_err}")

def _pipe_smart_media(format_type: str, is_attachment: bool = True):
    raw_url = request.args.get("url", "").strip()
    vid = extract_video_id(raw_url)
    if not vid:
        return jsonify({"status": "error", "message": "Video ID missing"}), 400

    target_url = f"https://www.youtube.com/watch?v={vid}"

    try:
        stream_url, headers, raw_title = _extract_stream(target_url, format_type)
        clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip() or f"DJ_ABHISHEK_{vid}"

        req_headers = dict(headers or {})
        if "Range" in request.headers:
            req_headers["Range"] = request.headers["Range"]

        req = requests.get(stream_url, headers=req_headers, stream=True, timeout=35)

        disposition = "attachment" if is_attachment else "inline"
        download_ext = "mp3" if format_type == 'audio' else "mp4"
        mime_type = 'audio/mpeg' if format_type == 'audio' else 'video/mp4'

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": req.headers.get('Content-Type', mime_type),
            "Content-Disposition": f'{disposition}; filename="{clean_title}.{download_ext}"',
            "Cache-Control": "no-cache",
            "Access-Control-Expose-Headers": "Content-Disposition, Content-Length"
        }
        if 'Content-Length' in req.headers:
            resp_headers['Content-Length'] = req.headers['Content-Length']
        if 'Content-Range' in req.headers:
            resp_headers['Content-Range'] = req.headers['Content-Range']

        return Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 128)),
            status=req.status_code if req.status_code in [200, 206] else 200,
            headers=resp_headers
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/stream-audio", methods=["GET"])
def stream_audio():
    return _pipe_smart_media('audio', is_attachment=False)

@app.route("/download-audio", methods=["GET"])
def download_audio():
    return _pipe_smart_media('audio', is_attachment=True)

@app.route("/download-video", methods=["GET"])
def download_video():
    return _pipe_smart_media('video', is_attachment=True)

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
                                                                                 
