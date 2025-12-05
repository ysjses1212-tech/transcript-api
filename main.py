from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import re

app = Flask(__name__)
CORS(app)

def clean_vtt(text):
    lines = text.split('\n')
    result = []
    for line in lines:
        if '-->' in line or line.startswith('WEBVTT') or line.strip().isdigit():
            continue
        if line.strip() and not line.startswith('Kind:') and not line.startswith('Language:'):
            clean = re.sub(r'<[^>]+>', '', line)
            if clean.strip() and clean.strip() not in result[-1:]:
                result.append(clean.strip())
    return ' '.join(result)

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Transcript API is running"})

@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')
    
    if not video_id:
        return jsonify({"error": "video_id가 필요합니다"}), 400
    
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        result = subprocess.run([
            'yt-dlp',
            '--skip-download',
            '--write-sub',
            '--write-auto-sub',
            '--sub-lang', 'ko,en',
            '--sub-format', 'vtt',
            '-o', f'/tmp/{video_id}',
            url
        ], capture_output=True, text=True, timeout=60)
        
        transcript = ""
        for lang in ['ko', 'en']:
            vtt_file = f'/tmp/{video_id}.{lang}.vtt'
            if os.path.exists(vtt_file):
                with open(vtt_file, 'r', encoding='utf-8') as f:
                    transcript = clean_vtt(f.read())
                os.remove(vtt_file)
                break
        
        if not transcript:
            return jsonify({"error": "자막을 찾을 수 없습니다", "video_id": video_id}), 404
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "transcript": transcript
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({"error": "시간 초과", "video_id": video_id}), 504
    except Exception as e:
        return jsonify({"error": str(e), "video_id": video_id}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
