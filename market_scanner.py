# market_scanner.py
# [최종] 전 종목 스캔(Funnel Filtering) + 유동성 필터 + 지표 기반 타겟 발굴

import pyupbit
import time
import requests
from strategy.indicators import TechnicalAnalyzer
import config

def get_all_krw_tickers():
    """업비트 원화 마켓 전 종목 조회"""
    try:
        return pyupbit.get_tickers(fiat="KRW")
    except:
        return []

def get_top_volume_coins(limit=30):
    """
    1차 필터: 유동성 공급이 원활한 상위 N개 종목 추출
    (전 종목의 24시간 거래대금을 조회하여 정렬)
    """
    try:
        tickers = get_all_krw_tickers()
        if not tickers: return []

        # 업비트 Ticker API는 한 번에 여러 개 조회가 가능하므로 콤마로 묶어서 요청
        # URL 길이가 너무 길면 잘릴 수 있으나, 100개 미만은 대체로 안전
        url = "https://api.upbit.com/v1/ticker"
        params = {"markets": ",".join(tickers)}
        
        resp = requests.get(url, params=params)
        data = resp.json()
        
        # 24시간 누적 거래대금(acc_trade_price_24h) 기준 내림차순 정렬
        sorted_data = sorted(data, key=lambda x: x['acc_trade_price_24h'], reverse=True)
        
        # 상위 N개의 마켓 코드만 리턴
        top_coins = [item['market'] for item in sorted_data[:limit]]
        return top_coins

    except Exception as e:
        print(f"⚠️ [Scanner] 유동성 분석 실패: {e}")
        return []

def scan_market():
    """
    2차 필터: 기술적 분석 (RSI + 볼린저 밴드)
    Return: 조건에 맞는 유망 종목 리스트 (딕셔너리 형태)
    """
    analyzer = TechnicalAnalyzer()
    
    # 1. 유동성 좋은 종목 선정 (40개 조회)
    candidates = get_top_volume_coins(limit=40) 
    if not candidates: 
        return config.TARGET_COINS # 실패 시 기존 타겟 유지

    print(f"\n🔍 [Scanner] 시장 스캔 시작 (대상: {len(candidates)}개 종목)")
    
    selected_coins = {}
    
    # 2. 각 종목별 정밀 지표 분석
    for ticker in candidates:
        try:
            # BTC, ETH, XRP는 시장 지표이므로 무조건 포함 (Safety Fallback)
            if ticker in ["KRW-BTC", "KRW-ETH", "KRW-XRP"]:
                symbol = ticker.replace("KRW-", "").lower() + "usdt"
                selected_coins[ticker] = symbol
                continue

            # API 호출 속도 조절
            time.sleep(0.1) 
            
            # 스캔은 15분봉 기준 (중기 추세 파악)
            df = pyupbit.get_ohlcv(ticker, interval="minute15", count=60) 
            if df is None: continue

            # 지표 계산
            analysis = analyzer.analyze_1m_candle(df) # 15분봉 데이터를 넣어도 계산식은 동일
            
            rsi = analysis['RSI_14']
            bb_lower = analysis['BB_Lower']
            current_price = analysis['current_price']
            
            # 🔥 [조건] RSI가 낮거나(과매도) or 볼린저밴드 하단 근처
            if rsi <= 40 or current_price <= bb_lower * 1.01:
                # 바이낸스 심볼 추정 (KRW-DOGE -> dogeusdt)
                symbol = ticker.replace("KRW-", "").lower() + "usdt"
                selected_coins[ticker] = symbol
                print(f"   👉 발견: {ticker} (RSI: {rsi:.1f}, BB하단접근)")
                
                # 타겟 개수가 너무 많아지면 중단 (최대 10개)
                if len(selected_coins) >= 10:
                    break

        except Exception as e:
            continue

    # 3. 최소한의 타겟 확보 실패 시 기본 타겟 사용
    if len(selected_coins) < 3:
        print("   ⚠️ 조건 만족 종목 부족 -> 우량주 위주로 채움")
        defaults = {"KRW-BTC": "btcusdt", "KRW-ETH": "ethusdt", "KRW-XRP": "xrpusdt"}
        selected_coins.update(defaults)

    return selected_coins

def get_strategy_recommendation():
    """
    AI Auto Pilot이 호출하는 메인 함수
    """
    # 1. 시장 스캔 수행
    new_targets = scan_market()
    
    # 2. 결과 반환 (여기서 매수 설정값도 시장 상황에 따라 조정 가능)
    return {
        'TARGET_COINS': new_targets,
        'FOLLOWER_COINS': list(new_targets.keys())[:5], # 상위 5개를 추격 매수 대상으로
        'RSI_BUY_THRESHOLD': 28,  
        'BB_MULTIPLIER': 2.0,
        'MAX_KIMP_THRESHOLD': 3.5,
        'REVERSE_KIMP_THRESHOLD': -0.5,
        'CURRENT_EXCHANGE_RATE': 1465.0 
    }

if __name__ == "__main__":
    print(scan_market())