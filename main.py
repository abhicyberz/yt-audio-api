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

# 🎵 Safe & Fast Channel Tracks (No Bot-Trigger Full Extraction)
@app.route("/channel-tracks", methods=["GET"])
def get_channel_tracks():
    # Pre-verified robust catalog of your original tracks to prevent bot bans
    safe_tracks = [
        { "id": "Mnr1eLcCejg", "title": "Ganjawa Pike Bolbam (Humming Bass) Sawan Special", "author": "DJ ABHISHEK DADA" },
        { "id": "YOUD_pqObe0", "title": "Hum Pyar Karne Wale Remix | Hard Bass Mix", "author": "DJ ABHISHEK DADA" },
        { "id": "5-_oKgZhDww", "title": "Gaura Ho Has Da Na (Pawan Singh) Bol Bam Special", "author": "DJ ABHISHEK DADA" },
        { "id": "fc3PeS5tq6g", "title": "A BABA FIR SE NIRMAL KAR DA - Hard Bass Bol Bam", "author": "DJ ABHISHEK DADA" },
        { "id": "Yec7wmQiWrY", "title": "BABA KE BUTI (Pawan Singh) Sawan Special Remix", "author": "DJ ABHISHEK DADA" },
        { "id": "3qiNfvDSrRs", "title": "Pawan Singh | Dance Remix | पापे पड़ी", "author": "DJ ABHISHEK DADA" },
        { "id": "FBclHzxx9UI", "title": "O Kanha Tu Hai Kiska Deewana Edm Mix", "author": "DJ ABHISHEK DADA" },
        { "id": "QSbZKOyFV50", "title": "EDM_MIX ×× इंडिया हिली ×× Hard 5G Vibration Mix", "author": "DJ ABHISHEK DADA" },
        { "id": "SsdeFebLfuM", "title": "Marab Marda Ke Goli Edm Vibration Mix", "author": "DJ ABHISHEK DADA" },
        { "id": "5UfhJ2DXtsc", "title": "Jai Bhim Bol ×× Khatarnak Edm Drop Mix", "author": "DJ ABHISHEK DADA" },
        { "id": "IKQluTUIDW4", "title": "Gauwa Ke Purube Kahe | Old Bhakti Dance Mix", "author": "DJ ABHISHEK DADA" },
        { "id": "snFAQzgG5yA", "title": "Dilwa Dole Thode Thode - Ankush Raja Remix", "author": "DJ ABHISHEK DADA" },
        { "id": "o7xYl27L_3s", "title": "Lahanga Me Meter Ba - Ultra Humming Bass", "author": "DJ ABHISHEK DADA" },
        { "id": "mJ94EaKx_7I", "title": "Hari Hari Odhani - 2026 Club Edit", "author": "DJ ABHISHEK DADA" },
        { "id": "67i6AoxgZ_A", title: "Kashi Me Bam Bhole - Heavy Trance Bolbam", "author": "DJ ABHISHEK DADA" },
        { "id": "wL3pWq10e-s", title: "Kamar Khesari Ke Gaana - Power Bass Mix", "author": "DJ ABHISHEK DADA" }
    ]
    return jsonify({"status": "success", "tracks": safe_tracks})

# 🔍 Smart Search (Anti-Bot Configured)
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
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'],
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch20:{query}", download=False)
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

# ⬇ Audio Download Pipeline with Jitter Queue
@app.route("/", methods=["GET"])
def handle_audio_request():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

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
                'player_client': ['ios', 'android', 'web_embedded'],
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X; en_US)',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate'
        },
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
            return send_file(
                final_mp3,
                as_attachment=True,
                download_name=f"{title}.mp3",
                mimetype="audio/mpeg"
            )
        except Exception as e:
            return jsonify({"error": "Download failed", "detail": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
    
