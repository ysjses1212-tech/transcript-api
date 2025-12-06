from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import re

app = Flask(__name__)
CORS(app)

SUPADATA_API_KEY = "sd_5a32b084e1add286bf167cbc40eb564c"
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

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
        prompt = f"""너는 유튜브 키워드 전문가야. 다음 영상에서 "검색용 키워드"를 추출해.

제목: {title}
설명: {description}
스크립트: {transcript[:1500] if transcript else '없음'}

**중요: 스크립트는 자동생성 자막이라 오타가 많아!**
- 문맥을 보고 올바른 단어로 보정해서 키워드 추출해
- 예시: "스캔팬" → "스텐팬", "고릴나" → "고릴라", "에프16" → "F-16"
- 제목과 스크립트를 비교해서 올바른 표기 판단해

**추출 규칙:**

1. 반드시 제외할 대형 카테고리 키워드:
   - 동물, 식물, 사람, 인간, 남자, 여자, 음식, 요리, 여행, 스포츠, 게임, 영화, 음악
   - 자연, 과학, 역사, 경제, 정치, 기술, 건강, 교육, 엔터테인먼트, 예능, 뉴스
   - 이런 "분류/카테고리" 수준의 추상적 단어는 절대 포함하지 마

2. 추출해야 할 키워드:
   - 영상의 구체적인 주제/소재 (예: 고릴라, 와사비, 손흥민, 참치해체, 트랩)
   - 사람들이 유튜브에서 실제로 검색할 구체적인 단어
   - 고유명사 우선 (인물명, 브랜드명, 특정 동물/식물 종류, 지명)

3. 복합 키워드도 포함 가능:
   - 단일: 고릴라, 와사비, 트랩
   - 복합: 실버백 고릴라, 와사비 강판, 전장 트랩

4. 3~5개만 추출

5. JSON 배열로만 응답

예시:
- 좋은 키워드: ["고릴라", "실버백", "괴력", "침팬지"]
- 나쁜 키워드: ["동물", "자연", "영상", "방법"]

응답 (JSON 배열만):"""


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
