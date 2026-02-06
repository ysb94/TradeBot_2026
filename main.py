# main.py
# [최종] 정밀 매수(골든크로스) + 정밀 매도(전략분리) + 쿨타임/시간손절

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from config import TARGET_COINS, TRADE_AMOUNT, FOLLOWER_COINS, IS_SIMULATION

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - Final Version")
    print(f"   Mode: {'🧪 Simulation' if IS_SIMULATION else '💳 Real Trading'}")
    print(f"========================================")
    
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    risk_manager = RiskManager()

    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            print("\r", end="", flush=True) 

            # 0. 자산 조회
            current_prices = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
            total_assets = order_manager.get_total_assets(current_prices)
            print(f"💰 {total_assets:,.0f}원 | ", end="", flush=True)

            # ---------------------------------------------------------
            # 🔥 [1] 긴급 매수 (지정가 추격)
            # ---------------------------------------------------------
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                for coin in FOLLOWER_COINS:
                    # 쿨타임 중이면 긴급 매수도 스킵 (안전 제일)
                    if risk_manager.is_in_cooldown(coin): continue
                    if order_manager.get_balance(coin) > 0: continue
                    
                    price = aggregator.market_data[coin]['upbit']
                    if price and order_manager.buy_limit_safe(coin, TRADE_AMOUNT):
                        order_manager.simulation_buy(coin, TRADE_AMOUNT, price)
                        risk_manager.register_buy(coin)
                
                aggregator.surge_detected = False
                print("✅ 긴급 매수 주문 완료. 3초 대기...\n")
                await asyncio.sleep(3)
                continue

            # ---------------------------------------------------------
            # 🎯 [2] 일반 매매
            # ---------------------------------------------------------
            for ticker in TARGET_COINS.keys():
                data = aggregator.market_data[ticker]
                price = data['upbit']
                kimp = data['kimp']

                if price is None or kimp is None: continue

                balance = order_manager.get_balance(ticker)
                has_coin = balance > 0 and (balance * price) > 5000

                # [A] 매도 관리
                if has_coin:
                    avg_price = order_manager.get_avg_buy_price(ticker)
                    action, msg = risk_manager.check_exit_signal(ticker, price, avg_price)
                    
                    if action == "SELL":
                        print(f"\n{msg}")
                        
                        # 손절 or 시간손절 -> 손절 전략 (빠른 탈출)
                        if "손절" in msg:
                            if order_manager.sell_stop_loss_strategy(ticker, balance):
                                order_manager.simulation_sell(ticker, price)
                        
                        # 익절 -> 익절 전략 (고가 매도)
                        else:
                            if order_manager.sell_take_profit_strategy(ticker, balance):
                                order_manager.simulation_sell(ticker, price)
                    else:
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 매수 관리
                else:
                    # 🧊 쿨타임 체크 (손절한 놈은 쳐다도 안 봄)
                    if risk_manager.is_in_cooldown(ticker):
                        continue

                    is_buy, reason = signal_maker.check_buy_signal(ticker, price, kimp)
                    if is_buy:
                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        if order_manager.get_balance("KRW") >= TRADE_AMOUNT:
                            if order_manager.buy_limit_safe(ticker, TRADE_AMOUNT):
                                order_manager.simulation_buy(ticker, TRADE_AMOUNT, price)
                                risk_manager.register_buy(ticker)
                                await asyncio.sleep(1)
                    else:
                        icon = "🟢" if is_buy else "⚪"
                        print(f"[{ticker.split('-')[1]} {icon}] ", end="", flush=True)

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