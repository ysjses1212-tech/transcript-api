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
            "videoId": video_id,
            "lang": "ko"
        }
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if response.status_code != 200:
            # 한국어 없으면 영어로 재시도
            params["lang"] = "en"
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
        
        if response.status_code != 200:
            return jsonify({"error": "자막을 찾을 수 없습니다", "video_id": video_id}), 404
        
        # 자막 텍스트 합치기
        if "content" in data:
            transcript = data["content"]
        elif "transcript" in data:
            if isinstance(data["transcript"], list):
                transcript = " ".join([item.get("text", "") for item in data["transcript"]])
            else:
                transcript = data["transcript"]
        else:
            transcript = str(data)
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "transcript": transcript
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "video_id": video_id}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
