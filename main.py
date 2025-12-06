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
@app.route('/api/extract-keywords', methods=['POST'])
def extract_keywords():
    data = request.get_json()
    
    title = data.get('title', '')
    description = data.get('description', '')
    tags = data.get('tags', [])
    transcript = data.get('transcript', '')
    
    if not title:
        return jsonify({"error": "title이 필요합니다"}), 400
    
    try:
        # Gemini API 호출
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""다음 유튜브 영상 정보를 분석해서 검색 키워드를 추출해줘.

제목: {title}
태그: {', '.join(tags) if tags else '없음'}
설명: {description[:500] if description else '없음'}
스크립트: {transcript[:1000] if transcript else '없음'}

규칙:
1. 사람들이 유튜브에서 실제로 검색할만한 키워드만 추출
2. 명사 또는 명사구만 추출 (동사, 형용사, 조사 제외)
3. 최소 2글자 이상
4. 최대 5개까지만 추출
5. 중요도 순으로 정렬
6. 브랜드명, 제품명, 주제어, 인물명 우선

응답 형식 (JSON만, 다른 텍스트 없이):
{{"keywords": ["키워드1", "키워드2", "키워드3"]}}
"""
        
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 200
            }
        }
        
        response = requests.post(url, headers=headers, json=body)
        result = response.json()
        
        # 응답에서 키워드 추출
        if "candidates" in result and len(result["candidates"]) > 0:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # JSON 파싱 시도
            try:
                # JSON 부분만 추출
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    keywords_data = json.loads(json_match.group())
                    keywords = keywords_data.get("keywords", [])
                else:
                    keywords = []
            except:
                # JSON 파싱 실패시 텍스트에서 추출
                keywords = re.findall(r'"([^"]+)"', text)[:5]
            
            return jsonify({
                "success": True,
                "keywords": keywords,
                "videoType": "keyword" if len(keywords) >= 2 else "content"
            })
        else:
            return jsonify({"error": "Gemini 응답 오류", "raw": result}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
