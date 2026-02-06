# main.py
# [최종] 완벽한 매도 로직 (분할매도 + 호가창분석 + 지표손절)

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from config import TARGET_COINS, TRADE_AMOUNT, FOLLOWER_COINS, IS_SIMULATION

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - Perfect Selling")
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
            # 🔥 [1] 긴급 매수
            # ---------------------------------------------------------
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                for coin in FOLLOWER_COINS:
                    if risk_manager.is_in_cooldown(coin): continue
                    if order_manager.get_balance(coin) > 0: continue
                    
                    price = aggregator.market_data[coin]['upbit']
                    if price and order_manager.buy_limit_safe(coin, TRADE_AMOUNT):
                        order_manager.simulation_buy(coin, TRADE_AMOUNT, price)
                        risk_manager.register_buy(coin)
                
                aggregator.surge_detected = False
                print("✅ 긴급 매수 완료. 3초 대기...\n")
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
                    
                    # 🔍 [신규] 보유 코인 정밀 분석 (RSI, VWAP, BB)
                    analysis = signal_maker.get_analysis_only(ticker)
                    
                    # 🚦 매도 신호 점검 (지표 데이터 함께 전달)
                    action, msg = risk_manager.check_exit_signal(ticker, price, avg_price, analysis)
                    
                    if action != "HOLD":
                        print(f"\n{msg}")
                        
                        # 📼 [호가창 분석] 매도벽이 두꺼우면 시장가로 급하게 던짐
                        ob_health = order_manager.analyze_orderbook_health(ticker)
                        sell_strategy = "LIMIT" # 기본은 지정가
                        
                        if ob_health == "BAD" or "손절" in msg:
                            sell_strategy = "MARKET" # 매도벽 두껍거나 손절이면 시장가
                            print(f"   ⚠️ 급한 매도 (호가창 나쁨 or 손절) -> 시장가 실행")

                        # 실행
                        if action == "SELL_ALL":
                            if order_manager.sell_percentage(ticker, 1.0, sell_strategy):
                                order_manager.simulation_sell(ticker, price)
                                
                        elif action == "SELL_HALF":
                            # 분할 매도는 100% 시뮬레이션 지원이 어려우므로 실전/로그 위주
                            order_manager.sell_percentage(ticker, 0.5, sell_strategy)

                    else:
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 매수 관리
                else:
                    if risk_manager.is_in_cooldown(ticker): continue

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