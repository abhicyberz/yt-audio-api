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

IOS_HEADERS = {
    'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X; en_US)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Sec-Fetch-Mode': 'navigate',
}

# 🎵 Live Channel Fetch with Fallback Safety
@app.route("/channel-tracks", methods=["GET"])
def get_channel_tracks():
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': 50, 
        'http_headers': IOS_HEADERS,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web'],
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Removed /videos to prevent tab extraction failure
            res = ydl.extract_info("https://www.youtube.com/@dj_abhishek_dada", download=False)
            entries = res.get('entries', [])
            tracks = [
                {
                    "id": item.get("id"),
                    "title": item.get("title", "DJ Track"),
                    "author": "DJ ABHISHEK DADA"
                }
                for item in entries if item and item.get("id")
            ]
            if not tracks:
                raise Exception("No tracks found in entries")
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        # Fallback default tracks so frontend never breaks due to network/parsing error
        fallback_tracks = [
            { "id": "Mnr1eLcCejg", "title": "Ganjawa Pike Bolbam (Humming Bass) Sawan Special", "author": "DJ ABHISHEK DADA" },
            { "id": "YOUD_pqObe0", "title": "Hum Pyar Karne Wale Remix | Hard Bass Mix", "author": "DJ ABHISHEK DADA" },
            { "id": "5-_oKgZhDww", "title": "Gaura Ho Has Da Na (Pawan Singh) Bol Bam Special", "author": "DJ ABHISHEK DADA" },
            { "id": "hakt6kJ4UaA", "title": "Instagram Trending Mix 2026 | Hard Bass Vibration", "author": "DJ ABHISHEK DADA" },
            { "id": "132gBeW2_QA", "title": "Sound Testing | Dj Lucky X Dj Abhishek | Barat SPL", "author": "DJ ABHISHEK DADA" }
        ]
        return jsonify({"status": "success", "tracks": fallback_tracks})

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
        'http_headers': IOS_HEADERS,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web'],
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

# ⬇ Audio Download Pipeline
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
                'player_client': ['ios', 'web'],
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_headers': IOS_HEADERS,
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
            
