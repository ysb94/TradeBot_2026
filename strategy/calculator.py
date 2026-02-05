# calculator.py
# **"수수료 0.1%를 극복하기 위한 최소 틱 수"**를 계산하는 핵심 로직

import math

class TickCalculator:
    def __init__(self, fee_rate=0.0005): # 업비트 기본 수수료 0.05%
        self.fee_rate = fee_rate

    def get_tick_size(self, price):
        """
        2025-2026 업비트 호가 단위 정책 반영
        (1,000원 ~ 10,000원 구간 0.5원 반영)
        """
        if price >= 2000000: return 1000
        elif price >= 1000000: return 500
        elif price >= 500000: return 100
        elif price >= 100000: return 50
        elif price >= 10000: return 10
        elif price >= 1000: 
            return 0.5 # [보고서 반영] 1원 -> 0.5원으로 세분화
        elif price >= 100: return 0.1
        elif price >= 10: return 0.01
        else: return 0.0001

    def calculate_bep(self, buy_price):
        """
        손익분기점(BEP) 계산: 수수료 0.1%를 극복하고 본전이 되는 가격
        """
        # 매수/매도 수수료 포함 목표가
        target_price = buy_price * (1 + self.fee_rate) / (1 - self.fee_rate)
        
        # 호가 단위에 맞춰 올림(Ceiling) 처리
        tick_size = self.get_tick_size(target_price)
        bep_price = math.ceil(target_price / tick_size) * tick_size
        
        return bep_price

    def get_ticks_to_bep(self, current_price):
        """현재가 대비 본전까지 몇 틱을 올라야 하는지 계산"""
        bep_price = self.calculate_bep(current_price)
        tick_size = self.get_tick_size(current_price)
        
        # 필요한 틱 수 계산
        if tick_size == 0: return 0, bep_price
        ticks_needed = (bep_price - current_price) / tick_size
        
        return int(round(ticks_needed)), bep_price