# order_manager.py
# 실제 주문을 담당하는 모듈입니다. IS_SIMULATION 값에 따라 진짜 주문을 넣을지, 흉내만 낼지 결정

import pyupbit
from config import UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, IS_SIMULATION

class OrderManager:
    def __init__(self):
        self.is_simulation = IS_SIMULATION
        self.upbit = None
        
        # [모의투자용] 가상 지갑 (Ticker: {vol: 수량, avg: 평단가})
        self.sim_holdings = {} 
        self.sim_krw = 10_000_000 # 가상 현금 1천만원
        
        if not self.is_simulation:
            self.upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            print("💳 [OrderManager] 실전 매매 모드 (업비트 연결됨)")
        else:
            print("🧪 [OrderManager] 모의 투자 모드 (가상 지갑 가동)")

    def get_balance(self, ticker="KRW"):
        """잔고 조회 (실전/모의 통합)"""
        if self.is_simulation:
            if ticker == "KRW":
                return self.sim_krw
            # 코인 잔고 조회 (KRW-BTC -> 보유수량 리턴)
            return self.sim_holdings.get(ticker, {}).get("vol", 0.0)
        
        try:
            return self.upbit.get_balance(ticker)
        except:
            return 0.0

    def get_avg_buy_price(self, ticker):
        """평단가 조회"""
        if self.is_simulation:
            return self.sim_holdings.get(ticker, {}).get("avg", 0.0)
        
        try:
            return self.upbit.get_avg_buy_price(ticker)
        except:
            return 0.0

    def buy_market_order(self, ticker, price_krw):
        """시장가 매수"""
        if self.is_simulation:
            # 현재가 조회가 안되므로, 메인에서 넘겨준 가격이라 가정하고 대략 계산
            # (실제 main.py에서직전 조회 가격을 넘겨주면 더 정확함. 여기선 단순화)
            # 시뮬레이션에서는 체결되었다고 가정하고 로그만 남김
            return {"uuid": "sim-buy-uuid", "state": "done"}

        try:
            return self.upbit.buy_market_order(ticker, price_krw)
        except Exception as e:
            print(f"❌ 매수 실패: {e}")
            return None

    # [중요] 시뮬레이션 잔고 업데이트용 헬퍼 함수
    def simulation_buy(self, ticker, amount, current_price):
        """모의투자 매수 체결 처리 (지갑 업데이트)"""
        if not self.is_simulation: return
        
        vol = amount / current_price # 수량 계산
        # 수수료(0.05%) 반영
        vol = vol * (1 - 0.0005) 
        
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [지갑] {ticker} {vol:.8f}개 매수 완료 (평단 {current_price:,.0f})")

    def sell_market_order(self, ticker, volume):
        """시장가 매도"""
        if self.is_simulation:
            print(f"\n✨ [모의 매도 체결] {ticker} | 수량: {volume:.8f}")
            if ticker in self.sim_holdings:
                # 수익 실현 후 KRW 복구 (단순화)
                avg = self.sim_holdings[ticker]['avg']
                # 현재가는 외부에서 받아야 정확하지만 대략 평단으로 계산 (로직 흐름 확인용)
                # 실제로는 main.py에서 simulation_sell을 호출해 정산함
                del self.sim_holdings[ticker]
            return {"uuid": "sim-sell-uuid", "state": "done"}

        try:
            return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            print(f"❌ 매도 실패: {e}")
            return None