# ai_analyst.py
# [V11 Economy] GPT 제거 -> Gemini가 의장직 겸임 (비용 절감 + 속도 향상)

import json
import requests
import re
import warnings
import os
import config

# [1] 경고 메시지 차단
os.environ["GRPC_VERBOSITY"] = "ERROR"
warnings.filterwarnings("ignore")

import google.generativeai as genai
from anthropic import Anthropic

class AIAnalyst:
    def __init__(self):
        print("\n🔍 [AI Analyst] 초기화 (Gemini 의장 체제)...")
        
        # 1. ChatGPT 제거 (비용 문제)
        # self.openai_client = ... (삭제)
        
        # 2. Gemini (공격수 & 의장)
        genai.configure(api_key=config.GOOGLE_API_KEY)
        bull_model = config.MODEL_BULL.strip()
        print(f"   👉 Gemini Model: '{bull_model}' (공격수 + 의장)") 
        self.gemini_model = genai.GenerativeModel(bull_model)
        
        # 3. Claude (수비수)
        bear_model = config.MODEL_BEAR.strip()
        print(f"   👉 Claude Model: '{bear_model}' (수비수)")
        self.claude_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    # ---------------------------------------------------------
    # 📰 1. 뉴스 데이터 수집
    # ---------------------------------------------------------
    def get_crypto_news(self):
        base_url = "https://cryptopanic.com/api/developer/v2/posts/"
        params = {
            "auth_token": config.CRYPTOPANIC_API_KEY,
            "public": "true",
            "filter": "hot",
            "kind": "news"
        }
        
        try:
            if not config.CRYPTOPANIC_API_KEY: return "API Key missing."
            
            resp = requests.get(base_url, params=params, timeout=10)
            data = resp.json()
            
            if 'results' not in data: return "News fetch failed."

            news_list = [post['title'] for post in data['results']]
            if not news_list: return "No news found."
            
            print(f"📰 [News] V2 API로 뉴스 {len(news_list)}건 수집 완료")
            return "\n".join(news_list)

        except:
            return "Market data unavailable."

    def get_fear_greed_index(self):
        try:
            url = "https://api.alternative.me/fng/"
            resp = requests.get(url, timeout=5).json()
            return int(resp['data'][0]['value'])
        except:
            return 50

    # ---------------------------------------------------------
    # 🔧 2. JSON 파싱 및 데이터 보정
    # ---------------------------------------------------------
    def _parse_json(self, text):
        try:
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```', '', text)
            text = text.strip()
            
            start_index = text.find('{')
            end_index = text.rfind('}')
            if start_index != -1 and end_index != -1:
                text = text[start_index : end_index + 1]
            else:
                return None
            
            data = json.loads(text)

            if 'STOP_LOSS' in data:
                sl = float(data['STOP_LOSS'])
                if sl > 0: data['STOP_LOSS'] = -sl
                
            return data

        except Exception as e:
            print(f"🚨 [JSON 파싱 실패] 내용: {text[:50]}... 원인: {e}")
            return None

    # ---------------------------------------------------------
    # 🦁 3. Gemini (공격수)
    # ---------------------------------------------------------
    def ask_gemini_bull(self, news, fng):
        prompt = f"""
        Role: You are a **High-Frequency Trading (HFT) Alpha Strategist**.
        [Market Context] FNG: {fng}, News:\n{news}
        [Task] Propose **aggressive** parameters (High RSI, Loose StopLoss).
        Format: JSON only {{ "RSI_BUY": int, "STOP_LOSS": float, "KIMP_MAX": float }}
        """
        try:
            resp = self.gemini_model.generate_content(prompt)
            return self._parse_json(resp.text)
        except Exception as e:
            print(f"⚠️ [Gemini Bull] 오류: {e}")
            return None

    # ---------------------------------------------------------
    # 🐢 4. Claude (수비수)
    # ---------------------------------------------------------
    def ask_claude_bear(self, news, fng):
        prompt = f"""
        Role: You are the **Chief Risk Officer (CRO)**.
        [Market Context] FNG: {fng}, News:\n{news}
        [Task] Propose **defensive** parameters (Low RSI, Tight StopLoss).
        Format: JSON only {{ "RSI_BUY": int, "STOP_LOSS": float, "KIMP_MAX": float }}
        """
        try:
            msg = self.claude_client.messages.create(
                model=config.MODEL_BEAR.strip(),
                max_tokens=250,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_json(msg.content[0].text)
        except Exception as e:
            print(f"⚠️ [Claude Bear] 오류: {e}")
            return None

    # ---------------------------------------------------------
    # 👨‍⚖️ 5. Gemini (의장 - GPT 대체)
    # ---------------------------------------------------------
    def ask_chairman(self, news, fng, bull_view, bear_view):
        """👨‍⚖️ Gemini가 의장 역할 수행 (비용 무료, 속도 빠름)"""
        print("   ⏳ 의장(Gemini)에게 최종 결정 요청 중...")
        prompt = f"""
        Role: You are the **Chief Investment Officer (CIO)**.
        
        [Market Data]
        - FNG Index: {fng}
        - News: {news[:500]}
        
        [Staff Opinions]
        - 🦁 Bull (Aggressive): {bull_view}
        - 🐢 Bear (Conservative): {bear_view}

        [Task]
        Synthesize opinions.
        - Bad News -> Follow Bear.
        - Good News -> Follow Bull.
        - Mixed -> Balanced.

        [Output Format]
        Return ONLY a JSON object:
        {{ 
            "RSI_BUY_THRESHOLD": int, 
            "MAX_KIMP_THRESHOLD": float, 
            "STOP_LOSS_PCT": float, 
            "MAX_TICKS_FOR_BEP": int, 
            "PARTIAL_SELL_MIN_PROFIT": float, 
            "TRAILING_START": float, 
            "REASON": "string summary" 
        }}
        """
        try:
            # OpenAI 대신 Gemini 모델 사용
            resp = self.gemini_model.generate_content(prompt)
            return self._parse_json(resp.text)
        except Exception as e:
            print(f"🚨 [Chairman Error] 합의 실패: {e}")
            return None

    # ---------------------------------------------------------
    # 🚀 메인 실행 함수
    # ---------------------------------------------------------
    def get_consensus_params(self):
        print("\n🧠 [AI Analyst] 3대 AI 위원회 소집 (Gemini + Claude)...")
        
        news = self.get_crypto_news()
        fng = self.get_fear_greed_index()
        
        bull = self.ask_gemini_bull(news, fng)
        bear = self.ask_claude_bear(news, fng)
        
        if not bull or not bear:
            print("⚠️ 위원 의견 수렴 실패 -> 기본 로직 사용")
            return None

        print(f"   ✅ 🦁 Gemini(공격): RSI {bull.get('RSI_BUY')}, 손절 {bull.get('STOP_LOSS')}%")
        print(f"   ✅ 🐢 Claude(수비): RSI {bear.get('RSI_BUY')}, 손절 {bear.get('STOP_LOSS')}%")

        # 의장 호출 (GPT 대신 Gemini 함수 사용)
        final_decision = self.ask_chairman(news, fng, bull, bear)
        
        if final_decision:
            print(f"   ✅ 👨‍⚖️ 의장(Gemini) 승인 완료: {final_decision.get('REASON')}")
            return final_decision
        else:
            return None

if __name__ == "__main__":
    ai = AIAnalyst()
    print(ai.get_consensus_params())
