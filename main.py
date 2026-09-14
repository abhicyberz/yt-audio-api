import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # Frontend se connect hone ke liye zaroori hai

COOKIES_FILE = 'cookies.txt'

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "running", "message": "API is online"})

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json() or {}
    url = data.get('url')
    mode = data.get('mode', 'video')  # 'audio' ya 'video'
    
    if not url:
        return jsonify({'success': False, 'error': 'URL provide karo'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    # Format decide karo (audio ya video)
    if mode == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = 'best[ext=mp4]/best'

    # Agar valid cookies file maujood hai
    if os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Direct media streaming link
            stream_url = info.get('url')
            title = info.get('title', 'Media')
            thumbnail = info.get('thumbnail')
            duration = info.get('duration')

            if not stream_url:
                return jsonify({'success': False, 'error': 'Direct stream link nahi mila'}), 500

            return jsonify({
                'success': True,
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'download_url': stream_url
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
