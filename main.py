import os
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

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
        # Direct best m4a audio stream
        'format': '140/ba[ext=m4a]/bestaudio',
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,
    }

    if COOKIE_FILE_PATH.is_file():
        ydl_opts['cookiefile'] = str(COOKIE_FILE_PATH)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        # Force browser to download as audio file
        return send_file(
            downloaded_file,
            as_attachment=True,
            download_name=f"{info.get('title', 'audio')}.m4a",
            mimetype="audio/mp4"
        )
    except Exception as e:
        return jsonify({"error": "Download failed", "detail": str(e)}), 500


def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
    
