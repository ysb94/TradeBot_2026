# execution/order_manager.py
# [최종] 호가창 분석(Tape Reading) + 분할 매도 기능 탑재

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
            print("💳 [OrderManager] 실전 매매 모드 (호가창 분석 시스템 가동)")
        else:
            print("🧪 [OrderManager] 모의 투자 모드")

    # --- [호가창 분석: Tape Reading] ---
    def analyze_orderbook_health(self, ticker):
        """
        호가창 상태를 분석하여 매도 강도를 판단
        Return: "GOOD"(매수벽 튼튼), "BAD"(매도벽 두꺼움), "NORMAL"
        """
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            if not orderbook: return "NORMAL"

            units = orderbook['orderbook_units']
            
            # 5호가까지의 잔량 합계 계산
            ask_size = sum([u['ask_size'] for u in units[:5]]) # 매도 잔량 (저항)
            bid_size = sum([u['bid_size'] for u in units[:5]]) # 매수 잔량 (지지)
            
            # 비율 분석
            if ask_size > bid_size * 3:
                return "BAD" # 매도벽이 3배 이상 두꺼움 (뚫기 힘듦 -> 시장가 던져야 할 수도)
            elif bid_size > ask_size * 2:
                return "GOOD" # 매수벽이 튼튼함 (지정가로 버텨볼 만함)
            
            return "NORMAL"
        except:
            return "NORMAL"

    # --- [기초 조회] ---
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

    # --- [매수] ---
    def buy_limit_safe(self, ticker, amount_krw):
        if self.is_simulation: return {"uuid": "sim-buy", "state": "done"}
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            best_ask = orderbook['orderbook_units'][0]['ask_price']
            volume = amount_krw / best_ask
            
            ret = self.upbit.buy_limit_order(ticker, best_ask, volume)
            if not ret or 'uuid' not in ret: return None
            
            uuid = ret['uuid']
            time.sleep(2)
            
            order_info = self.upbit.get_order(uuid)
            if order_info and order_info['state'] == 'wait':
                self.upbit.cancel_order(uuid)
                return None 
            return order_info
        except Exception as e:
            print(f"❌ 매수 에러: {e}")
            return None

    # --- [매도: 분할 매도 지원] ---
    def sell_percentage(self, ticker, ratio, strategy="LIMIT"):
        """
        보유 물량의 특정 비율(ratio)만큼 매도
        strategy: "LIMIT" (지정가 추격), "MARKET" (시장가)
        """
        current_vol = self.get_balance(ticker)
        sell_vol = current_vol * ratio
        
        # 너무 적은 수량이면 매도 불가 (5000원 미만 등 체크 필요하지만 여기선 생략)
        if sell_vol == 0: return None

        print(f"   📉 [매도 실행] {ratio*100}% 처분 진행 ({strategy})")
        
        if strategy == "MARKET":
            return self.sell_market_order(ticker, sell_vol)
        else:
            # 지정가 안전 매도 (기존 로직 활용)
            return self.sell_limit_safe(ticker, sell_vol)

    def sell_limit_safe(self, ticker, volume):
        """지정가 매도 시도 -> 실패시 시장가"""
        if self.is_simulation: return {"uuid": "sim-sell", "state": "done"}
        try:
            # 1. 호가 확인
            orderbook = pyupbit.get_orderbook(ticker)
            best_bid = orderbook['orderbook_units'][0]['bid_price']
            
            # 2. 지정가 주문
            ret = self.upbit.sell_limit_order(ticker, best_bid, volume)
            if not ret or 'uuid' not in ret: 
                return self.sell_market_order(ticker, volume)
            
            uuid = ret['uuid']
            time.sleep(1.5) # 대기
            
            # 3. 체결 확인
            order_info = self.upbit.get_order(uuid)
            if order_info and order_info['state'] == 'wait':
                # 미체결시 취소 후 시장가
                self.upbit.cancel_order(uuid)
                time.sleep(0.5)
                # 남은 물량 시장가
                remain = self.get_balance(ticker) # 잔고 다시 확인 (일부 체결됐을 수 있음)
                # 부분매도 상황에서는 'volume'만큼만 팔아야 하므로 복잡해질 수 있음.
                # 여기서는 간단히 '주문했던 양만큼' 다시 시장가로 던지는 건 위험하므로(잔고부족),
                # 그냥 '남은 잔고 중 판매하려던 비율'을 계산해야 하나, 
                # 안전하게 '현재 잔고'를 확인해서 다시 던짐 (전량 매도 시 유효)
                # *분할 매도 시에는 이 부분이 조금 부정확할 수 있으나 안전을 위해 시장가 전환*
                if remain > 0:
                    # 주의: 분할매도였다면 remain이 전체 잔고일 수 있음. 
                    # 미체결분만 시장가로 던지는 로직은 복잡하므로, 
                    # 여기서는 지정가 취소되면 -> "주문 실패" 처리하고 다음 루프에 맡기는 게 안전함
                    print("   ⚠️ 지정가 미체결 -> 주문 취소 (다음 턴에 재시도)")
                    return None 
            return order_info
        except Exception as e:
            print(f"❌ 지정가 매도 에러: {e}")
            return None

    def sell_market_order(self, ticker, volume):
        if self.is_simulation: return {"uuid": "sim-sell", "state": "done"}
        try:
            return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            print(f"❌ 시장가 매도 실패: {e}")
            return None

    # --- 모의투자 정산 ---
    def simulation_buy(self, ticker, amount, current_price):
        if not self.is_simulation: return
        vol = amount / current_price * 0.9995 
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [가상] {ticker} 매수. 잔액: {self.sim_krw:,.0f}원")

    def simulation_sell(self, ticker, current_price):
        if not self.is_simulation or ticker not in self.sim_holdings: return
        # 시뮬레이션은 전량 매도만 구현 (단순화)
        vol = self.sim_holdings[ticker]['vol']
        sell_amount = vol * current_price * 0.9995 
        self.sim_krw += sell_amount
        del self.sim_holdings[ticker]
        print(f"   [가상] {ticker} 매도. 회수: {sell_amount:,.0f}원")