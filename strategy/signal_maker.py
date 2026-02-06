# strategy/signal_maker.py
# [최종] RSI 골든크로스 + VWAP 지지 + 역프 스나이퍼 전략

import pyupbit
from strategy.indicators import TechnicalAnalyzer
from strategy.calculator import TickCalculator
from config import RSI_BUY_THRESHOLD, MAX_KIMP_THRESHOLD, MAX_TICKS_FOR_BEP, REVERSE_KIMP_THRESHOLD

class SignalMaker:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.calculator = TickCalculator()

    def check_buy_signal(self, ticker, current_price, current_kimp):
        """
        매수 신호 점검 (RSI 골든크로스 + 볼밴 + VWAP + 김프)
        """
        # 1. 김프 필터
        if current_kimp > MAX_KIMP_THRESHOLD:
            return False, f"김프 과열({current_kimp:.2f}%)"

        # 2. 틱 효율성(BEP) 체크
        ticks_to_bep, _ = self.calculator.get_ticks_to_bep(current_price)
        if ticks_to_bep > MAX_TICKS_FOR_BEP:
            return False, f"틱 효율 나쁨(본전까지 {ticks_to_bep}틱 필요)"

        # 3. 데이터 수집 (VWAP 정확도를 위해 200개 조회)
        try:
            df = pyupbit.get_ohlcv(ticker, interval="minute1", count=200)
            if df is None: return False, "데이터 없음"
        except: return False, "API 오류"

        # 4. 지표 분석
        analysis = self.analyzer.analyze_1m_candle(df)
        rsi_14 = analysis['RSI_14']
        rsi_9 = analysis['RSI_9']
        is_bb_touch = analysis['is_oversold']
        vwap = analysis['VWAP']

        # =========================================================
        # 🔥 [3순위] 역프리미엄 스나이퍼
        # =========================================================
        if current_kimp <= REVERSE_KIMP_THRESHOLD:
            # 역프 상태면 RSI 기준을 +10만큼 완화
            if rsi_14 < (RSI_BUY_THRESHOLD + 10):
                return True, f"🔥 역프 스나이퍼 (김프:{current_kimp:.2f}%, RSI:{rsi_14})"

        # =========================================================
        # 🎯 [핵심] 정밀 매수 전략 (보고서 기반)
        # 1. RSI(14) 과매도권 (기본 조건)
        # 2. 볼린저 밴드 하단 터치 (과매도 확인)
        # 3. RSI(9) > RSI(14) (골든크로스: 반등 시작)
        # 4. VWAP 지지 (현재가가 VWAP보다 너무 낮지 않아야 함 - 하락세 진정 확인)
        # =========================================================
        
        is_rsi_golden_cross = rsi_9 > rsi_14
        
        # VWAP 대비 이격도가 -1.0% 이내인지 확인 (너무 싼 건 떨어지는 칼날일 수 있음)
        # 단, 급락 후 반등 시점에는 VWAP보다 한참 아래일 수 있으므로 보조 조건으로만 활용
        # 여기서는 '골든크로스'를 최우선으로 봅니다.
        
        if rsi_14 < RSI_BUY_THRESHOLD and is_bb_touch:
            if is_rsi_golden_cross:
                return True, f"⚡ 골든크로스 진입! (RSI9:{rsi_9} > RSI14:{rsi_14})"
            else:
                return False, f"반등 대기중 (RSI9:{rsi_9} < RSI14:{rsi_14})"
        
        return False, f"관망 (RSI14:{rsi_14}, RSI9:{rsi_9})"