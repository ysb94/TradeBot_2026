# execution/risk_manager.py
# [최종] 지표 기반 손절(VWAP) + 분할 익절(50%) 로직 추가

import time
from config import STOP_LOSS_PCT, TRAILING_START, TRAILING_DROP

class RiskManager:
    def __init__(self):
        self.trailing_highs = {}
        self.cooldowns = {}
        self.entry_times = {}
        self.partial_sold = {} # {ticker: True} -> 이미 50% 팔았는지 체크

    def register_buy(self, ticker):
        self.trailing_highs[ticker] = -100.0
        self.entry_times[ticker] = time.time()
        self.partial_sold[ticker] = False # 매수 시 초기화

    def is_in_cooldown(self, ticker):
        if ticker in self.cooldowns:
            if time.time() < self.cooldowns[ticker]:
                return True
            else:
                del self.cooldowns[ticker]
        return False

    def check_exit_signal(self, ticker, current_price, avg_buy_price, analysis=None):
        """
        Return: (Action, Message)
        Action: "HOLD", "SELL_ALL", "SELL_HALF"
        """
        if avg_buy_price == 0: return "HOLD", ""

        raw_profit = ((current_price - avg_buy_price) / avg_buy_price) * 100
        profit_pct = raw_profit - 0.15
        
        # 고점 갱신 (트레일링 스탑용)
        if ticker not in self.trailing_highs: self.trailing_highs[ticker] = profit_pct
        else: self.trailing_highs[ticker] = max(self.trailing_highs[ticker], profit_pct)
        current_high = self.trailing_highs[ticker]

        # ====================================================
        # 1. 🛡️ 손절 (Stop Loss) - 가격 & 지표 & 시간
        # ====================================================
        # 1-1. 수익률 손절 (기존)
        if profit_pct <= STOP_LOSS_PCT:
            self.cooldowns[ticker] = time.time() + 3600
            return "SELL_ALL", f"💧 가격 손절 ({profit_pct:.2f}%)"

        # 1-2. 지표 손절 (VWAP 붕괴 or RSI 급락)
        if analysis:
            vwap = analysis['VWAP']
            rsi = analysis['RSI_14']
            
            # VWAP보다 1% 이상 빠지면 추세 이탈로 간주
            if current_price < vwap * 0.99: 
                self.cooldowns[ticker] = time.time() + 1800 # 30분 밴
                return "SELL_ALL", f"📉 VWAP 지지 붕괴 (현재 {current_price} < VWAP {vwap})"
            
            # RSI가 25 밑으로 꽂히면 투매로 간주
            if rsi < 25:
                self.cooldowns[ticker] = time.time() + 3600
                return "SELL_ALL", f"📉 RSI 급락 ({rsi}) - 투매 감지"

        # 1-3. 시간 손절 (3분)
        if ticker in self.entry_times:
            elapsed = time.time() - self.entry_times[ticker]
            if elapsed > 180 and profit_pct < 0.2:
                self.cooldowns[ticker] = time.time() + 600
                return "SELL_ALL", f"⏰ 시간 손절 ({int(elapsed)}초 지체)"

        # ====================================================
        # 2. 💰 익절 (Profit Taking) - 분할 & 트레일링
        # ====================================================
        # 2-1. 트레일링 스탑 (전량 청산)
        if current_high >= TRAILING_START and (current_high - profit_pct) >= TRAILING_DROP:
            return "SELL_ALL", f"🎉 트레일링 익절 (고점:{current_high:.2f}% -> 현재:{profit_pct:.2f}%)"

        # 2-2. 분할 익절 (50%) - 볼린저밴드 중심선 도달 시
        if analysis and not self.partial_sold.get(ticker, False):
            bb_mid = analysis['BB_Mid']
            if current_price >= bb_mid and profit_pct > 0.3: # 최소 수익 0.3%는 넘겨야 의미 있음
                self.partial_sold[ticker] = True # 플래그 세움 (또 팔지 않게)
                return "SELL_HALF", f"🍰 1차 목표 달성 (BB중심선) -> 50% 익절"

        # 2-3. 최종 익절 (전량) - 볼린저밴드 상단 or RSI 과매수
        if analysis:
            bb_upper = analysis['BB_Upper']
            rsi = analysis['RSI_14']
            if current_price >= bb_upper:
                return "SELL_ALL", f"🚀 2차 목표 달성 (BB상단 터치) -> 전량 익절"
            if rsi >= 70:
                return "SELL_ALL", f"🔥 과매수 도달 (RSI {rsi}) -> 전량 익절"

        return "HOLD", f"{profit_pct:+.2f}%"