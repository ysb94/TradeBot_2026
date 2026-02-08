# market_scanner.py
# [V2 Upgrade] 시장 온도(Regime) 기반 동적 스캐닝 & 파라미터 튜닝

import pyupbit
import time
import requests
import numpy as np
import pandas as pd
from strategy.indicators import TechnicalAnalyzer
import config

class MarketScanner:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.market_status = "NEUTRAL" # 초기 상태

    def get_all_krw_tickers(self):
        try:
            return pyupbit.get_tickers(fiat="KRW")
        except:
            return []

    def get_top_volume_coins(self, limit=30):
        """유동성 상위 N개 코인 조회"""
        try:
            tickers = self.get_all_krw_tickers()
            if not tickers: return []

            # 업비트 Ticker API로 거래대금 조회
            url = "https://api.upbit.com/v1/ticker"
            params = {"markets": ",".join(tickers)}
            resp = requests.get(url, params=params).json()
            
            # 24시간 누적 거래대금(acc_trade_price_24h) 기준 내림차순 정렬
            sorted_data = sorted(resp, key=lambda x: x['acc_trade_price_24h'], reverse=True)
            return [item['market'] for item in sorted_data[:limit]]
        except Exception as e:
            print(f"⚠️ [Scanner] 유동성 분석 실패: {e}")
            return []

    def analyze_market_regime(self):
        """
        [핵심] 시장의 온도를 측정하여 장세를 판단함
        Return: "BULL"(불장), "BEAR"(하락장), "NEUTRAL"(횡보)
        """
        try:
            # 대장주(BTC) + 거래상위 5개 종목의 추세 확인
            leaders = ["KRW-BTC"] + self.get_top_volume_coins(limit=5)
            rsi_sum = 0
            count = 0

            print("\n🌡️ [Scanner] 시장 온도 측정 중...")
            for ticker in leaders:
                time.sleep(0.05)
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=24) # 1시간봉 기준
                if df is None: continue
                
                # indicators.py의 analyzer 사용
                rsi = self.analyzer.calculate_rsi(df).iloc[-1]
                rsi_sum += rsi
                count += 1

            # 평균 RSI 계산
            avg_rsi = rsi_sum / count if count > 0 else 50
            
            # 장세 판단 로직
            if avg_rsi >= 58:
                self.market_status = "BULL"
                print(f"🔥 시장 상태: [강세장] (Avg RSI: {avg_rsi:.1f}) -> 공격적 모드 가동")
            elif avg_rsi <= 38:
                self.market_status = "BEAR"
                print(f"❄️ 시장 상태: [약세장] (Avg RSI: {avg_rsi:.1f}) -> 방어적 모드 가동")
            else:
                self.market_status = "NEUTRAL"
                print(f"⚖️ 시장 상태: [횡보장] (Avg RSI: {avg_rsi:.1f}) -> 균형 모드 가동")

            return self.market_status, avg_rsi

        except Exception as e:
            print(f"⚠️ 시장 분석 실패: {e}")
            return "NEUTRAL", 50

    def scan_market(self):
        """장세에 따라 유연하게 종목을 발굴"""
        # 1. 시장 온도 측정
        regime, avg_rsi = self.analyze_market_regime()
        
        # 2. 장세별 스캔 조건 설정 (동적 변화)
        if regime == "BULL":
            # 불장: 물 들어올 때 노 젓자
            scan_limit = 50       # 더 많은 종목을 탐색
            target_count = 10     # 타겟을 많이 가져감 (분산 투자)
            rsi_criteria = 55     # RSI가 55 이하여도 눌림목으로 간주 (공격적)
            
        elif regime == "BEAR":
            # 하락장: 소나기는 피하자
            scan_limit = 20       # 거래량 터진 확실한 놈만 봄
            target_count = 3      # 소수 정예 (집중 투자)
            rsi_criteria = 25     # 정말 싼 거 아니면 쳐다도 안 봄 (방어적)
            
        else: # NEUTRAL
            # 횡보장: 기본값
            scan_limit = 30
            target_count = 5
            rsi_criteria = 35

        # 3. 스캔 시작
        candidates = self.get_top_volume_coins(limit=scan_limit)
        selected_coins = {}

        print(f"🔍 [Scanner] 조건 적용: 상위 {scan_limit}개 중 RSI {rsi_criteria} 이하 발굴")

        for ticker in candidates:
            try:
                # 대장주는 무조건 포함 (시장 지표용)
                if ticker in ["KRW-BTC", "KRW-ETH", "KRW-XRP"]:
                    symbol = ticker.replace("KRW-", "").lower() + "usdt"
                    selected_coins[ticker] = symbol
                    continue

                time.sleep(0.1)
                df = pyupbit.get_ohlcv(ticker, interval="minute15", count=60) # 15분봉 기준
                if df is None: continue

                analysis = self.analyzer.analyze_1m_candle(df)
                current_rsi = analysis['RSI_14']
                bb_lower = analysis['BB_Lower']
                current_price = analysis['current_price']

                # 🔥 동적 조건 적용
                # 1) 설정된 동적 RSI 기준보다 낮거나
                # 2) 볼밴 하단을 뚫고 내려갔거나 (과매도)
                if current_rsi <= rsi_criteria or current_price <= bb_lower:
                    symbol = ticker.replace("KRW-", "").lower() + "usdt"
                    selected_coins[ticker] = symbol
                    print(f"   👉 발굴: {ticker} (RSI: {current_rsi:.1f})")

                if len(selected_coins) >= target_count:
                    break

            except: continue

        # 최소 수량 보정 (너무 없으면 대장주라도 넣음)
        if len(selected_coins) < 2:
            defaults = {"KRW-BTC": "btcusdt", "KRW-ETH": "ethusdt"}
            selected_coins.update(defaults)

        return selected_coins, regime

# ==========================================================
# main.py에서 호출하는 함수
# ==========================================================
def get_strategy_recommendation():
    """
    AI Auto Pilot이 호출하는 메인 함수
    """
    scanner = MarketScanner()
    new_targets, regime = scanner.scan_market()
    
    # 장세에 따른 config 파라미터 자동 튜닝
    # (시장 상황에 맞춰 봇의 성격을 바꿈)
    
    if regime == "BULL":
        # 불장: RSI 기준을 높여서 적극적으로 삼
        rec_rsi_threshold = 50 
        rec_kimp_max = 7.0 # 김프 좀 껴도 봐줌
        
    elif regime == "BEAR":
        # 하락장: RSI 기준을 낮춰서 바닥만 잡음
        rec_rsi_threshold = 22 
        rec_kimp_max = 3.0 # 김프 끼면 칼같이 거름
        
    else:
        # 횡보장: 기본값
        rec_rsi_threshold = 28
        rec_kimp_max = 5.0

    return {
        'TARGET_COINS': new_targets,
        'FOLLOWER_COINS': list(new_targets.keys())[:5],
        'RSI_BUY_THRESHOLD': rec_rsi_threshold,  # 🔥 핵심: 동적 변경
        'MAX_KIMP_THRESHOLD': rec_kimp_max,      # 🔥 핵심: 동적 변경
        'BB_MULTIPLIER': 2.0,
        'REVERSE_KIMP_THRESHOLD': -0.5,
        'CURRENT_EXCHANGE_RATE': 1465.0
    }

if __name__ == "__main__":
    # 테스트 실행
    print(get_strategy_recommendation())