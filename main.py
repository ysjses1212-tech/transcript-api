from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

SUPADATA_API_KEY = "sd_5a32b084e1add286bf167cbc40eb564c"
SERPAPI_KEY = "977335de6ae29be45b2de7b51c7bd335ba72d94d876d547a61f9b37455f4964a"

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Transcript & Trends API is running"})

# 자막 API
@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')
    
    if not video_id:
        return jsonify({"error": "video_id가 필요합니다"}), 400
    
    try:
        url = "https://api.supadata.ai/v1/youtube/transcript"
        headers = {"x-api-key": SUPADATA_API_KEY}
        params = {"videoId": video_id}
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if response.status_code != 200:
            return jsonify({"error": "자막을 찾을 수 없습니다", "video_id": video_id}), 404
        
        content = data.get("content", [])
        texts = [item.get("text", "") for item in content if item.get("text") and not item.get("text", "").startswith("[")]
        transcript = " ".join(texts)
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "transcript": transcript
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "video_id": video_id}), 500

# Google Trends API
@app.route('/api/trends', methods=['GET'])
def get_trends():
    keyword = request.args.get('keyword')
    
    if not keyword:
        return jsonify({"error": "keyword가 필요합니다"}), 400
    
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_trends",
            "q": keyword,
            "data_type": "TIMESERIES",
            "api_key": SERPAPI_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        # 트렌드 분석
        trend_type = "unknown"
        keyword_type = "unknown"
        
        if "interest_over_time" in data and "timeline_data" in data["interest_over_time"]:
            timeline = data["interest_over_time"]["timeline_data"]
            values = [t["values"][0]["extracted_value"] for t in timeline[-12:] if t.get("values")]
            
            if len(values) >= 6:
                recent = sum(values[-3:]) / 3
                earlier = sum(values[:-3]) / max(len(values) - 3, 1)
                
                if recent > earlier * 1.5:
                    trend_type = "rising"
                    keyword_type = "shorttail"
                elif earlier > 0:
                    trend_type = "steady"
                    keyword_type = "longtail"
        
        return jsonify({
            "success": True,
            "keyword": keyword,
            "trend_type": trend_type,
            "keyword_type": keyword_type
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "keyword": keyword}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
