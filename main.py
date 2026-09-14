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
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11})', r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})', r'^([0-9A-Za-z_-]{11})$']
    for p in patterns:
        match = re.search(p, url_or_id)
        if match: return match.group(1)
    return url_or_id

def get_ydl_opts(client_type="ios"):
    opts = {
        'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': [client_type]}}
    }
    if COOKIE_FILE.is_file(): opts['cookiefile'] = str(COOKIE_FILE)
    return opts

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "portal": "DJ ABHISHEK DADA"})

@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    # DIRECT CHANNEL FETCH INSTEAD OF SEARCH
    opts = {'quiet': True, 'extract_flat': True, 'playlistend': 50}
    if COOKIE_FILE.is_file(): opts['cookiefile'] = str(COOKIE_FILE)

    try:
        target = "https://www.youtube.com/@DJABHISHEKDADA/videos"
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(target, download=False)
            entries = res.get('entries', []) or []
            tracks = [{"id": i.get("id"), "title": i.get("title", "DJ Track"), "author": i.get("uploader") or "DJ ABHISHEK DADA"} for i in entries if i and i.get("id")]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_tracks():
    q = request.args.get("q", "").strip()
    opts = {'quiet': True, 'extract_flat': True, 'playlistend': 30}
    if COOKIE_FILE.is_file(): opts['cookiefile'] = str(COOKIE_FILE)
    try:
        target = q if q.startswith("http") else f"ytsearch30:{q}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(target, download=False)
            raw_entries = res.get('entries', []) if 'entries' in res else [res]
            tracks = [{"id": i.get("id"), "title": i.get("title"), "author": i.get("uploader")} for i in raw_entries if i and i.get("id")]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def _extract_stream(target_url, format_type):
    clients = ['ios', 'android', 'mweb'] if format_type == 'audio' else ['ios', 'android', 'web']
    for client in clients:
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts(client)) as ydl:
                info = ydl.extract_info(target_url, download=False)
                formats = info.get('formats', [])
                selected_url = None
                
                if format_type == 'audio':
                    audio_cands = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                    if audio_cands: selected_url = sorted(audio_cands, key=lambda x: x.get('abr') or 0, reverse=True)[0]['url']
                else:
                    video_cands = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                    if video_cands: selected_url = sorted(video_cands, key=lambda x: x.get('height') or 0, reverse=True)[0]['url']
                
                if selected_url: return selected_url, info.get('http_headers', {}), info.get('title', 'Media')
        except: continue
    raise Exception("All clients blocked.")

def _pipe_smart_media(format_type, is_attachment=True):
    vid = extract_video_id(request.args.get("url", ""))
    if not vid: return jsonify({"status": "error"}), 400
    try:
        stream_url, headers, raw_title = _extract_stream(f"https://www.youtube.com/watch?v={vid}", format_type)
        clean_title = re.sub(r'[\/*?:"<>|]', "", raw_title).strip()
        req_headers = dict(headers)
        if "Range" in request.headers: req_headers["Range"] = request.headers["Range"]
        
        req = requests.get(stream_url, headers=req_headers, stream=True, timeout=30)
        ext = "mp3" if format_type == 'audio' else "mp4"
        mime = 'audio/mpeg' if format_type == 'audio' else 'video/mp4'
        disp = f'{"attachment" if is_attachment else "inline"}; filename="{clean_title}.{ext}"'
        
        resp_headers = {"Accept-Ranges": "bytes", "Content-Type": req.headers.get('Content-Type', mime), "Content-Disposition": disp}
        if 'Content-Length' in req.headers: resp_headers['Content-Length'] = req.headers['Content-Length']
        
        return Response(stream_with_context(req.iter_content(chunk_size=1024*128)), status=req.status_code, headers=resp_headers)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/stream-audio", methods=["GET"])
def stream_audio(): return _pipe_smart_media('audio', False)
@app.route("/download-audio", methods=["GET"])
def download_audio(): return _pipe_smart_media('audio', True)
@app.route("/download-video", methods=["GET"])
def download_video(): return _pipe_smart_media('video', True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
