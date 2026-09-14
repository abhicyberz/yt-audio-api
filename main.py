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

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "online", 
        "portal": "DJ ABHISHEK DADA Smart API", 
        "cookies_loaded": COOKIE_FILE.is_file()
    })

@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    # 500 limit aur fastest extraction
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
        'playlistend': 500
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)

    try:
        # sp=CAI parameter enforces latest upload sorting
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
        'playlistend': 500
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)

    try:
        is_url = q.startswith("http://") or q.startswith("https://") or "youtube.com" in q or "youtu.be" in q
        if is_url:
            target = q
        else:
            encoded_query = requests.utils.quote(q)
            target = f"https://www.youtube.com/results?search_query={encoded_query}&sp=CAI"

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

def _pipe_smart_media(format_type: str, is_attachment: bool = True):
    raw_url = request.args.get("url", "").strip()
    vid = extract_video_id(raw_url)
    if not vid:
        return jsonify({"status": "error", "message": "Video ID missing"}), 400

    target_url = f"https://www.youtube.com/watch?v={vid}"

    # Smart Routing: Agar audio hai toh web client hide karke Android Music client use karo
    # Agar video hai toh normal mweb fallback use karo
    client_list = ['android_music', 'ios'] if format_type == 'audio' else ['ios', 'mweb']
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': client_list,
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_chunk_size': 10485760
    }
    if COOKIE_FILE.is_file():
        ydl_opts['cookiefile'] = str(COOKIE_FILE)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            formats = info.get('formats') or []
            
            stream_url = None
            headers = info.get('http_headers') or {}
            ext = 'mp4'

            if format_type == 'audio':
                # Pure audio format extraction
                for f in reversed(formats):
                    if f.get('url') and f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        stream_url = f['url']
                        ext = f.get('ext', 'm4a')
                        if f.get('http_headers'): headers = f['http_headers']
                        break
            else:
                # Progressive Video (Audio+Video) extraction
                for f in reversed(formats):
                    if f.get('url') and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        stream_url = f['url']
                        ext = f.get('ext', 'mp4')
                        if f.get('http_headers'): headers = f['http_headers']
                        break

            # Ultimate fallback if formats are blocked but raw URL exists
            if not stream_url:
                stream_url = info.get('url')

            if not stream_url:
                return jsonify({"status": "error", "message": f"{format_type} stream blocked by server"}), 404

            raw_title = info.get('title', f"DJ_ABHISHEK_{vid}")
            clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip() or f"DJ_ABHISHEK_{vid}"

            req_headers = dict(headers or {})
            if "Range" in request.headers:
                req_headers["Range"] = request.headers["Range"]

            req = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)
            
            disposition = "attachment" if is_attachment else "inline"
            download_ext = "mp3" if format_type == 'audio' else "mp4"
            mime_type = 'audio/mpeg' if format_type == 'audio' else 'video/mp4'
            
            resp_headers = {
                "Accept-Ranges": "bytes",
                "Content-Type": req.headers.get('Content-Type', mime_type),
                "Content-Disposition": f'{disposition}; filename="{clean_title}.{download_ext}"',
                "Cache-Control": "no-cache"
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
        
