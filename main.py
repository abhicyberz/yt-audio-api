import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import static_ffmpeg

static_ffmpeg.add_paths()

app = Flask(__name__)
CORS(app)

IOS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

@app.route("/channel-tracks", methods=["GET"])
def get_channel_tracks():
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': 100,  # Limit ko thoda badha diya hai taaki aur tracks aayein
        'http_headers': IOS_HEADERS,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # /videos tab use karne se channel ke saare uploads proper extract hote hain
            res = ydl.extract_info("https://www.youtube.com/@dj_abhishek_dada/videos", download=False)
            entries = res.get('entries', [])
            tracks = [
                {"id": item.get("id"), "title": item.get("title", "DJ Track"), "author": "DJ ABHISHEK DADA"}
                for item in entries if item and item.get("id")
            ]
            if not tracks: raise Exception("No tracks found")
            return jsonify({"status": "success", "tracks": tracks})
    except Exception as e:
        fallback_tracks = [
            { "id": "Mnr1eLcCejg", "title": "Ganjawa Pike Bolbam (Humming Bass) Sawan Special", "author": "DJ ABHISHEK DADA" },
            { "id": "YOUD_pqObe0", "title": "Hum Pyar Karne Wale Remix | Hard Bass Mix", "author": "DJ ABHISHEK DADA" },
            { "id": "5-_oKgZhDww", "title": "Gaura Ho Has Da Na (Pawan Singh) Bol Bam Special", "author": "DJ ABHISHEK DADA" },
            { "id": "hakt6kJ4UaA", "title": "Instagram Trending Mix 2026 | Hard Bass Vibration", "author": "DJ ABHISHEK DADA" },
            { "id": "132gBeW2_QA", "title": "Sound Testing | Dj Lucky X Dj Abhishek | Barat SPL", "author": "DJ ABHISHEK DADA" }
        ]
        return jsonify({"status": "success", "tracks": fallback_tracks})

@app.route("/search", methods=["GET"])
def search_youtube():
    query = request.args.get("q", "").strip()
    if not query: 
        return jsonify({"status": "error", "message": "Missing query"}), 400

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'http_headers': IOS_HEADERS,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch50:{query}", download=False)
            entries = res.get('entries', [])
            results = [
                {"id": item.get("id"), "title": item.get("title", "YouTube Track"), "author": item.get("uploader", "YouTube Creator")}
                for item in entries if item and item.get("id")
            ]
            return jsonify({"status": "success", "tracks": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def handle_audio_request():
    raw_url = request.args.get("url", "").strip()
    if not raw_url: 
        return jsonify({"error": "Missing url"}), 400

    if "v=" in raw_url:
        video_id = raw_url.split("v=")[-1].split("&")[0]
    elif len(raw_url) == 11 and "/" not in raw_url:
        video_id = raw_url
    else:
        video_id = raw_url.split("?")[0].split("/")[-1]

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
        'http_headers': IOS_HEADERS
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            audio_url = info.get('url')
            if not audio_url:
                for f in info.get('formats', []):
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        audio_url = f.get('url')
                        break
            if audio_url:
                return jsonify({"status": "success", "stream_url": audio_url})
            return jsonify({"error": "Stream not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
    
