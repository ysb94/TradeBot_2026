# ai_analyst.py
# [V14 Revert] 의장(Chairman) 권한을 ChatGPT(GPT-4o)로 복구 + 디버깅 모드

import json
import requests
import re
import warnings
import os
import pandas as pd
import config
import traceback

# [1] 경고 메시지 차단
os.environ["GRPC_VERBOSITY"] = "ERROR"
warnings.filterwarnings("ignore")

import openai # ✅ OpenAI 라이브러리 부활
import google.generativeai as genai
from anthropic import Anthropic

class AIAnalyst:
    def __init__(self):
        print("\n🔍 [AI Analyst] 초기화 (GPT-4o 의장 체제)...")
        
        # 1. ChatGPT (의장) - ✅ 복구됨
        try:
            self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            print(f"   👉 Chairman Model: '{config.MODEL_CHAIRMAN}' (OpenAI)")
        except Exception as e:
            print(f"   🚨 OpenAI 초기화 실패: {e}")

        # 2. Gemini (공격수)
        try:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            bull_model = config.MODEL_BULL.strip()
            print(f"   👉 Bull Model: '{bull_model}' (Gemini)") 
            self.gemini_model = genai.GenerativeModel(bull_model)
        except Exception as e:
            print(f"   🚨 Gemini 초기화 실패: {e}")
        
        # 3. Claude (수비수)
        try:
            bear_model = config.MODEL_BEAR.strip()
            print(f"   👉 Bear Model: '{bear_model}' (Claude)")
            self.claude_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        except Exception as e:
            print(f"   🚨 Claude 초기화 실패: {e}")

    # =========================================================
    # 🛠 유틸리티 함수
    # =========================================================
    def _parse_json(self, text, source="Unknown"):
        try:
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```', '', text)
            text = text.strip()
            
            start_index = text.find('{')
            end_index = text.rfind('}')
            
            if start_index != -1 and end_index != -1:
                json_text = text[start_index : end_index + 1]
            else:
                print(f"   ⚠️ [{source}] JSON 형식이 아님. 원본: {text[:100]}...")
                return None
            
            data = json.loads(json_text)
            
            if 'STOP_LOSS' in data:
                sl = float(data['STOP_LOSS'])
                if sl > 0: data['STOP_LOSS'] = -sl
                
            return data

        except Exception as e:
            print(f"   🚨 [{source}] 파싱 에러: {e}")
            return None

    # =========================================================
    # 📰 Part 1. 거시경제 분석
    # =========================================================
    def get_crypto_news(self):
        print("   📰 뉴스 수집 중...")
        base_url = "https://cryptopanic.com/api/developer/v2/posts/"
        params = {"auth_token": config.CRYPTOPANIC_API_KEY, "public": "true", "filter": "hot", "kind": "news"}
        try:
            if not config.CRYPTOPANIC_API_KEY: return "API Key missing."
            resp = requests.get(base_url, params=params, timeout=10)
            data = resp.json()
            if 'results' not in data: return "News fetch failed."
            news_list = [post['title'] for post in data['results']]
            if not news_list: return "No news found."
            print(f"   ✅ 뉴스 {len(news_list)}건 수집 완료")
            return "\n".join(news_list)
        except: return "Market data unavailable."

    def get_fear_greed_index(self):
        try:
            url = "https://api.alternative.me/fng/"
            resp = requests.get(url, timeout=5).json()
            return int(resp['data'][0]['value'])
        except: return 50

    def ask_gemini_bull_macro(self, news, fng):
        print("   🦁 [Gemini] 공격수 의견 청취 중...")
        prompt = f"""
        Role: Aggressive Crypto Trader.
        [Context] FNG: {fng}, News:\n{news[:1000]}
        [Task] Propose aggressive parameters.
        Format: JSON only {{ "RSI_BUY": int, "STOP_LOSS": float, "KIMP_MAX": float }}
        """
        try:
            resp = self.gemini_model.generate_content(prompt)
            return self._parse_json(resp.text, "Gemini Bull")
        except Exception as e:
            print(f"   🚨 Gemini 오류: {e}")
            return None

    def ask_claude_bear_macro(self, news, fng):
        print("   🐢 [Claude] 수비수 의견 청취 중...")
        prompt = f"""
        Role: Conservative Risk Manager.
        [Context] FNG: {fng}, News:\n{news[:1000]}
        [Task] Propose defensive parameters.
        Format: JSON only {{ "RSI_BUY": int, "STOP_LOSS": float, "KIMP_MAX": float }}
        """
        try:
            msg = self.claude_client.messages.create(
                model=config.MODEL_BEAR.strip(),
                max_tokens=250,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_json(msg.content[0].text, "Claude Bear")
        except Exception as e:
            print(f"   🚨 Claude 오류: {e}")
            return None

    def ask_chairman_macro(self, news, fng, bull, bear):
        print("   👨‍⚖️ [Chairman] GPT-4o 의장에게 최종 결정 요청 중...")
        prompt = f"""
        Role: Chief Investment Officer (CIO).
        [Context] FNG: {fng}, News: {news[:500]}
        [Opinions] Bull: {bull}, Bear: {bear}
        [Task] Synthesize strategy.
        Format: JSON only {{ "RSI_BUY_THRESHOLD": int, "MAX_KIMP_THRESHOLD": float, "STOP_LOSS_PCT": float, "MAX_TICKS_FOR_BEP": int, "PARTIAL_SELL_MIN_PROFIT": float, "TRAILING_START": float, "REASON": "summary" }}
        """
        try:
            # ✅ OpenAI API 호출 (의장)
            resp = self.openai_client.chat.completions.create(
                model=config.MODEL_CHAIRMAN,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            print(f"   🚨 Chairman(OpenAI) 오류: {e}")
            return None

    def get_consensus_params(self):
        print("\n🧠 [Macro] AI 위원회 소집 (GPT 의장)...")
        news = self.get_crypto_news()
        fng = self.get_fear_greed_index()
        
        bull = self.ask_gemini_bull_macro(news, fng)
        bear = self.ask_claude_bear_macro(news, fng)
        
        if not bull or not bear:
            print("   ⚠️ 위원 의견 수렴 실패")
            return None
        
        final = self.ask_chairman_macro(news, fng, bull, bear)
        if final:
            print(f"   ✅ 전략 수립 완료: {final.get('REASON')}")
            return final
        return None

    # =========================================================
    # 📈 Part 2. 차트 패턴 정밀 분석
    # =========================================================
    def _df_to_string(self, df):
        return df[['open', 'high', 'low', 'close', 'volume']].tail(30).to_string()

    def ask_bull_chart(self, ticker, chart_str):
        prompt = f"""Target: {ticker}\nData:\n{chart_str}\nTask: Find BULLISH patterns. Output JSON {{ "opinion": "BUY"/"WAIT", "reason": "brief" }}"""
        try:
            resp = self.gemini_model.generate_content(prompt)
            return self._parse_json(resp.text, "Bull Chart")
        except: return {"opinion": "WAIT", "reason": "Error"}

    def ask_bear_chart(self, ticker, chart_str):
        prompt = f"""Target: {ticker}\nData:\n{chart_str}\nTask: Find RISKS. Output JSON {{ "opinion": "BUY"/"WAIT", "reason": "brief" }}"""
        try:
            msg = self.claude_client.messages.create(
                model=config.MODEL_BEAR.strip(),
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_json(msg.content[0].text, "Bear Chart")
        except: return {"opinion": "WAIT", "reason": "Error"}

    def ask_chairman_chart(self, ticker, chart_str, bull, bear):
        prompt = f"""
        Role: Head Trader. Target: {ticker}
        Opinions: Bull({bull.get('opinion')}), Bear({bear.get('opinion')})
        Data:\n{chart_str}
        Task: Final GO/NO-GO decision.
        Output JSON {{ "decision": "APPROVE"/"REJECT", "reason": "summary" }}
        """
        try:
            # ✅ OpenAI API 호출 (의장)
            resp = self.openai_client.chat.completions.create(
                model=config.MODEL_CHAIRMAN,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(resp.choices[0].message.content)
        except: return {"decision": "REJECT", "reason": "Chairman Error"}

    def verify_buy_signal_consensus(self, ticker, df_ohlcv):
        print(f"   🧠 [Chartist] {ticker} 3대 AI 긴급 회의 (GPT 의장)...")
        chart_str = self._df_to_string(df_ohlcv)
        
        bull_res = self.ask_bull_chart(ticker, chart_str)
        bear_res = self.ask_bear_chart(ticker, chart_str)
        
        # 안전장치
        bull_op = bull_res.get('opinion', 'WAIT') if bull_res else 'WAIT'
        bear_op = bear_res.get('opinion', 'WAIT') if bear_res else 'WAIT'
        
        print(f"      🦁 Bull: {bull_op} | 🐢 Bear: {bear_op}")
        
        final_res = self.ask_chairman_chart(ticker, chart_str, bull_res, bear_res)
        return final_res

if __name__ == "__main__":
    ai = AIAnalyst()
    print(ai.get_consensus_params())