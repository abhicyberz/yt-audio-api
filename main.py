import os
import re
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

ABS_DOWNLOADS_PATH = Path("/tmp/downloads")
ABS_DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)

# Helper function to extract 11-digit YouTube ID
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

# 🩺 Health Check (Railway keep-alive)
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "online", "portal": "DJ ABHISHEK DADA"})

# 🎵 Live Channel Fetch (Limit 500 Songs)
@app.route("/channel-tracks", methods=["GET"])
def get_channel_tracks():
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': 500,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info("https://www.youtube.com/@dj_abhishek_dada/videos", download=False)
            entries = res.get('entries', [])
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

# 🔍 Smart Search (Limit 50 Results)
@app.route("/search", methods=["GET"])
def search_youtube():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing search query"}), 400

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch50:{query}", download=False)
            entries = res.get('entries', [])
            results = [
                {
                    "id": item.get("id"),
                    "title": item.get("title", "YouTube Track"),
                    "author": item.get("uploader", "YouTube Creator")
                }
                for item in entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 🎧 Audio Stream & Direct MP3 Downloader
@app.route("/download-audio", methods=["GET"])
def handle_audio_download():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url parameter"}), 400

    vid = extract_video_id(raw_url)
    video_url = f"https://www.youtube.com/watch?v={vid}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['configs', 'webpage']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            
            if not stream_url and 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('url')]
                stream_url = audio_formats[-1]['url'] if audio_formats else info['formats'][-1].get('url')

            if stream_url:
                return jsonify({
                    "status": "success",
                    "stream_url": stream_url,
                    "title": info.get('title', f"DJ_ABHISHEK_{vid}")
                })
            return jsonify({"status": "error", "message": "Stream URL not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 🎬 Direct MP4 Video Downloader
@app.route("/download-video", methods=["GET"])
def handle_video_download():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url parameter"}), 400

    vid = extract_video_id(raw_url)
    video_url = f"https://www.youtube.com/watch?v={vid}"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['configs', 'webpage']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')

            if not stream_url and 'formats' in info:
                prog = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url')]
                stream_url = prog[-1]['url'] if prog else info['formats'][-1].get('url')

            if stream_url:
                return jsonify({
                    "status": "success",
                    "stream_url": stream_url,
                    "title": info.get('title', f"DJ_ABHISHEK_{vid}")
                })
            return jsonify({"status": "error", "message": "Video stream not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
        
