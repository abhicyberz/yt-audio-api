import os
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import static_ffmpeg

static_ffmpeg.add_paths()

BASE_DIR = Path(__file__).resolve().parent
ABS_DOWNLOADS_PATH = Path("/tmp/downloads")
ABS_DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)

COOKIE_FILE_PATH = BASE_DIR / "cookies.txt"

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def handle_audio_request():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"error": "Missing 'url' parameter in request."}), 400

    if "v=" in raw_url:
        video_id = raw_url.split("v=")[-1].split("&")[0]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
    elif len(raw_url) == 11 and "/" not in raw_url:
        video_url = f"https://www.youtube.com/watch?v={raw_url}"
    else:
        video_url = raw_url

    filename_base = str(uuid4())
    output_template = str(ABS_DOWNLOADS_PATH / f"{filename_base}.%(ext)s")
    final_mp3_name = f"{filename_base}.mp3"

    ydl_opts = {
        'format': 'ba/b',
        'outtmpl': output_template,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['webpage', 'configs', 'js']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.05.36 (Linux; U; Android 14) gzip'
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True
    }

    # Cookies pass karna
    if COOKIE_FILE_PATH.is_file():
        ydl_opts['cookiefile'] = str(COOKIE_FILE_PATH)
    elif Path("cookies.txt").is_file():
        ydl_opts['cookiefile'] = "cookies.txt"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return send_from_directory(ABS_DOWNLOADS_PATH, final_mp3_name, as_attachment=True)
    except Exception as e:
        return jsonify({"error": "Failed to download or convert audio.", "detail": str(e)}), 500


def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
    
