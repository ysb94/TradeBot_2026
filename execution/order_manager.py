# execution/order_manager.py
# [최종] 호가창 분석(Tape Reading) + 분할 매도 기능 탑재 + 동적 설정 지원

import pyupbit
import time
import config

class OrderManager:
    def __init__(self):
        # self.is_simulation 변수 삭제 (config 직접 참조)
        self.upbit = None
        self.sim_holdings = {} 
        
        # [수정] config에서 금액 가져오기
        self.sim_krw = config.SIMULATION_BALANCE 
        
        # 초기화 시점의 모드 출력
        if not config.IS_SIMULATION:
            self.upbit = pyupbit.Upbit(config.UPBIT_ACCESS_KEY, config.UPBIT_SECRET_KEY)
            print("💳 [OrderManager] 실전 매매 모드")
        else:
            print(f"🧪 [OrderManager] 모의 투자 모드 (시작 금액: {self.sim_krw:,.0f}원)")

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

            # N호가까지의 잔량 합계 계산 (config 참조)
            depth = units[:config.OB_DEPTH_COUNT]
            ask_size = sum([u['ask_size'] for u in depth])  # 매도 잔량 (저항)
            bid_size = sum([u['bid_size'] for u in depth])  # 매수 잔량 (지지)

            # 비율 분석 (config 참조)
            if ask_size > bid_size * config.OB_BAD_RATIO:
                return "BAD"
            elif bid_size > ask_size * config.OB_GOOD_RATIO:
                return "GOOD"
            
            return "NORMAL"
        except:
            return "NORMAL"

    # --- [기초 조회] ---
    def get_balance(self, ticker="KRW"):
        if config.IS_SIMULATION:
            if ticker == "KRW": return self.sim_krw
            return self.sim_holdings.get(ticker, {}).get("vol", 0.0)
        try:
            return self.upbit.get_balance(ticker)
        except: return 0.0

    def get_avg_buy_price(self, ticker):
        if config.IS_SIMULATION:
            return self.sim_holdings.get(ticker, {}).get("avg", 0.0)
        try:
            return self.upbit.get_avg_buy_price(ticker)
        except: return 0.0

    def get_total_assets(self, current_prices):
        total = 0.0
        if config.IS_SIMULATION:
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
        if config.IS_SIMULATION: return {"uuid": "sim-buy", "state": "done"}
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
        """
        current_vol = self.get_balance(ticker)
        sell_vol = current_vol * ratio
        
        if sell_vol == 0: return None

        print(f"   📉 [매도 실행] {ratio*100}% 처분 진행 ({strategy})")
        
        if strategy == "MARKET":
            return self.sell_market_order(ticker, sell_vol)
        else:
            return self.sell_limit_safe(ticker, sell_vol)

    def sell_limit_safe(self, ticker, volume):
        """지정가 매도 시도 -> 실패시 시장가"""
        if config.IS_SIMULATION: return {"uuid": "sim-sell", "state": "done"}
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
                self.upbit.cancel_order(uuid)
                time.sleep(0.5)
                
                remain = self.get_balance(ticker)
                if remain > 0:
                    print("   ⚠️ 지정가 미체결 -> 주문 취소 (다음 턴에 재시도)")
                    return None 
            return order_info
        except Exception as e:
            print(f"❌ 지정가 매도 에러: {e}")
            return None

    def sell_market_order(self, ticker, volume):
        if config.IS_SIMULATION: return {"uuid": "sim-sell", "state": "done"}
        try:
            return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            print(f"❌ 시장가 매도 실패: {e}")
            return None

    # --- 모의투자 정산 ---
    def simulation_buy(self, ticker, amount, current_price):
        if not config.IS_SIMULATION: return
        vol = amount / current_price * 0.9995 
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [가상] {ticker} 매수. 잔액: {self.sim_krw:,.0f}원")

    def simulation_sell(self, ticker, current_price):
        if not config.IS_SIMULATION or ticker not in self.sim_holdings: return
        vol = self.sim_holdings[ticker]['vol']
        sell_amount = vol * current_price * 0.9995 
        self.sim_krw += sell_amount
        del self.sim_holdings[ticker]
        print(f"   [가상] {ticker} 매도. 회수: {sell_amount:,.0f}원")