# execution/risk_manager.py
# 보유 종목의 매도 시점(익절, 손절, 트레일링 스탑)을 전문적으로 판단합니다.

from config import STOP_LOSS_PCT, TRAILING_START, TRAILING_DROP

class RiskManager:
    def __init__(self):
        # 트레일링 스탑을 위한 고점 기록 저장소 {ticker: max_profit_pct}
        self.trailing_highs = {}

    def register_buy(self, ticker):
        """매수 성공 시 해당 코인의 고점 기록 초기화"""
        self.trailing_highs[ticker] = -100.0

    def check_exit_signal(self, ticker, current_price, avg_buy_price):
        """
        매도 신호 점검 (손절, 익절, 트레일링 스탑)
        Return: (Action: str, Message: str)
          - Action: "SELL" or "HOLD"
        """
        if avg_buy_price == 0:
            return "HOLD", ""

        # 💰 수수료(0.1%) + 슬리피지(0.05%) 포함한 순수익률 계산
        raw_profit = ((current_price - avg_buy_price) / avg_buy_price) * 100
        profit_pct = raw_profit - 0.15 

        # 고점 갱신 (트레일링 스탑용)
        if ticker not in self.trailing_highs:
            self.trailing_highs[ticker] = profit_pct
        else:
            self.trailing_highs[ticker] = max(self.trailing_highs[ticker], profit_pct)
        
        current_high = self.trailing_highs[ticker]

        # 1. 손절 (Stop Loss)
        if profit_pct <= STOP_LOSS_PCT:
            return "SELL", f"💧 손절 (수익률: {profit_pct:.2f}%)"

        # 2. 트레일링 스탑 (Trailing Stop)
        # 예: 0.5% 이상 올랐다가, 고점 대비 0.3% 떨어지면 익절
        if current_high >= TRAILING_START and (current_high - profit_pct) >= TRAILING_DROP:
            return "SELL", f"🎉 트레일링 익절 (고점: {current_high:.2f}% -> 현재: {profit_pct:.2f}%)"

        # 상태 메시지 리턴 (로그용)
        return "HOLD", f"{profit_pct:+.2f}%"