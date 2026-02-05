# signal_maker.py
# 실질적인 **'판단'**을 내리는 곳입니다. 업비트 차트 데이터를 가져와서 우리의 전략(RSI + 볼밴 + 김프)에 맞는지 검사



import pyupbit
from strategy.indicators import TechnicalAnalyzer
from config import RSI_BUY_THRESHOLD, MAX_KIMP_THRESHOLD

class SignalMaker:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()

    def check_buy_signal(self, ticker, current_price, current_kimp):
        """
        매수 신호 점검 (보고서 기반 하이브리드 전략)
        True: 매수 진행 / False: 관망
        """
        # 1. 김프 필터 (안전장치)
        if current_kimp > MAX_KIMP_THRESHOLD:
            return False, f"김프 과열({current_kimp:.2f}%)"

        # 2. 차트 데이터 가져오기 (1분봉)
        # (실전에서는 API 호출 제한을 고려해야 함)
        df = pyupbit.get_ohlcv(ticker, interval="minute1", count=50)
        
        if df is None:
            return False, "데이터 수신 실패"

        # 3. 지표 분석
        analysis = self.analyzer.analyze_1m_candle(df)
        
        rsi = analysis['RSI']
        is_bb_touch = analysis['is_oversold']

        # 4. 하이브리드 진입 조건 (RSI + 볼린저밴드 AND 조건)
        # 조건: RSI가 30 미만이면서 동시에 볼밴 하단을 터치해야 함
        if rsi < RSI_BUY_THRESHOLD and is_bb_touch:
            reason = f"매수 포착! (RSI: {rsi} + BB하단 터치)"
            return True, reason
        
        # 매수 실패 사유 리턴 (모니터링용)
        fail_reason = []
        if rsi >= RSI_BUY_THRESHOLD: fail_reason.append(f"RSI높음({rsi})")
        if not is_bb_touch: fail_reason.append("BB미도달")
        
        return False, " / ".join(fail_reason)