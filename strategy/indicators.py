# strategy/indicators.py
# [업데이트] RSI(9) 및 VWAP 계산 기능 추가

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
        sma = df['close'].rolling(window=period).mean() # 중단
        std = df['close'].rolling(window=period).std()  # 표준편차

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band

    def calculate_vwap(self, df):
        """VWAP (거래량 가중 평균 가격) 계산"""
        v = df['volume']
        tp = (df['high'] + df['low'] + df['close']) / 3
        # 누적 합 계산
        return (tp * v).cumsum() / v.cumsum()

    def analyze_1m_candle(self, ohlcv_data):
        """
        1분봉 데이터를 받아 RSI(9), RSI(14), 볼린저밴드, VWAP 상태 리턴
        """
        df = ohlcv_data.copy()
        
        # 1. 지표 계산
        df['RSI_14'] = self.calculate_rsi(df, 14) # 장기 추세
        df['RSI_9'] = self.calculate_rsi(df, 9)   # 단기 민감도 (골든크로스용)
        df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = self.calculate_bollinger_bands(df, 20, 2)
        df['VWAP'] = self.calculate_vwap(df)      # 세력 평단가 (눌림목용)
        
        # 2. 최신 데이터 추출
        latest = df.iloc[-1]
        
        # 3. 결과 포장
        return {
            "current_price": latest['close'],
            "RSI_14": round(latest['RSI_14'], 2),
            "RSI_9": round(latest['RSI_9'], 2),
            "BB_Lower": round(latest['BB_Lower'], 2),
            "VWAP": round(latest['VWAP'], 2),
            "is_oversold": latest['close'] <= latest['BB_Lower'], # 볼밴 하단 터치
            "is_rsi_low": latest['RSI_14'] < 30
        }