# execution/order_manager.py
# [스마트 주문 v2] 손절/익절 상황별 정밀 타격 로직 탑재

import pyupbit
import time
from config import UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, IS_SIMULATION

class OrderManager:
    def __init__(self):
        self.is_simulation = IS_SIMULATION
        self.upbit = None
        self.sim_holdings = {} 
        self.sim_krw = 10_000_000 
        
        if not self.is_simulation:
            self.upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY)
            print("💳 [OrderManager] 실전 매매 모드 (정밀 매도 시스템 가동)")
        else:
            print("🧪 [OrderManager] 모의 투자 모드")

    # --- [기초 조회 함수들] ---
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

    def get_total_assets(self, current_prices):
        total = 0.0
        if self.is_simulation:
            total = self.sim_krw
            for t, info in self.sim_holdings.items():
                if t in current_prices and current_prices[t]:
                    total += info['vol'] * current_prices[t]
        else:
            try:
                balances = self.upbit.get_balances()
                for b in balances:
                    if b['currency'] == 'KRW':
                        total += float(b['balance']) + float(b['locked'])
                    else:
                        ticker = f"KRW-{b['currency']}"
                        vol = float(b['balance']) + float(b['locked'])
                        if ticker in current_prices and current_prices[ticker]:
                            total += vol * current_prices[ticker]
            except: pass
        return total

    # --- [매수 로직] (기존 유지) ---
    def buy_limit_safe(self, ticker, amount_krw):
        """매도 1호가 지정가 매수 -> 2초 대기 -> 미체결 취소"""
        if self.is_simulation: return {"uuid": "sim-buy", "state": "done"}
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            best_ask = orderbook['orderbook_units'][0]['ask_price']
            volume = amount_krw / best_ask
            
            ret = self.upbit.buy_limit_order(ticker, best_ask, volume)
            if not ret or 'uuid' not in ret: return None
            
            uuid = ret['uuid']
            time.sleep(2) # 대기
            
            order_info = self.upbit.get_order(uuid)
            if order_info and order_info['state'] == 'wait':
                self.upbit.cancel_order(uuid)
                return None 
            return order_info
        except Exception as e:
            print(f"❌ 매수 에러: {e}")
            return None

    # -----------------------------------------------------------
    # 🔥 [전략 1] 손절 전용 매도 (빠르고 확실하게)
    # 1. 지정가 -> 2. 지정가(1틱 아래) -> 3. 시장가
    # -----------------------------------------------------------
    def sell_stop_loss_strategy(self, ticker, volume):
        if self.is_simulation: return {"uuid": "sim-sell", "state": "done"}
        print(f"   💧 [손절 전략] 시작: {ticker}")

        try:
            # [1단계] 현재 매수 1호가에 던짐
            orderbook = pyupbit.get_orderbook(ticker)
            best_bid = orderbook['orderbook_units'][0]['bid_price']
            
            ret = self.upbit.sell_limit_order(ticker, best_bid, volume)
            if ret and 'uuid' in ret:
                time.sleep(1) # 1초 대기
                if self._check_and_cancel(ret['uuid']): 
                    return ret # 체결 완료

            # [2단계] 미체결 시 -> 1틱 더 싸게 던짐 (급함!)
            # 남은 물량 재조회
            volume = self.get_balance(ticker) 
            if volume <= 0: return ret

            orderbook = pyupbit.get_orderbook(ticker)
            best_bid = orderbook['orderbook_units'][0]['bid_price']
            tick_size = pyupbit.get_tick_size(best_bid)
            lower_price = best_bid - tick_size # 1틱 아래

            print(f"   💧 [손절 2단계] 1틱 하향 매도 시도 ({lower_price})")
            ret = self.upbit.sell_limit_order(ticker, lower_price, volume)
            if ret and 'uuid' in ret:
                time.sleep(1)
                if self._check_and_cancel(ret['uuid']): 
                    return ret

            # [3단계] 아직도 안 팔림 -> 시장가 투척
            volume = self.get_balance(ticker)
            if volume > 0:
                print(f"   💧 [손절 3단계] 시장가 투척")
                return self.upbit.sell_market_order(ticker, volume)

        except Exception as e:
            print(f"❌ 손절 실행 중 에러: {e}")
            return None

    # -----------------------------------------------------------
    # 🔥 [전략 2] 익절 전용 매도 (최대한 비싸게)
    # 1~3. 지정가 재시도(3회) -> 4. 지정가(1틱 아래) -> 5. 시장가
    # -----------------------------------------------------------
    def sell_take_profit_strategy(self, ticker, volume):
        if self.is_simulation: return {"uuid": "sim-sell", "state": "done"}
        print(f"   🎉 [익절 전략] 시작: {ticker}")

        try:
            # [1~3단계] 지정가 3회 시도
            for i in range(3):
                orderbook = pyupbit.get_orderbook(ticker)
                best_bid = orderbook['orderbook_units'][0]['bid_price']
                
                # 주문
                ret = self.upbit.sell_limit_order(ticker, best_bid, volume)
                if ret and 'uuid' in ret:
                    time.sleep(1) # 1초 대기
                    if self._check_and_cancel(ret['uuid']):
                        return ret # 체결 완료되면 종료
                
                # 미체결돼서 취소됐으면, 다음 루프에서 다시 호가 조회해서 재시도
                volume = self.get_balance(ticker)
                if volume <= 0: return ret

            # [4단계] 3번 해도 안 팔림 -> 1틱 싸게 (물량 정리)
            orderbook = pyupbit.get_orderbook(ticker)
            best_bid = orderbook['orderbook_units'][0]['bid_price']
            tick_size = pyupbit.get_tick_size(best_bid)
            lower_price = best_bid - tick_size

            print(f"   🎉 [익절 4단계] 1틱 하향 매도 ({lower_price})")
            ret = self.upbit.sell_limit_order(ticker, lower_price, volume)
            if ret and 'uuid' in ret:
                time.sleep(1)
                if self._check_and_cancel(ret['uuid']):
                    return ret
            
            # [5단계] 최후의 수단 -> 시장가
            volume = self.get_balance(ticker)
            if volume > 0:
                print(f"   🎉 [익절 5단계] 시장가 정리")
                return self.upbit.sell_market_order(ticker, volume)

        except Exception as e:
            print(f"❌ 익절 실행 중 에러: {e}")
            return None

    def _check_and_cancel(self, uuid):
        """주문 상태 확인 후 미체결이면 취소하는 헬퍼 함수"""
        try:
            order = self.upbit.get_order(uuid)
            if order and order['state'] == 'wait':
                self.upbit.cancel_order(uuid)
                time.sleep(0.2) # 취소 반영 대기
                return False # 미체결 (취소함)
            return True # 체결됨 (혹은 이미 완료)
        except: return False

    # --- 모의투자 정산 ---
    def simulation_buy(self, ticker, amount, current_price):
        if not self.is_simulation: return
        vol = amount / current_price * 0.9995 
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [가상] {ticker} 매수. 잔액: {self.sim_krw:,.0f}원")

    def simulation_sell(self, ticker, current_price):
        if not self.is_simulation or ticker not in self.sim_holdings: return
        vol = self.sim_holdings[ticker]['vol']
        sell_amount = vol * current_price * 0.9995 
        self.sim_krw += sell_amount
        del self.sim_holdings[ticker]
        print(f"   [가상] {ticker} 매도. 회수: {sell_amount:,.0f}원")