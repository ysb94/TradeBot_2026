# main.py
# 프로그램 시작점 (비동기 루프 실행)

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager # 추가됨
from config import TARGET_COIN_TICKER_UPBIT, TRADE_AMOUNT

async def main():
    print("========================================")
    print("   🤖 2026 Hybrid Trading Bot - v0.3   ")
    print("   Step 4: Full System Integrated       ")
    print("========================================")
    
    # 모듈 초기화
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager() # 주문 관리자 생성
    
    # 데이터 수집 시작
    asyncio.create_task(aggregator.run())

    print("⏳ 데이터 수집 및 초기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            upbit_price = aggregator.prices["upbit"]
            current_kimp = aggregator.kimchi_premium

            if upbit_price is not None and current_kimp is not None:
                # 1. 매수 신호 점검
                is_buy, reason = signal_maker.check_buy_signal(
                    TARGET_COIN_TICKER_UPBIT, 
                    upbit_price, 
                    current_kimp
                )

                status_color = "🟢" if is_buy else "⚪"
                
                # 2. 상태 출력
                print(f"\r[{status_color}] 현재가: {upbit_price:,.0f} | 김프: {current_kimp:+.2f}% | 상태: {reason}          ", end="", flush=True)

                # 3. 매수 실행 로직
                if is_buy:
                    # 현재 잔고 확인
                    balance = order_manager.get_balance("KRW")
                    
                    if balance >= TRADE_AMOUNT:
                        # 주문 실행
                        order_manager.buy_market_order(TARGET_COIN_TICKER_UPBIT, TRADE_AMOUNT)
                        
                        # 매수 후에는 중복 매수를 막기 위해 잠시 대기 (예: 1분)
                        print("\n⏸️ 매수 체결로 인해 잠시 대기합니다...")
                        await asyncio.sleep(60) 
                    else:
                        print("\n❌ 잔고 부족으로 매수 실패")

            await asyncio.sleep(3)

        except Exception as e:
            print(f"\n⚠️ Main Loop Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 봇을 종료합니다.")