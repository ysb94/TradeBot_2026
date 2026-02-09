# market_scanner.py
# [V3 Integrated] 차트 분석 + AI 위원회(Ensemble) 통합 전략

import pyupbit
import time
import requests
from strategy.indicators import TechnicalAnalyzer
import config
from ai_analyst import AIAnalyst # ✅ 신규 모듈 임포트

class MarketScanner:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.ai_analyst = AIAnalyst() # AI 객체 생성

    def get_all_krw_tickers(self):
        try: return pyupbit.get_tickers(fiat="KRW")
        except: return []

    def get_top_volume_coins(self, limit=30):
        # ... (기존 유동성 조회 로직 유지) ...
        try:
            tickers = self.get_all_krw_tickers()
            if not tickers: return []
            url = "https://api.upbit.com/v1/ticker"
            params = {"markets": ",".join(tickers)}
            resp = requests.get(url, params=params).json()
            sorted_data = sorted(resp, key=lambda x: x['acc_trade_price_24h'], reverse=True)
            return [item['market'] for item in sorted_data[:limit]]
        except: return []

    def scan_market(self):
        """
        [1. 차트 분석] 기술적 지표로 1차 타겟 선정
        """
        candidates = self.get_top_volume_coins(limit=40)
        selected_coins = {}
        
        # 일단 안전하게 비트, 이더, 리플은 기본 포함
        defaults = {"KRW-BTC": "btcusdt", "KRW-ETH": "ethusdt", "KRW-XRP": "xrpusdt"}
        
        print(f"\n🔍 [Scanner] 기술적 타겟 발굴 시작 ({len(candidates)}개)...")
        for ticker in candidates:
            try:
                if ticker in defaults: continue # 기본 타겟은 나중에 합침
                time.sleep(0.05)
                df = pyupbit.get_ohlcv(ticker, interval="minute15", count=60)
                if df is None: continue

                analysis = self.analyzer.analyze_1m_candle(df)
                
                # 기술적 필터 (RSI 40 이하 or 볼밴 하단) - 느슨하게 잡음 (AI가 거를 거니까)
                if analysis['RSI_14'] <= 40 or analysis['is_oversold']:
                    symbol = ticker.replace("KRW-", "").lower() + "usdt"
                    selected_coins[ticker] = symbol
            except: continue
        
        # 타겟이 너무 적으면 기본 종목 추가
        if len(selected_coins) < 3:
            selected_coins.update(defaults)
            
        return selected_coins

def get_strategy_recommendation():
    """
    [Main Logic] 차트 타겟 + AI 파라미터 융합
    """
    scanner = MarketScanner()
    
    # 1. 기술적 분석으로 타겟 코인 선정
    tech_targets = scanner.scan_market()
    
    # 2. AI 위원회 소집 (뉴스 + 거시경제 분석)
    #    (API 호출 실패 시 None 반환)
    ai_params = scanner.ai_analyst.get_consensus_params()
    
    final_params = {}

    # [Case A] AI가 성공적으로 전략을 줬을 때 -> AI 의견 전적으로 채택
    if ai_params:
        print(f"🧠 [Strategy] AI 위원회 전략 적용 완료")
        final_params = ai_params # RSI, 손절가, 김프 등 AI값 사용
    
    # [Case B] AI 호출 실패/오류 시 -> 보수적인 기본값(Fallback) 사용
    else:
        print(f"⚠️ [Strategy] AI 분석 실패 -> 안전 모드(Fallback) 가동")
        final_params = {
            'RSI_BUY_THRESHOLD': 30,
            'MAX_KIMP_THRESHOLD': 5.0,
            'STOP_LOSS_PCT': -1.5,
            'MAX_TICKS_FOR_BEP': 13,
            'PARTIAL_SELL_MIN_PROFIT': 0.5,
            'TRAILING_START': 0.5,
            'REASON': 'AI Connection Failed'
        }

    # 3. 공통 데이터 병합 (타겟 코인 등)
    final_params['TARGET_COINS'] = tech_targets
    final_params['FOLLOWER_COINS'] = list(tech_targets.keys())[:5]
    final_params['BB_MULTIPLIER'] = 2.0
    
    return final_params

if __name__ == "__main__":
    print(get_strategy_recommendation())