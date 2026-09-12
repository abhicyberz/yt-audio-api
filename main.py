import os
from flask import Flask, request, jsonify, Response
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
        'playlistend': 100, 
        'http_headers': IOS_HEADERS,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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

# Video Download Route (MP4)
@app.route("/download-video", methods=["GET"])
def download_video():
    raw_url = request.args.get("url", "").strip()
    if not raw_url: return jsonify({"error": "Missing url"}), 400
    video_id = raw_url.split("v=")[-1].split("&")[0] if "v=" in raw_url else raw_url.split("/")[-1]

    ydl_opts = {
        'format': 'best/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': IOS_HEADERS
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            media_url = info.get('url')
            if media_url:
                return jsonify({"status": "success", "stream_url": media_url})
            return jsonify({"error": "Video stream not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Audio Download Route (MP3 Server Conversion)
@app.route("/download-audio", methods=["GET"])
def download_audio():
    raw_url = request.args.get("url", "").strip()
    if not raw_url: return jsonify({"error": "Missing url"}), 400
    video_id = raw_url.split("v=")[-1].split("&")[0] if "v=" in raw_url else raw_url.split("/")[-1]

    output_template = f"temp_{video_id}.%(ext)s"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'http_headers': IOS_HEADERS
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"
            
            if os.path.exists(mp3_filename):
                title = info.get('title', 'DJ_ABHISHEK_DADA')
                clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                
                def generate():
                    with open(mp3_filename, "rb") as f:
                        yield from f
                    try:
                        os.remove(mp3_filename)
                    except:
                        pass

                return Response(generate(), mimetype="audio/mpeg", headers={
                    "Content-Disposition": f"attachment; filename={clean_title}.mp3"
                })
        return jsonify({"error": "Could not generate MP3"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()
    
