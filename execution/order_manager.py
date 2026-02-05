# order_manager.py
# 실제 주문을 담당하는 모듈입니다. IS_SIMULATION 값에 따라 진짜 주문을 넣을지, 흉내만 낼지 결정

import pyupbit
from config import UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, IS_SIMULATION

class OrderManager:
    def __init__(self):
        self.is_simulation = IS_SIMULATION
        self.upbit = None
        
        # [모의투자용] 가상 지갑
        self.sim_holdings = {} 
        self.sim_krw = 10_000_000 # 1천만원 시작
        
        if not self.is_simulation:
            self.upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            print("💳 [OrderManager] 실전 매매 모드 (업비트 연결됨)")
        else:
            print("🧪 [OrderManager] 모의 투자 모드 (가상 지갑 가동)")

    def get_balance(self, ticker="KRW"):
        if self.is_simulation:
            if ticker == "KRW": return self.sim_krw
            return self.sim_holdings.get(ticker, {}).get("vol", 0.0)
        try:
            return self.upbit.get_balance(ticker)
        except: return 0.0

    def get_avg_buy_price(self, ticker):
        if self.is_simulation:
            return self.sim_holdings.get(ticker, {}).get("avg", 0.0)
        try:
            return self.upbit.get_avg_buy_price(ticker)
        except: return 0.0

    def buy_market_order(self, ticker, price_krw):
        if self.is_simulation:
            return {"uuid": "sim-buy", "state": "done"} # 가짜 성공 리턴
        try:
            return self.upbit.buy_market_order(ticker, price_krw)
        except Exception as e:
            print(f"❌ 매수 실패: {e}")
            return None

    def simulation_buy(self, ticker, amount, current_price):
        """모의투자 매수 정산"""
        if not self.is_simulation: return
        vol = amount / current_price * 0.9995 # 수수료 0.05% 차감
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [지갑] {ticker} 매수됨. 잔액: {self.sim_krw:,.0f}원")

    def sell_market_order(self, ticker, volume):
        if self.is_simulation:
            return {"uuid": "sim-sell", "state": "done"}
        try:
            return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            print(f"❌ 매도 실패: {e}")
            return None

    def simulation_sell(self, ticker, current_price):
        """[수정됨] 모의투자 매도 정산 (돈 돌려받기)"""
        if not self.is_simulation or ticker not in self.sim_holdings: return
        
        vol = self.sim_holdings[ticker]['vol']
        # 매도 금액 = 수량 * 현재가 * 수수료차감(99.95%)
        sell_amount = vol * current_price * 0.9995
        
        self.sim_krw += sell_amount
        del self.sim_holdings[ticker]
        print(f"   [지갑] {ticker} 매도됨. 회수금: {sell_amount:,.0f}원 | 잔액: {self.sim_krw:,.0f}원")