from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import re

app = Flask(__name__)
CORS(app)

SUPADATA_API_KEY = "sd_5a32b084e1add286bf167cbc40eb564c"
SERPAPI_KEY = "977335de6ae29be45b2de7b51c7bd335ba72d94d876d547a61f9b37455f4964a"
GEMINI_API_KEY = "AIzaSyAehoi3X5r0zC89gjQnQr_UD5q0pJyTBIk"

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "TubeDash API Server"})

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

# Gemini 키워드 추출 API (신규!)
@app.route('/api/extract-keywords', methods=['GET', 'POST'])
def extract_keywords():
    # GET 또는 POST 둘 다 처리
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title', '')
        description = data.get('description', '')
        transcript = data.get('transcript', '')
    else:
        title = request.args.get('title', '')
        description = request.args.get('description', '')
        transcript = request.args.get('transcript', '')
    
    if not title:
        return jsonify({"error": "title이 필요합니다"}), 400
    
    try:
        # Gemini API 호출
        prompt = f"""다음 유튜브 영상에서 검색용 키워드를 추출해줘.

제목: {title}
설명: {description}
스크립트: {transcript[:2000] if transcript else '없음'}

규칙:
1. 명사 위주로 추출 (동사/형용사/조사 제외)
2. 사람들이 실제로 검색할만한 단어만
3. 3~5개만 추출
4. 한국어와 영어 모두 가능
5. JSON 배열로만 응답: ["키워드1", "키워드2", "키워드3"]

응답:"""

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1}
            }
        )
        
        result = response.json()
        
        # Gemini 응답에서 텍스트 추출
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '[]')
        
        # JSON 파싱
        import re
        json_match = re.search(r'\[.*?\]', text, re.DOTALL)
        if json_match:
            keywords = json.loads(json_match.group())
        else:
            keywords = []
        
        return jsonify({
            "success": True,
            "keywords": keywords,
            "videoType": "keyword" if len(keywords) >= 2 else "content"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
