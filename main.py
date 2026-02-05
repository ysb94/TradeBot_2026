# main.py
# 봇의 메인 로직을 담당하는 파일입니다. 데이터 수집, 신호 판단, 주문 처리를 담당합니다.

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from config import TARGET_COINS, TRADE_AMOUNT, STOP_LOSS_PCT, IS_SIMULATION, FOLLOWER_COINS

async def main():
    print("========================================")
    print("   🐙 2026 Octopus Bot - Leader Follower ")
    print(f"   Mode: {'🧪 Simulation' if IS_SIMULATION else '💳 Real Trading'}")
    print("========================================")
    
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    
    trailing_highs = {} 
    TRAILING_START = 0.5  
    TRAILING_DROP = 0.3   

    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            print("\r", end="", flush=True) 

            # 🔥 [1. 리더-팔로워 긴급 매수 로직]
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                print("⚡ [FOLLOWER] 추종 코인 긴급 매수 실행!")
                
                for coin in FOLLOWER_COINS:
                    if order_manager.get_balance(coin) > 0:
                        continue
                        
                    current_price = aggregator.market_data[coin]['upbit']
                    if current_price:
                        res = order_manager.buy_market_order(coin, TRADE_AMOUNT)
                        if res:
                            order_manager.simulation_buy(coin, TRADE_AMOUNT, current_price)
                            trailing_highs[coin] = -100 
                
                aggregator.surge_detected = False
                print("✅ 긴급 매수 완료. 5초간 쿨타임...\n")
                await asyncio.sleep(5) 
                continue 

            # [2. 일반 루프 (RSI, 트레일링 스탑 등)]
            for ticker in TARGET_COINS.keys():
                data = aggregator.market_data[ticker]
                curr_price = data['upbit']
                curr_kimp = data['kimp']

                # [수정] 가격이나 김프 중 하나라도 없으면(None) 건너뜀 (에러 방지 핵심!)
                if curr_price is None or curr_kimp is None:
                    continue

                # 잔고 확인
                balance = order_manager.get_balance(ticker)
                avg_price = order_manager.get_avg_buy_price(ticker)
                has_coin = balance > 0 and (balance * curr_price) > 5000

                # [A] 매도 로직 (보유 중)
                if has_coin:
                    profit_pct = ((curr_price - avg_price) / avg_price) * 100
                    
                    if ticker not in trailing_highs: trailing_highs[ticker] = profit_pct
                    else: trailing_highs[ticker] = max(trailing_highs[ticker], profit_pct)
                    current_high = trailing_highs[ticker]
                    
                    print(f"[{ticker.split('-')[1]} {profit_pct:+.2f}%] ", end="", flush=True)

                    if profit_pct <= STOP_LOSS_PCT:
                        print(f"\n💧 {ticker} 손절")
                        if order_manager.sell_market_order(ticker, balance): 
                            order_manager.simulation_sell(ticker, curr_price)
                            del trailing_highs[ticker]

                    elif current_high >= TRAILING_START and (current_high - profit_pct) >= TRAILING_DROP:
                        print(f"\n🎉 {ticker} 트레일링 익절!")
                        if order_manager.sell_market_order(ticker, balance): 
                            order_manager.simulation_sell(ticker, curr_price)
                            del trailing_highs[ticker]

                # [B] 매수 로직 (일반 RSI 전략)
                else:
                    is_buy, reason = signal_maker.check_buy_signal(ticker, curr_price, curr_kimp)
                    icon = "🟢" if is_buy else "⚪"
                    print(f"[{ticker.split('-')[1]} {icon}] ", end="", flush=True)

                    if is_buy:
                        print(f"\n🔥 {ticker} 일반 진입! ({reason})")
                        if order_manager.get_balance("KRW") >= TRADE_AMOUNT:
                            if order_manager.buy_market_order(ticker, TRADE_AMOUNT):
                                order_manager.simulation_buy(ticker, TRADE_AMOUNT, curr_price)
                                trailing_highs[ticker] = -100
                                await asyncio.sleep(1)

            await asyncio.sleep(1)

        except Exception as e:
            # 에러가 나도 죽지 않고 로그만 찍고 재시도
            print(f"\n⚠️ Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")