import os
import time
import random
from pathlib import Path
from uuid import uuid4
from threading import BoundedSemaphore
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import static_ffmpeg

static_ffmpeg.add_paths()

ABS_DOWNLOADS_PATH = Path("/tmp/downloads")
ABS_DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)

DOWNLOAD_SEMAPHORE = BoundedSemaphore(value=2)

COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
}

# 🎵 Live Channel Fetch (Limit 500 Songs)
@app.route("/channel-tracks", methods=["GET"])
def get_channel_tracks():
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': 500, 
        'http_headers': COMMON_HEADERS,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'web'],
            }
        }
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
        'http_headers': COMMON_HEADERS,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'web'],
            }
        }
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

# ⬇ Audio Download Pipeline (Anti-Bot & 403 Forbidden Fix)
@app.route("/", methods=["GET"])
def handle_audio_request():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"error": "Missing url parameter"}), 400

    if "v=" in raw_url:
        video_id = raw_url.split("v=")[-1].split("&")[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
    elif len(raw_url) == 11 and "/" not in raw_url:
        video_url = f"https://www.youtube.com/watch?v={raw_url}"
    else:
        video_url = raw_url

    file_id = str(uuid4())
    output_path = str(ABS_DOWNLOADS_PATH / f"{file_id}.%(ext)s")

    ydl_opts = {
        'format': 'ba/b',
        'outtmpl': output_path,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'web'],
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_headers': COMMON_HEADERS,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    with DOWNLOAD_SEMAPHORE:
        time.sleep(random.uniform(1.0, 2.0))
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                final_mp3 = str(ABS_DOWNLOADS_PATH / f"{file_id}.mp3")

            title = info.get('title', 'audio').replace('/', '_').replace('\\', '_')
            return send_file(final_mp3, as_attachment=True, download_name=f"{title}.mp3", mimetype="audio/mpeg")
        except Exception as e:
            return jsonify({"error": "Download failed", "detail": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
        
