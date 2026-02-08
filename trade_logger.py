import csv
import os
from datetime import datetime

class TradeLogger:
    def __init__(self, filename="trade_history.csv"):
        self.filename = filename
        self.columns = [
            "Timestamp", "Ticker", "Action", "Price", 
            "RSI", "VWAP", "Profit_Rate", "Reason"
        ]
        self._initialize_csv()

    def _initialize_csv(self):
        """파일이 없으면 헤더(제목)를 생성"""
        if not os.path.exists(self.filename):
            with open(self.filename, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(self.columns)

    def log(self, ticker, action, price, analysis=None, profit_rate=0.0, reason=""):
        """
        매매 기록 저장
        :param analysis: signal_maker에서 받은 지표 딕셔너리 (RSI, VWAP 등 포함)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 지표 데이터가 없는 경우(API 에러 등) 대비
        rsi = analysis['RSI_14'] if analysis else 0
        vwap = analysis['VWAP'] if analysis else 0

        row = [
            now, 
            ticker, 
            action, 
            f"{price:,.0f}", 
            f"{rsi:.1f}", 
            f"{vwap:,.0f}", 
            f"{profit_rate:.2f}%" if profit_rate else "", 
            reason
        ]

        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(row)
            print(f"📝 [Logger] 기록 저장 완료: {action} {ticker}")
        except Exception as e:
            print(f"⚠️ [Logger] 저장 실패: {e}")