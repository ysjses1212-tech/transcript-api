from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

SUPADATA_API_KEY = "sd_5a32b984e1add286bf167cbc40eb564c"

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Transcript API is running"})

@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')
    
    if not video_id:
        return jsonify({"error": "video_id가 필요합니다"}), 400
    
    try:
        # Supadata API 호출
        url = f"https://api.supadata.ai/v1/youtube/transcript"
        headers = {
            "x-api-key": SUPADATA_API_KEY
        }
        params = {
            "videoId": video_id
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        # 디버그: 원본 응답 그대로 반환
        return jsonify({
            "status_code": response.status_code,
            "video_id": video_id,
            "raw_response": response.json() if response.text else None,
            "response_text": response.text[:1000] if response.text else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "video_id": video_id}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
