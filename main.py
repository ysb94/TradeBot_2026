# main.py
# 봇의 메인 로직을 담당하는 파일입니다. 데이터 수집, 신호 판단, 주문 처리를 담당합니다.

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from config import TARGET_COINS, TRADE_AMOUNT, STOP_LOSS_PCT, TAKE_PROFIT_PCT, IS_SIMULATION

async def main():
    print("========================================")
    print("   🐙 2026 Octopus Trading Bot - Final ")
    print("   Mode: " + ("🧪 Simulation" if IS_SIMULATION else "💳 Real Trading"))
    print("========================================")
    
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    
    # 데이터 수집 시작
    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            print("\r", end="", flush=True) # 줄바꿈 초기화

            for ticker in TARGET_COINS.keys():
                # 1. 데이터 가져오기
                data = aggregator.market_data[ticker]
                current_price = data['upbit']
                current_kimp = data['kimp']

                if current_price is None or current_kimp is None:
                    continue

                # 2. 보유 상태 확인
                balance = order_manager.get_balance(ticker)
                avg_price = order_manager.get_avg_buy_price(ticker)
                has_coin = balance > 0 and (balance * current_price) > 5000 # 5천원 이상 보유 시

                # --- [A] 매도 로직 (보유 중일 때) ---
                if has_coin:
                    # 수익률 계산
                    profit_pct = ((current_price - avg_price) / avg_price) * 100
                    
                    # 상태 표시 (수익률 포함)
                    print(f"[{ticker.split('-')[1]} {profit_pct:+.2f}%] ", end="", flush=True)

                    # 익절 또는 손절 조건 확인
                    if profit_pct >= TAKE_PROFIT_PCT: # 익절 (+1.0%)
                        print(f"\n🎉 {ticker} 익절! 수익률: {profit_pct:.2f}%")
                        order_manager.sell_market_order(ticker, balance)
                    
                    elif profit_pct <= STOP_LOSS_PCT: # 손절 (-1.5%)
                        print(f"\n💧 {ticker} 손절... 수익률: {profit_pct:.2f}%")
                        order_manager.sell_market_order(ticker, balance)

                # --- [B] 매수 로직 (미보유 중일 때) ---
                else:
                    is_buy, reason = signal_maker.check_buy_signal(
                        ticker, current_price, current_kimp
                    )
                    
                    icon = "🟢" if is_buy else "⚪"
                    print(f"[{ticker.split('-')[1]} {icon}] ", end="", flush=True)

                    if is_buy:
                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        
                        # KRW 잔고 확인
                        krw_balance = order_manager.get_balance("KRW")
                        if krw_balance >= TRADE_AMOUNT:
                            # 주문 실행
                            res = order_manager.buy_market_order(ticker, TRADE_AMOUNT)
                            if res:
                                # (모의투자용) 가상 지갑 업데이트
                                order_manager.simulation_buy(ticker, TRADE_AMOUNT, current_price)
                                # 연속 주문 방지 쿨타임
                                await asyncio.sleep(2) 
                        else:
                            print("❌ 잔고 부족")

            await asyncio.sleep(1) # 1초마다 갱신

        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 봇 종료")