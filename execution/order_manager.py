# execution/order_manager.py
# [최종] 호가창 분석 + 분할 매도 + 안전 금액 + [NEW] 허매수(Spoofing) 판독

import pyupbit
import time
import config

class OrderManager:
    def __init__(self):
        self.upbit = None
        self.sim_holdings = {} 
        self.sim_krw = config.SIMULATION_BALANCE 
        
        if not config.IS_SIMULATION:
            self.upbit = pyupbit.Upbit(config.UPBIT_ACCESS_KEY, config.UPBIT_SECRET_KEY)
            print("💳 [OrderManager] 실전 매매 모드")
        else:
            print(f"🧪 [OrderManager] 모의 투자 모드 (시작 금액: {self.sim_krw:,.0f}원)")

    # -----------------------------------------------------------
    # 🛡️ [안전 금액] 자산 25% + 호가창 10% 룰
    # -----------------------------------------------------------
    def calculate_safe_buy_amount(self, ticker, target_amount):
        krw_balance = self.get_balance("KRW")
        max_by_asset = krw_balance * config.MAX_ASSET_RATIO
        max_by_orderbook = float('inf') 
        try:
            ob = pyupbit.get_orderbook(ticker)
            if ob:
                asks = ob['orderbook_units'][:5]
                total_ask_value = sum([u['ask_size'] * u['ask_price'] for u in asks])
                max_by_orderbook = total_ask_value * config.MAX_OB_RATIO
        except: pass
        
        safe_amount = min(target_amount, max_by_asset, max_by_orderbook)
        
        if safe_amount < config.MIN_ORDER_VALUE: return 0
        if safe_amount < target_amount:
            print(f"   🛡️ [Safety] 주문 금액 조정: {target_amount/10000:.0f}만 -> {safe_amount/10000:.0f}만")
            print(f"      (사유: 자산제한 {max_by_asset/10000:.0f}만 / 호가제한 {max_by_orderbook/10000:.0f}만)")
        
        return safe_amount

    # -----------------------------------------------------------
    # 🕵️ [신규] 체결 속도 기반 허매수 판독 (Advanced Tape Reading)
    # -----------------------------------------------------------
    def check_fake_buy(self, ticker, trade_history_deque):
        """
        호가창은 매수 우위인데, 실제 체결이 안 일어나면 '허매수'로 판단
        Return: True(허매수 의심), False(정상)
        """
        try:
            # 1. 호가창 조회
            orderbook = pyupbit.get_orderbook(ticker)
            if not orderbook: return False

            units = orderbook['orderbook_units'][:5] # 5호가만 봄
            ask_size = sum([u['ask_size'] for u in units])
            bid_size = sum([u['bid_size'] for u in units])

            # 매수벽이 매도벽보다 2배 이상 두꺼운지 확인 (매수 우위 상태)
            is_bid_strong = bid_size > (ask_size * 2.0)
            
            if not is_bid_strong:
                return False # 매수벽이 안 두꺼우면 허매수 논할 필요 없음

            # 2. 최근 체결 내역 분석 (Tape Reading)
            now = time.time()
            recent_buy_vol = 0.0
            
            # 최근 3초간의 'BID'(매수 주도) 체결량 합산
            if trade_history_deque:
                for trade in list(trade_history_deque)[-20:]: # 뒤에서 20개만 확인
                    if now - trade['timestamp'] > 3.0: continue # 3초 지난건 무시
                    
                    if trade['side'] == 'BID': # 매수 체결(빨간불)
                        recent_buy_vol += trade['volume'] * trade['price']

            # 3. 판독: 매수벽은 빵빵한데(is_bid_strong), 실제 매수는 쥐꼬리(100만원 미만)인가?
            if recent_buy_vol < 1_000_000: # 기준: 최근 3초간 매수체결액 100만원 미만
                return True # 🚨 허매수 경보!
            
            return False

        except Exception as e:
            return False

    # --- [호가창 분석] ---
    def analyze_orderbook_health(self, ticker):
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            if not orderbook: return "NORMAL"
            units = orderbook['orderbook_units']
            depth = units[:config.OB_DEPTH_COUNT]
            ask_size = sum([u['ask_size'] for u in depth])
            bid_size = sum([u['bid_size'] for u in depth])
            if ask_size > bid_size * config.OB_BAD_RATIO: return "BAD"
            elif bid_size > ask_size * config.OB_GOOD_RATIO: return "GOOD"
            return "NORMAL"
        except: return "NORMAL"

    # --- [기초 조회] ---
    def get_balance(self, ticker="KRW"):
        if config.IS_SIMULATION:
            if ticker == "KRW": return self.sim_krw
            return self.sim_holdings.get(ticker, {}).get("vol", 0.0)
        try: return self.upbit.get_balance(ticker)
        except: return 0.0

    def get_avg_buy_price(self, ticker):
        if config.IS_SIMULATION:
            return self.sim_holdings.get(ticker, {}).get("avg", 0.0)
        try: return self.upbit.get_avg_buy_price(ticker)
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
        safe_amount = self.calculate_safe_buy_amount(ticker, amount_krw)
        if safe_amount <= 0:
            print(f"   🚫 [Buy Cancel] 안전 주문 가능액 부족 (0원)")
            return None

        if config.IS_SIMULATION: return {"uuid": "sim-buy", "state": "done"}
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            best_ask = orderbook['orderbook_units'][0]['ask_price']
            
            volume = safe_amount / best_ask
            
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

    # --- [매도] ---
    def sell_percentage(self, ticker, ratio, strategy="LIMIT"):
        current_vol = self.get_balance(ticker)
        sell_vol = current_vol * ratio
        if sell_vol == 0: return None
        print(f"   📉 [매도 실행] {ratio*100}% 처분 진행 ({strategy})")
        if strategy == "MARKET": return self.sell_market_order(ticker, sell_vol)
        else: return self.sell_limit_safe(ticker, sell_vol)

    def sell_limit_safe(self, ticker, volume):
        if config.IS_SIMULATION: return {"uuid": "sim-sell", "state": "done"}
        try:
            orderbook = pyupbit.get_orderbook(ticker)
            best_bid = orderbook['orderbook_units'][0]['bid_price']
            ret = self.upbit.sell_limit_order(ticker, best_bid, volume)
            if not ret or 'uuid' not in ret: return self.sell_market_order(ticker, volume)
            uuid = ret['uuid']
            time.sleep(1.5)
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
        try: return self.upbit.sell_market_order(ticker, volume)
        except Exception as e:
            print(f"❌ 시장가 매도 실패: {e}")
            return None

    # --- [모의투자] ---
    def simulation_buy(self, ticker, amount, current_price):
        if not config.IS_SIMULATION: return
        if self.sim_krw < amount: amount = self.sim_krw
        vol = amount / current_price * 0.9995 
        self.sim_krw -= amount
        self.sim_holdings[ticker] = {"vol": vol, "avg": current_price}
        print(f"   [가상] {ticker} 매수 ({amount:,.0f}원). 잔액: {self.sim_krw:,.0f}원")

    def simulation_sell(self, ticker, current_price):
        if not config.IS_SIMULATION or ticker not in self.sim_holdings: return
        vol = self.sim_holdings[ticker]['vol']
        sell_amount = vol * current_price * 0.9995 
        self.sim_krw += sell_amount
        del self.sim_holdings[ticker]
        print(f"   [가상] {ticker} 매도. 회수: {sell_amount:,.0f}원")