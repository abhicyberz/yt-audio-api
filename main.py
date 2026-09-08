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

# 🔒 Traffic Controller: Ek waqt par YouTube par sirf 2 download requests execute hongi
# Baki sab safe queue mein line lagakar aaram se process hongi
DOWNLOAD_SEMAPHORE = BoundedSemaphore(value=2)

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

    # Anti-bot options
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

    # Queue Buffer: User request line mein wait karegi jab tak pehla download complete na ho
    with DOWNLOAD_SEMAPHORE:
        # Human Jitter: Har request ke beech 1 se 2.5 second ka random human delay
        time.sleep(random.uniform(1.0, 2.5))

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
    
