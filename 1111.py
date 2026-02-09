# check_models.py
# 내 API 키로 사용할 수 있는 Gemini 모델 명단 조회

import google.generativeai as genai
import config
import os

# 경고 무시
os.environ["GRPC_VERBOSITY"] = "ERROR"

print("🔍 Google API에 모델 목록을 조회 중입니다...")

try:
    genai.configure(api_key=config.GOOGLE_API_KEY)
    
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            name = m.name.replace("models/", "")
            available_models.append(name)
            print(f"  - {name}")

    print("\n✅ 조회 완료! 위 목록 중 하나를 config.py에 적으세요.")
    
    # 추천 로직
    if "gemini-2.0-flash" in available_models:
        print("👉 추천: 'gemini-2.0-flash' (가장 최신/빠름)")
    elif "gemini-1.5-flash" in available_models:
        print("👉 추천: 'gemini-1.5-flash'")
        
except Exception as e:
    print(f"❌ 조회 실패: {e}")
    print("API 키가 올바른지, 인터넷이 연결되었는지 확인하세요.")