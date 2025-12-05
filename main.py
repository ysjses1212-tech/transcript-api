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
    seen = set()
    for line in lines:
        if '-->' in line or line.startswith('WEBVTT') or line.strip().isdigit():
            continue
        if line.strip() and not line.startswith('Kind:') and not line.startswith('Language:'):
            clean = re.sub(r'<[^>]+>', '', line).strip()
            if clean and clean not in seen:
                seen.add(clean)
                result.append(clean)
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
        
        # yt-dlp 버전 확인
        version_check = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        
        # 자막 다운로드 시도
        result = subprocess.run([
            'yt-dlp',
            '--skip-download',
            '--write-sub',
            '--write-auto-sub',
            '--sub-lang', 'ko,en,ko-auto,en-auto',
            '--sub-format', 'vtt/srt/best',
            '-o', f'/tmp/{video_id}',
            '--no-warnings',
            url
        ], capture_output=True, text=True, timeout=120)
        
        # 디버그 정보
        debug_info = {
            "yt_dlp_version": version_check.stdout.strip(),
            "stdout": result.stdout[:500] if result.stdout else None,
            "stderr": result.stderr[:500] if result.stderr else None,
            "return_code": result.returncode
        }
        
        # 파일 찾기
        transcript = ""
        found_file = None
        tmp_files = os.listdir('/tmp') if os.path.exists('/tmp') else []
        matching_files = [f for f in tmp_files if video_id in f]
        
        for f in matching_files:
            if f.endswith('.vtt') or f.endswith('.srt'):
                filepath = f'/tmp/{f}'
                with open(filepath, 'r', encoding='utf-8') as file:
                    transcript = clean_vtt(file.read())
                found_file = f
                os.remove(filepath)
                break
        
        if not transcript:
            return jsonify({
                "error": "자막을 찾을 수 없습니다",
                "video_id": video_id,
                "debug": debug_info,
                "matching_files": matching_files
            }), 404
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "transcript": transcript,
            "file_used": found_file
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({"error": "시간 초과", "video_id": video_id}), 504
    except Exception as e:
        return jsonify({"error": str(e), "video_id": video_id}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
