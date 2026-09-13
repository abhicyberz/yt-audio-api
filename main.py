import requests
from flask import Response, stream_with_context

@app.route("/download-audio", methods=["GET"])
def handle_audio_download():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url"}), 400

    vid = extract_video_id(raw_url)
    video_url = f"https://www.youtube.com/watch?v={vid}"

    ydl_opts = {
        'format': 'ba/b',
        'quiet': True,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            if not stream_url and 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('url')]
                stream_url = audio_formats[-1]['url'] if audio_formats else info['formats'][-1].get('url')

            title = info.get('title', f"DJ_ABHISHEK_{vid}").replace('"', '').replace('/', '_')
            
            # Direct Stream Pipe with Forced Download Header
            req = requests.get(stream_url, stream=True)
            return Response(
                stream_with_context(req.iter_content(chunk_size=1024*64)),
                content_type="audio/mpeg",
                headers={"Content-Disposition": f'attachment; filename="{title}.mp3"'}
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/download-video", methods=["GET"])
def handle_video_download():
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({"status": "error", "message": "Missing url"}), 400

    vid = extract_video_id(raw_url)
    video_url = f"https://www.youtube.com/watch?v={vid}"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            if not stream_url and 'formats' in info:
                prog = [f for f in info['formats'] if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('url')]
                stream_url = prog[-1]['url'] if prog else info['formats'][-1].get('url')

            title = info.get('title', f"DJ_ABHISHEK_{vid}").replace('"', '').replace('/', '_')
            
            req = requests.get(stream_url, stream=True)
            return Response(
                stream_with_context(req.iter_content(chunk_size=1024*128)),
                content_type="video/mp4",
                headers={"Content-Disposition": f'attachment; filename="{title}.mp4"'}
            )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        
