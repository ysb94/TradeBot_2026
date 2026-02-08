# strategy/signal_maker.py
# [업데이트] main.py에서 보유 코인 분석을 위해 호출할 함수 추가

import pyupbit
from strategy.indicators import TechnicalAnalyzer
from strategy.calculator import TickCalculator
import config

class SignalMaker:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.calculator = TickCalculator()

    def get_analysis_only(self, ticker):
        """
        [신규] 매수 여부와 상관없이, 현재 코인의 지표 상태(RSI, VWAP, BB)를 리턴
        (보유 중인 코인의 매도 판단용)
        """
        try:
            df = pyupbit.get_ohlcv(ticker, interval=config.OHLCV_INTERVAL, count=config.OHLCV_COUNT)
            if df is None: return None
            
            # 지표 계산
            analysis = self.analyzer.analyze_1m_candle(df)
            return analysis
        except:
            return None

    # 기존 import 구문 유지...

    def check_buy_signal(self, ticker, current_price, current_kimp):
        """
        [수정] 리턴값 변경: (bool, str) -> (bool, str, dict)
        마지막에 analysis 딕셔너리를 함께 반환합니다.
        """
        # 1. 김프 필터
        if current_kimp > config.MAX_KIMP_THRESHOLD:
            return False, f"김프 과열({current_kimp:.2f}%)", None # None 추가

        # 2. 틱 효율성(BEP) 체크
        ticks_to_bep, _ = self.calculator.get_ticks_to_bep(current_price)
        if ticks_to_bep > config.MAX_TICKS_FOR_BEP:
            return False, f"틱 효율 나쁨(본전까지 {ticks_to_bep}틱 필요)", None # None 추가

        # 3. 데이터 수집
        try:
            df = pyupbit.get_ohlcv(ticker, interval=config.OHLCV_INTERVAL, count=config.OHLCV_COUNT)
            if df is None: return False, "데이터 없음", None # None 추가
        except: return False, "API 오류", None # None 추가

        # 4. 지표 분석
        analysis = self.analyzer.analyze_1m_candle(df)
        rsi_14 = analysis['RSI_14']
        rsi_9 = analysis['RSI_9']
        is_bb_touch = analysis['is_oversold']
        vwap = analysis['VWAP']

        # [3순위] 역프리미엄 스나이퍼
        if current_kimp <= config.REVERSE_KIMP_THRESHOLD:
            if rsi_14 < (config.RSI_BUY_THRESHOLD + config.RSI_REVERSE_OFFSET):
                # [수정] analysis 함께 리턴
                return True, f"🔥 역프 스나이퍼 (김프:{current_kimp:.2f}%, RSI:{rsi_14})", analysis

        # 🎯 [핵심] 정밀 매수 전략
        is_rsi_golden_cross = rsi_9 > rsi_14
        is_vwap_support = current_price >= (vwap * config.VWAP_BUY_FACTOR)

        if rsi_14 < config.RSI_BUY_THRESHOLD and is_bb_touch:
            if is_rsi_golden_cross:
                if is_vwap_support:
                    # [수정] analysis 함께 리턴
                    return True, f"⚡ 골든크로스+VWAP지지 (RSI9:{rsi_9}>14:{rsi_14})", analysis
                else:
                    return False, f"VWAP 저항 (현재가 < VWAP)", analysis
            else:
                return False, f"반등 대기중 (RSI9:{rsi_9} < RSI14:{rsi_14})", analysis
        
        return False, f"관망 (RSI:{rsi_14})", analysis