# execution/risk_manager.py
# [최종] 지표 기반 손절(VWAP) + 분할 익절(50%) 로직 추가

import time
import config

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
        profit_pct = raw_profit - 0.15 # 수수료 반영 수익률
        
        # 진입 후 경과 시간 계산 (안전장치용)
        elapsed_time = 0
        if ticker in self.entry_times:
            elapsed_time = time.time() - self.entry_times[ticker]

        # 고점 갱신 (트레일링 스탑용)
        if ticker not in self.trailing_highs: self.trailing_highs[ticker] = profit_pct
        else: self.trailing_highs[ticker] = max(self.trailing_highs[ticker], profit_pct)
        current_high = self.trailing_highs[ticker]

        # ====================================================
        # 1. 🛡️ 손절 (Stop Loss)
        # ====================================================
        # 1-1. 수익률 손절 (이건 무조건 실행)
        if profit_pct <= config.STOP_LOSS_PCT:
            self.cooldowns[ticker] = time.time() + config.COOLDOWN_STOP_LOSS
            return "SELL_ALL", f"💧 가격 손절 ({profit_pct:.2f}%)"

        # 1-2. 지표 손절 (VWAP 붕괴 or RSI 급락)
        if analysis:
            vwap = analysis['VWAP']
            rsi = analysis['RSI_14']
            
            # [VWAP] 지지선 붕괴 (진입 후 3분은 유예 - 흔들기 방지)
            if elapsed_time > 180 and current_price < vwap * config.VWAP_STOP_FACTOR:
                self.cooldowns[ticker] = time.time() + config.COOLDOWN_VWAP_BREAK
                return "SELL_ALL", f"📉 VWAP 지지 붕괴 (현재 {current_price} < VWAP {vwap})"
            
            # [RSI] 투매 감지 (🔥🔥 수정된 핵심 로직 🔥🔥)
            # 진입 후 5분(300초) 동안은 RSI 손절 금지 (매수 시점 자체가 RSI가 낮으므로)
            if elapsed_time > 300 and rsi < config.RSI_PANIC_SELL:
                self.cooldowns[ticker] = time.time() + config.COOLDOWN_STOP_LOSS
                return "SELL_ALL", f"📉 RSI 급락 ({rsi}) - 투매 감지"

        # 1-3. 시간 손절 (너무 오래 횡보하면 탈출)
        if elapsed_time > config.TIME_CUT_SECONDS and profit_pct < config.TIME_CUT_MIN_PROFIT:
            self.cooldowns[ticker] = time.time() + config.COOLDOWN_TIME_CUT
            return "SELL_ALL", f"⏰ 시간 손절 ({int(elapsed_time)}초 지체)"

        # ... (이하 익절 로직은 기존 유지) ...
        # 2-1. 트레일링 스탑
        if current_high >= config.TRAILING_START and (current_high - profit_pct) >= config.TRAILING_DROP:
            return "SELL_ALL", f"🎉 트레일링 익절 (고점:{current_high:.2f}% -> 현재:{profit_pct:.2f}%)"

        # 2-2. 분할 익절
        if analysis and not self.partial_sold.get(ticker, False):
            bb_mid = analysis['BB_Mid']
            if current_price >= bb_mid and profit_pct > config.PARTIAL_SELL_MIN_PROFIT:
                self.partial_sold[ticker] = True
                return "SELL_HALF", f"🍰 1차 목표 달성 (BB중심선) -> {int(config.PARTIAL_SELL_RATIO*100)}% 익절"

        # 2-3. 최종 익절
        if analysis:
            bb_upper = analysis['BB_Upper']
            rsi = analysis['RSI_14']
            if current_price >= bb_upper:
                return "SELL_ALL", f"🚀 2차 목표 달성 (BB상단 터치) -> 전량 익절"
            if rsi >= config.RSI_SELL_THRESHOLD:
                return "SELL_ALL", f"🔥 과매수 도달 (RSI {rsi}) -> 전량 익절"

        return "HOLD", f"{profit_pct:+.2f}%"