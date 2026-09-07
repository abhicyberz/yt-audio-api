import os
import threading
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import static_ffmpeg

# Static ffmpeg paths add karein
static_ffmpeg.add_paths()

# Downloads folder path define karein
ABS_DOWNLOADS_PATH = Path("/tmp/downloads")
ABS_DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)

# Flask application initialize karein
app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def handle_audio_request():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "Missing 'url' parameter in request."}), 400

    filename = f"{uuid4()}.mp3"
    output_path = ABS_DOWNLOADS_PATH / filename

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path),
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'ios', 'android']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return send_from_directory(ABS_DOWNLOADS_PATH, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": "Failed to download or convert audio.", "detail": str(e)}), 500


def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
    
