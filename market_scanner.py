import time
import requests
import pyupbit
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# [설정] 분석 대상 및 API 주소
# ---------------------------------------------------------
# 환율 정보 (무료 API)
EXCHANGE_RATE_API = "https://api.exchangerate-api.com/v4/latest/USD"
# 공포/탐욕 지수 (무료 API)
FEAR_GREED_API = "https://api.alternative.me/fng/"
# 분석할 코인 개수 (거래대금 상위 N개)
TOP_COIN_COUNT = 10 

def get_exchange_rate():
    """실시간 원/달러 환율 조회"""
    try:
        resp = requests.get(EXCHANGE_RATE_API, timeout=5).json()
        return float(resp['rates']['KRW'])
    except Exception as e:
        print(f"⚠️ 환율 조회 실패 (기본값 1450원 사용): {e}")
        return 1450.0

def get_fear_and_greed():
    """공포/탐욕 지수 조회"""
    try:
        resp = requests.get(FEAR_GREED_API, timeout=5).json()
        data = resp['data'][0]
        return int(data['value']), data['value_classification']
    except:
        return 50, "Neutral"

def analyze_market_conditions():
    print(f"\n🔍 [시장 정밀 진단 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)

    # 1. 기초 데이터 수집
    usd_krw = get_exchange_rate()
    fng_value, fng_label = get_fear_and_greed()
    
    print(f"💵 실시간 환율: {usd_krw:.2f} 원/$")
    print(f"😨 공포/탐욕 지수: {fng_value} ({fng_label})")

    # 2. 업비트 전 종목 스캔 (거래대금 상위 추출)
    print("⏳ 업비트 상장 코인 스캔 중...")
    tickers = pyupbit.get_tickers(fiat="KRW")
    
    # API 요청 제한을 피하기 위해 100개씩 나누어 조회하거나, 전체 Ticker 조회 (업비트 API는 빠름)
    # 한 번에 요청 (url 길이 제한 주의, 나눠서 요청)
    url = "https://api.upbit.com/v1/ticker"
    markets = ",".join(tickers)
    
    # 너무 길면 에러나므로 30개씩 분할 요청
    chunk_size = 30
    ticker_data = []
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        params = {"markets": ",".join(chunk)}
        try:
            res = requests.get(url, params=params).json()
            ticker_data.extend(res)
            time.sleep(0.1)
        except:
            pass

    # DataFrame 변환 및 정렬
    df = pd.DataFrame(ticker_data)
    df['acc_trade_price_24h'] = df['acc_trade_price_24h'].astype(float)
    df = df.sort_values(by='acc_trade_price_24h', ascending=False)
    
    # 거래대금 상위 코인 추출
    top_coins = df.head(TOP_COIN_COUNT)[['market', 'trade_price', 'acc_trade_price_24h', 'signed_change_rate']]
    
    print(f"\n🏆 [오늘의 주도주 TOP {TOP_COIN_COUNT}]")
    target_coins_map = {}
    
    # 바이낸스 심볼 매핑용 (간이 로직: KRW-BTC -> btcusdt)
    for idx, row in top_coins.iterrows():
        ticker = row['market']
        symbol = ticker.split('-')[1].lower() + "usdt"
        
        # 제외할 코인 (스테이블 코인 등)
        if symbol in ['usdtusdt']: continue
            
        print(f"   {idx+1}. {ticker:<9} | 등락률: {row['signed_change_rate']*100:>6.2f}% | 거래대금: {row['acc_trade_price_24h']/100000000:,.0f}억")
        target_coins_map[ticker] = symbol

    # 3. 김치 프리미엄 계산 (대장주 BTC 기준)
    print("\n🍔 [김치 프리미엄 분석]")
    
    upbit_btc = float(df[df['market']=='KRW-BTC']['trade_price'].iloc[0])
    
    try:
        binance_res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5).json()
        binance_btc = float(binance_res['price'])
        
        # 김프 계산
        global_krw = binance_btc * usd_krw
        kimp_pct = ((upbit_btc - global_krw) / global_krw) * 100
        
        print(f"   - 업비트 BTC: {upbit_btc:,.0f} 원")
        print(f"   - 바이낸스 BTC: ${binance_btc:,.2f} (환산: {global_krw:,.0f} 원)")
        print(f"   - 현재 김프: {kimp_pct:+.2f}%")
        
    except Exception as e:
        print(f"⚠️ 바이낸스 조회 실패: {e}")
        kimp_pct = 0.0

    # ---------------------------------------------------------
    # 🤖 추천 설정값 생성 로직
    # ---------------------------------------------------------
    rec_rsi = 30
    rec_bb_mult = 2.0
    rec_kimp_max = 5.0
    rec_reverse_kimp = -1.0
    
    # 1. 공포지수에 따른 RSI 조정
    if fng_value <= 20: # 극단적 공포
        rec_rsi = 25 # 더 보수적으로 (더 떨어져야 산다)
        rec_bb_mult = 2.2 # 밴드폭 넓힘
        market_mood = "🥶 극단적 공포 (보수적 진입 추천)"
    elif fng_value >= 75: # 극단적 탐욕
        rec_rsi = 40 # 기회를 놓치지 않게 완화
        market_mood = "🔥 극단적 탐욕 (공격적 진입 가능)"
    else:
        market_mood = "😐 중립/일반장"

    # 2. 김프에 따른 필터 조정
    if kimp_pct < 0: # 역프 상태
        rec_reverse_kimp = kimp_pct - 0.5 # 현재 역프보다 조금 더 아래
        rec_kimp_max = 3.0 # 김프가 다시 끼기 시작하면 3%만 되도 튄다
        kimp_status = "📉 역프리미엄 (줍줍 찬스!)"
    elif kimp_pct > 5.0: # 고김프
        rec_kimp_max = kimp_pct + 2.0 # 현재보다 2% 더 여유
        kimp_status = "🚨 고김프 주의 (추격 매수 조심)"
    else:
        rec_kimp_max = 5.0
        kimp_status = "✅ 안정적"

    # ---------------------------------------------------------
    # 📝 config.py 코드 생성
    # ---------------------------------------------------------
    print("\n" + "="*50)
    print("      📋 config.py 추천 설정값 (복사해서 사용)")
    print("="*50)
    
    config_code = f"""
# [1. 자동 생성된 설정 - {datetime.now().strftime('%Y-%m-%d')}]
# 시장 분위기: {market_mood}
# 김프 상태: {kimp_status} ({kimp_pct:+.2f}%)

CURRENT_EXCHANGE_RATE = {usd_krw} 

# [주도주 TOP {len(target_coins_map)} 자동 반영]
TARGET_COINS = {str(target_coins_map)}

# [전략 설정]
RSI_BUY_THRESHOLD = {rec_rsi}      # 공포지수 {fng_value} 반영
BB_MULTIPLIER = {rec_bb_mult}         

# [리스크 관리]
MAX_KIMP_THRESHOLD = {rec_kimp_max:.1f}   
REVERSE_KIMP_THRESHOLD = {rec_reverse_kimp:.1f} 

# [추천 팔로워 코인 (거래대금 최상위 제외한 2~5위)]
FOLLOWER_COINS = {list(target_coins_map.keys())[1:5]}
"""
    print(config_code)
    print("="*50)

if __name__ == "__main__":
    analyze_market_conditions()