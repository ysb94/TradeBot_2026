# order_manager.py
# 실제 주문을 담당하는 모듈입니다. IS_SIMULATION 값에 따라 진짜 주문을 넣을지, 흉내만 낼지 결정

import pyupbit
from config import UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, IS_SIMULATION

class OrderManager:
    def __init__(self):
        self.is_simulation = IS_SIMULATION
        self.upbit = None
        
        if not self.is_simulation:
            # 실전 모드일 때만 업비트 객체 생성
            self.upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            print("💳 [OrderManager] 실전 매매 모드 가동 (업비트 연결됨)")
        else:
            print("🧪 [OrderManager] 모의 투자 모드 가동 (가상 매매)")

    def get_balance(self, ticker="KRW"):
        """보유 현금(KRW) 또는 코인 잔고 조회"""
        if self.is_simulation:
            return 100_000_000 # 모의투자 시 1억 원 있다고 가정
        
        try:
            balance = self.upbit.get_balance(ticker)
            return balance if balance else 0
        except Exception as e:
            print(f"⚠️ 잔고 조회 실패: {e}")
            return 0

    def buy_market_order(self, ticker, price_krw):
        """시장가 매수"""
        if self.is_simulation:
            print(f"\n✨ [모의 매수 체결] {ticker} | 금액: {price_krw:,.0f}원")
            return {"uuid": "fake-uuid-1234", "state": "done"} # 가짜 주문 결과 반환

        try:
            # 최소 주문 금액 체크 (업비트 5,000원)
            if price_krw < 5000:
                print("❌ 주문 금액이 너무 적습니다 (최소 5,000원)")
                return None
            
            # 실제 주문 전송
            result = self.upbit.buy_market_order(ticker, price_krw)
            print(f"\n⚡ [실전 매수 체결] {ticker} | 결과: {result}")
            return result
            
        except Exception as e:
            print(f"❌ 매수 주문 실패: {e}")
            return None