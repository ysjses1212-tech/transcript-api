from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import re

app = Flask(__name__)
CORS(app)

SUPADATA_API_KEY = "sd_5a32b084e1add286bf167cbc40eb564c"
GEMINI_API_KEY = "AIzaSyAehoi3X5r0zC89gjQnQr_UD5q0pJyTBIk"

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Transcript API is running"})

@app.route('/api/transcript', methods=['GET'])
def get_transcript():
    video_id = request.args.get('video_id')
    lang = request.args.get('lang', 'ko')
    
    if not video_id:
        return jsonify({"error": "video_id가 필요합니다"}), 400
    
    try:
        url = "https://api.supadata.ai/v1/youtube/transcript"
        headers = {"x-api-key": SUPADATA_API_KEY}
        params = {"videoId": video_id, "lang": lang}
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if response.status_code != 200:
            if lang == "ko":
                params["lang"] = "en"
                response = requests.get(url, headers=headers, params=params)
                data = response.json()
        
        if response.status_code != 200:
            return jsonify({"error": "자막을 찾을 수 없습니다", "video_id": video_id}), 404
        
        content = data.get("content", [])
        texts = []
        for item in content:
            text = item.get("text", "")
            if text and not text.startswith("["):
                texts.append(text)
        
        transcript = " ".join(texts)
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "lang": data.get("lang", lang),
            "transcript": transcript
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "video_id": video_id}), 500

@app.route('/api/extract-keywords', methods=['GET', 'POST'])
def extract_keywords():
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
        prompt = f"""유튜브 영상의 검색 키워드를 추출해.

제목: {title}
설명: {description}
스크립트: {transcript[:1000] if transcript else '없음'}

지시사항:
- 검색용 명사 키워드 3~5개 추출
- JSON 배열로만 응답: ["키워드1", "키워드2"]

응답:"""

        gemini_response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            },
            timeout=30
        )
        
        status_code = gemini_response.status_code
        
        try:
            result = gemini_response.json()
        except:
            result = {"parse_error": gemini_response.text[:500]}
        
        raw_text = ""
        keywords = []
        
        if 'candidates' in result:
            try:
                raw_text = result['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\[.*?\]', raw_text, re.DOTALL)
                if json_match:
                    keywords = json.loads(json_match.group())
            except Exception as parse_err:
                raw_text = f"파싱에러: {str(parse_err)}"
        
        return jsonify({
            "success": True,
            "keywords": keywords,
            "videoType": "keyword" if len(keywords) >= 2 else "content",
            "debug": {
                "status_code": status_code,
                "raw_text": raw_text[:300] if raw_text else "없음",
                "result_keys": list(result.keys()) if isinstance(result, dict) else "not_dict"
            }
        })
        
    except requests.exceptions.Timeout:
        return jsonify({"error": "Gemini 타임아웃", "type": "timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e), "type": "exception"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
