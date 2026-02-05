# test_strategy.py
# 전략 모듈 테스트 (placeholder)

import pyupbit
from strategy.calculator import TickCalculator
from strategy.indicators import TechnicalAnalyzer

# 1. 틱 가치 계산기 테스트
calc = TickCalculator()
current_price = 104373000 # 비트코인 예시 가격
bep_price = calc.calculate_bep(current_price)
ticks, _ = calc.get_ticks_to_bep(current_price)

print(f"=== 💰 계산기 테스트 ===")
print(f"현재가: {current_price:,.0f} KRW")
print(f"손익분기점(BEP): {bep_price:,.0f} KRW (수수료 포함)")
print(f"최소 상승 틱: {ticks} 틱")
print("-" * 30)

# 2. 지표 분석기 테스트
analyzer = TechnicalAnalyzer()
print(f"=== 📊 지표 분석 테스트 ===")
# 비트코인 1분봉 200개 가져오기
df = pyupbit.get_ohlcv("KRW-BTC", interval="minute1", count=200)

if df is not None:
    result = analyzer.analyze_1m_candle(df)
    print(f"현재 RSI: {result['RSI']}")
    print(f"볼밴 하단: {result['BB_Lower']:,.0f}")
    print(f"과매도 상태(볼밴터치): {result['is_oversold']}")
    print(f"RSI 저점(30이하): {result['is_rsi_low']}")
else:
    print("업비트 데이터 호출 실패")