import os
import re
from pathlib import Path
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import yt_dlp
import requests

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
        "portal": "DJ ABHISHEK DADA API v2",
        "cookies_loaded": COOKIE_FILE.is_file()
    })

@app.route("/channel-tracks", methods=["GET"])
def channel_tracks():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'skip_download': True,
        'playlistend': 30
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)

    try:
        # Direct search query via ytsearch
        target = "ytsearch30:DJ ABHISHEK DADA"
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
        'playlistend': 25
    }
    if COOKIE_FILE.is_file():
        opts['cookiefile'] = str(COOKIE_FILE)

    try:
        target = q if ("youtube.com" in q or "youtu.be" in q) else f"ytsearch25:{q}"
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

# Zero-Bandwidth Download Routes (Redirects to Cobalt API Stream)
@app.route("/download-audio", methods=["GET"])
def download_audio():
    vid = extract_video_id(request.args.get("url", "").strip())
    if not vid:
        return jsonify({"status": "error", "message": "Video ID missing"}), 400
    
    try:
        cobalt_res = requests.post("https://api.cobalt.tools/", json={
            "url": f"https://www.youtube.com/watch?v={vid}",
            "downloadMode": "audio",
            "audioFormat": "mp3"
        }, headers={"Accept": "application/json", "Content-Type": "application/json"}, timeout=10)
        
        data = cobalt_res.json()
        if "url" in data:
            return redirect(data["url"])
    except Exception:
        pass
    
    # Fallback direct stream link
    return redirect(f"https://cobalt.tools/")

@app.route("/download-video", methods=["GET"])
def download_video():
    vid = extract_video_id(request.args.get("url", "").strip())
    if not vid:
        return jsonify({"status": "error", "message": "Video ID missing"}), 400

    try:
        cobalt_res = requests.post("https://api.cobalt.tools/", json={
            "url": f"https://www.youtube.com/watch?v={vid}",
            "downloadMode": "auto"
        }, headers={"Accept": "application/json", "Content-Type": "application/json"}, timeout=10)
        
        data = cobalt_res.json()
        if "url" in data:
            return redirect(data["url"])
    except Exception:
        pass

    return redirect(f"https://cobalt.tools/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)
            
