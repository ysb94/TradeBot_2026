# execution/order_manager.py
# 주문 실행(매수/매도) 및 자산/잔고 조회 담당

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
        """특정 코인 혹은 원화 잔고 조회"""
        if self.is_simulation:
            if ticker == "KRW": return self.sim_krw
            return self.sim_holdings.get(ticker, {}).get("vol", 0.0)
        try:
            return self.upbit.get_balance(ticker)
        except: return 0.0

    def get_avg_buy_price(self, ticker):
        """평단가 조회"""
        if self.is_simulation:
            return self.sim_holdings.get(ticker, {}).get("avg", 0.0)
        try:
            return self.upbit.get_avg_buy_price(ticker)
        except: return 0.0

    def buy_market_order(self, ticker, price_krw):
        """시장가 매수"""
        if self.is_simulation:
            return {"uuid": "sim-buy", "state": "done"} 
        try:
            return self.upbit.buy_market_order(ticker, price_krw)
        except Exception as e:
            print(f"❌ 매수 실패: {e}")
            return None

    def sell_market_order(self, ticker, volume):
        """시장가 매도"""
        if self.is_simulation:
            return {"uuid": "sim-sell", "state": "done"}
        try:
            return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            print(f"❌ 매도 실패: {e}")
            return None

    # --- 모의투자 정산 로직 ---
    def simulation_buy(self, ticker, amount, current_price):
        if not self.is_simulation: return
        vol = amount / current_price * 0.9995 # 수수료 반영
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [가상체결] {ticker} 매수. 잔액: {self.sim_krw:,.0f}원")

    def simulation_sell(self, ticker, current_price):
        if not self.is_simulation or ticker not in self.sim_holdings: return
        vol = self.sim_holdings[ticker]['vol']
        sell_amount = vol * current_price * 0.9995 # 수수료 반영
        self.sim_krw += sell_amount
        del self.sim_holdings[ticker]
        print(f"   [가상체결] {ticker} 매도. 회수: {sell_amount:,.0f}원 | 잔액: {self.sim_krw:,.0f}원")

    def get_total_assets(self, current_prices):
        """총 추정 자산 계산"""
        total_value = 0.0
        
        if self.is_simulation:
            total_value = self.sim_krw
            for ticker, info in self.sim_holdings.items():
                if ticker in current_prices and current_prices[ticker]:
                    total_value += info['vol'] * current_prices[ticker]
        else:
            try:
                balances = self.upbit.get_balances()
                for b in balances:
                    if b['currency'] == 'KRW':
                        total_value += float(b['balance']) + float(b['locked'])
                    else:
                        ticker = f"KRW-{b['currency']}"
                        vol = float(b['balance']) + float(b['locked'])
                        if ticker in current_prices and current_prices[ticker]:
                            total_value += vol * current_prices[ticker]
            except: pass
                
        return total_value