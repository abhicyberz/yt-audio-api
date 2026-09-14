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
    for p in [r'(?:v=|\/)([0-9A-Za-z_-]{11})', r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})', r'^([0-9A-Za-z_-]{11})$']:
        match = re.search(p, url_or_id)
        if match: return match.group(1)
    return url_or_id

def get_opts(client="ios"):
    opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True, 'extractor_args': {'youtube': {'player_client': [client]}}}
    if COOKIE_FILE.is_file(): opts['cookiefile'] = str(COOKIE_FILE)
    return opts

@app.route("/", methods=["GET"])
def health(): return jsonify({"status": "online", "portal": "DJ ABHISHEK DADA API"})

@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    # Direct channel ke videos nikalega, random search nahi
    opts = {'quiet': True, 'extract_flat': True, 'playlistend': 50}
    if COOKIE_FILE.is_file(): opts['cookiefile'] = str(COOKIE_FILE)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info("https://www.youtube.com/@DJABHISHEKDADA/videos", download=False)
            tracks = [{"id": i.get("id"), "title": i.get("title", "DJ Track"), "author": i.get("uploader")} for i in res.get('entries', []) if i and i.get("id")]
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
            tracks = [{"id": i.get("id"), "title": i.get("title"), "author": i.get("uploader")} for i in res.get('entries', []) if i and i.get("id")]
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

def _extract_stream(url, fmt):
    for client in (['ios', 'android', 'mweb'] if fmt == 'audio' else ['ios', 'android']):
        try:
            with yt_dlp.YoutubeDL(get_opts(client)) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                if fmt == 'audio':
                    cands = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                    if cands: return sorted(cands, key=lambda x: x.get('abr') or 0, reverse=True)[0]['url'], info.get('http_headers', {}), info.get('title')
                else:
                    cands = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                    if cands: return sorted(cands, key=lambda x: x.get('height') or 0, reverse=True)[0]['url'], info.get('http_headers', {}), info.get('title')
        except: continue
    raise Exception("Extraction blocked")

def _pipe_media(fmt, is_att=True):
    vid = extract_video_id(request.args.get("url", ""))
    if not vid: return jsonify({"error": "No ID"}), 400
    try:
        url, hdrs, title = _extract_stream(f"https://www.youtube.com/watch?v={vid}", fmt)
        clean = re.sub(r'[\/*?:"<>|]', "", title).strip()
        req_hdrs = dict(hdrs)
        if "Range" in request.headers: req_hdrs["Range"] = request.headers["Range"]
        
        r = requests.get(url, headers=req_hdrs, stream=True, timeout=30)
        ext, mime = ("mp3", "audio/mpeg") if fmt == 'audio' else ("mp4", "video/mp4")
        resp_hdrs = {"Accept-Ranges": "bytes", "Content-Type": r.headers.get('Content-Type', mime), "Content-Disposition": f'{"attachment" if is_att else "inline"}; filename="{clean}.{ext}"'}
        if 'Content-Length' in r.headers: resp_hdrs['Content-Length'] = r.headers['Content-Length']
        
        return Response(stream_with_context(r.iter_content(chunk_size=128*1024)), status=r.status_code, headers=resp_hdrs)
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/stream-audio", methods=["GET"])
def stream_audio(): return _pipe_media('audio', False)
@app.route("/download-audio", methods=["GET"])
def download_audio(): return _pipe_media('audio', True)
@app.route("/download-video", methods=["GET"])
def download_video(): return _pipe_media('video', True)

if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
