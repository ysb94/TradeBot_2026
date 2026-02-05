# main.py
# 봇의 메인 로직을 담당하는 파일입니다. 데이터 수집, 신호 판단, 주문 처리를 담당합니다.

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from config import TARGET_COINS, TRADE_AMOUNT, STOP_LOSS_PCT, IS_SIMULATION

async def main():
    print("========================================")
    print("   🐙 2026 Octopus Trading Bot - Fixed ")
    print(f"   Mode: {'🧪 Simulation' if IS_SIMULATION else '💳 Real Trading'}")
    print("========================================")
    
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    
    # [트레일링 스탑] 각 코인별 최고 수익률 기억장소
    # 구조: {'KRW-BTC': 1.5, 'KRW-ETH': 0.5 ...} (단위: %)
    trailing_highs = {} 

    # 트레일링 설정 (보고서 전략 반영)
    TRAILING_START = 0.5  # 0.5% 수익부터 추적 시작
    TRAILING_DROP = 0.3   # 고점 대비 0.3%p 빠지면 익절

    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            print("\r", end="", flush=True) 

            for ticker in TARGET_COINS.keys():
                data = aggregator.market_data[ticker]
                curr_price = data['upbit']
                curr_kimp = data['kimp']

                if curr_price is None: continue

                # 잔고 확인
                balance = order_manager.get_balance(ticker)
                avg_price = order_manager.get_avg_buy_price(ticker)
                has_coin = balance > 0 and (balance * curr_price) > 5000

                # ==============================
                # [A] 매도 로직 (보유 중) - 트레일링 스탑
                # ==============================
                if has_coin:
                    # 수익률 계산 (%)
                    profit_pct = ((curr_price - avg_price) / avg_price) * 100
                    
                    # 1. 고점 갱신 (Trailing High Update)
                    if ticker not in trailing_highs:
                        trailing_highs[ticker] = profit_pct
                    else:
                        trailing_highs[ticker] = max(trailing_highs[ticker], profit_pct)
                    
                    current_high = trailing_highs[ticker]
                    
                    # 상태 표시
                    print(f"[{ticker.split('-')[1]} {profit_pct:+.2f}%(고:{current_high:.1f})] ", end="", flush=True)

                    # 2. 매도 조건 판단
                    # 2-1. 손절 (Stop Loss)
                    if profit_pct <= STOP_LOSS_PCT:
                        print(f"\n💧 {ticker} 손절 (-1.5% 도달)")
                        res = order_manager.sell_market_order(ticker, balance)
                        if res: 
                            order_manager.simulation_sell(ticker, curr_price)
                            del trailing_highs[ticker] # 기록 삭제

                    # 2-2. 트레일링 익절 (Trailing Stop)
                    # 목표 수익(0.5%) 이상이고 + 고점 대비(0.3%) 하락 시
                    elif current_high >= TRAILING_START and (current_high - profit_pct) >= TRAILING_DROP:
                        print(f"\n🎉 {ticker} 트레일링 익절! (고점 {current_high:.2f}% -> 현재 {profit_pct:.2f}%)")
                        res = order_manager.sell_market_order(ticker, balance)
                        if res: 
                            order_manager.simulation_sell(ticker, curr_price)
                            del trailing_highs[ticker] # 기록 삭제

                # ==============================
                # [B] 매수 로직 (미보유 중)
                # ==============================
                else:
                    is_buy, reason = signal_maker.check_buy_signal(ticker, curr_price, curr_kimp)
                    icon = "🟢" if is_buy else "⚪"
                    print(f"[{ticker.split('-')[1]} {icon}] ", end="", flush=True)

                    if is_buy:
                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        krw = order_manager.get_balance("KRW")
                        if krw >= TRADE_AMOUNT:
                            res = order_manager.buy_market_order(ticker, TRADE_AMOUNT)
                            if res:
                                order_manager.simulation_buy(ticker, TRADE_AMOUNT, curr_price)
                                trailing_highs[ticker] = -100 # 초기화
                                await asyncio.sleep(1) # 연속 주문 방지
                        else:
                            print("❌ 잔고 부족")

            await asyncio.sleep(1)

        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")