# execution/risk_manager.py
# [업데이트] 손절 쿨타임 + 시간 손절(Time Stop) 기능 탑재

import time
from config import STOP_LOSS_PCT, TRAILING_START, TRAILING_DROP

class RiskManager:
    def __init__(self):
        self.trailing_highs = {}
        self.cooldowns = {}      # {ticker: release_time}
        self.entry_times = {}    # {ticker: entry_timestamp} 매수 시간 기록

    def register_buy(self, ticker):
        """매수 성공 시 초기화"""
        self.trailing_highs[ticker] = -100.0
        self.entry_times[ticker] = time.time() # 매수 시간 기록

    def is_in_cooldown(self, ticker):
        """쿨타임 확인"""
        if ticker in self.cooldowns:
            if time.time() < self.cooldowns[ticker]:
                return True
            else:
                del self.cooldowns[ticker]
        return False

    def check_exit_signal(self, ticker, current_price, avg_buy_price):
        """매도 신호 점검 (손절, 익절, 트레일링, 시간손절)"""
        if avg_buy_price == 0:
            return "HOLD", ""

        # 순수익률 계산
        raw_profit = ((current_price - avg_buy_price) / avg_buy_price) * 100
        profit_pct = raw_profit - 0.15 

        # 고점 갱신
        if ticker not in self.trailing_highs:
            self.trailing_highs[ticker] = profit_pct
        else:
            self.trailing_highs[ticker] = max(self.trailing_highs[ticker], profit_pct)
        
        current_high = self.trailing_highs[ticker]

        # 1. 가격 손절 (Stop Loss) -> 쿨타임 1시간
        if profit_pct <= STOP_LOSS_PCT:
            self.cooldowns[ticker] = time.time() + 3600 
            return "SELL", f"💧 손절 (수익률: {profit_pct:.2f}%) -> 1시간 밴🚫"

        # 2. 시간 손절 (Time Stop)
        # 매수 후 3분(180초) 지났는데 수익이 0.2% 미만이면 정리
        if ticker in self.entry_times:
            elapsed_time = time.time() - self.entry_times[ticker]
            if elapsed_time > 180 and profit_pct < 0.2:
                # 시간 손절은 쿨타임 10분만 적용
                self.cooldowns[ticker] = time.time() + 600
                return "SELL", f"⏰ 시간 손절 ({int(elapsed_time)}초 경과, 수익지체) -> 10분 밴"

        # 3. 트레일링 스탑 (Trailing Stop)
        if current_high >= TRAILING_START and (current_high - profit_pct) >= TRAILING_DROP:
            return "SELL", f"🎉 트레일링 익절 (고점: {current_high:.2f}% -> 현재: {profit_pct:.2f}%)"

        return "HOLD", f"{profit_pct:+.2f}%"