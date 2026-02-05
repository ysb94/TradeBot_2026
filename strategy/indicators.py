# indicators.py
# RSI, 볼린저 밴드, VWAP를 계산

import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    def __init__(self):
        pass

    def calculate_rsi(self, df, period=14):
        """RSI(상대강도지수) 계산"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """볼린저 밴드 계산 (상단, 중단, 하단)"""
        sma = df['close'].rolling(window=period).mean() # 중단 (이동평균)
        std = df['close'].rolling(window=period).std()  # 표준편차

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band

    def calculate_vwap(self, df):
        """VWAP (거래량 가중 평균 가격) 계산"""
        # (가격 * 거래량)의 누적 합 / 거래량의 누적 합
        v = df['volume'].values
        tp = (df['high'] + df['low'] + df['close']) / 3
        return (tp * v).cumsum() / v.cumsum()

    def analyze_1m_candle(self, ohlcv_data):
        """
        1분봉 데이터(DataFrame)를 받아 지표를 계산하고 현재 상태 리턴
        ohlcv_data: pyupbit.get_ohlcv() 결과값
        """
        df = ohlcv_data.copy()
        
        # 지표 추가
        df['RSI_14'] = self.calculate_rsi(df, 14)
        df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = self.calculate_bollinger_bands(df, 20, 2)
        
        # 최신 데이터(마지막 줄) 추출
        latest = df.iloc[-1]
        
        return {
            "current_price": latest['close'],
            "RSI": round(latest['RSI_14'], 2),
            "BB_Upper": round(latest['BB_Upper'], 2),
            "BB_Lower": round(latest['BB_Lower'], 2),
            "is_oversold": latest['close'] <= latest['BB_Lower'], # 볼밴 하단 터치 여부
            "is_rsi_low": latest['RSI_14'] < 30 # RSI 과매도 여부
        }