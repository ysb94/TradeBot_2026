# signal_maker.py
# 실질적인 **'판단'**을 내리는 곳입니다. 업비트 차트 데이터를 가져와서 우리의 전략(RSI + 볼밴 + 김프)에 맞는지 검사

import pyupbit
from strategy.indicators import TechnicalAnalyzer
from strategy.calculator import TickCalculator # [추가] 계산기 임포트
from config import RSI_BUY_THRESHOLD, MAX_KIMP_THRESHOLD, MAX_TICKS_FOR_BEP # [추가] 설정값 임포트

class SignalMaker:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.calculator = TickCalculator() # [추가] 계산기 초기화

    def check_buy_signal(self, ticker, current_price, current_kimp):
        """
        매수 신호 점검 (하이브리드 전략 + 틱 가치 필터)
        """
        # 1. 김프 필터
        if current_kimp > MAX_KIMP_THRESHOLD:
            return False, f"김프 과열({current_kimp:.2f}%)"

        # 2. [기능 구현 1번] 동적 틱 가치 분석 (손익분기점 체크)
        ticks_to_bep, _ = self.calculator.get_ticks_to_bep(current_price)
        
        # 수수료 떼고 본전 찾는데 너무 많은 틱이 필요하면 진입 금지
        if ticks_to_bep > MAX_TICKS_FOR_BEP:
            return False, f"틱 효율 나쁨(본전까지 {ticks_to_bep}틱 필요)"

        # 3. 데이터 수집
        try:
            df = pyupbit.get_ohlcv(ticker, interval="minute1", count=50)
            if df is None: return False, "데이터 없음"
        except: return False, "API 오류"

        # 4. 지표 분석
        analysis = self.analyzer.analyze_1m_candle(df)
        rsi = analysis['RSI']
        is_bb_touch = analysis['is_oversold']

        # 5. 매수 조건 확인 (RSI + 볼린저밴드)
        if rsi < RSI_BUY_THRESHOLD and is_bb_touch:
            return True, f"매수조건 만족 (RSI:{rsi:.1f}, BB터치, BEP:{ticks_to_bep}틱)"
        
        return False, f"관망 (RSI:{rsi:.1f}, 필요틱:{ticks_to_bep})"