# main.py
# 봇의 메인 로직 (지휘관 역할)

import asyncio
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager # [신규] 리스크 매니저 추가
from config import TARGET_COINS, TRADE_AMOUNT, FOLLOWER_COINS, IS_SIMULATION

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - Optimized")
    print(f"   Mode: {'🧪 Simulation' if IS_SIMULATION else '💳 Real Trading'}")
    print(f"========================================")
    
    # 각 모듈(담당자) 초기화
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    risk_manager = RiskManager() # 리스크 담당자

    # 데이터 수집 시작
    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            print("\r", end="", flush=True) 

            # 0. 실시간 자산 조회 및 출력
            current_prices = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
            total_assets = order_manager.get_total_assets(current_prices)
            print(f"💰 {total_assets:,.0f}원 | ", end="", flush=True)

            # ---------------------------------------------------------
            # 🔥 [1] 리더-팔로워 긴급 매수 (최우선 순위)
            # ---------------------------------------------------------
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                for coin in FOLLOWER_COINS:
                    if order_manager.get_balance(coin) > 0: continue # 이미 있으면 패스
                    
                    price = aggregator.market_data[coin]['upbit']
                    if price and order_manager.buy_market_order(coin, TRADE_AMOUNT):
                        order_manager.simulation_buy(coin, TRADE_AMOUNT, price)
                        risk_manager.register_buy(coin) # 리스크 매니저에게 "매수했음" 보고
                
                aggregator.surge_detected = False
                print("✅ 긴급 매수 완료. 3초간 쿨타임...\n")
                await asyncio.sleep(3)
                continue

            # ---------------------------------------------------------
            # 🎯 [2] 일반 순회 (매도 관리 -> 매수 탐색)
            # ---------------------------------------------------------
            for ticker in TARGET_COINS.keys():
                data = aggregator.market_data[ticker]
                price = data['upbit']
                kimp = data['kimp']

                if price is None or kimp is None: continue

                # 보유 여부 확인
                balance = order_manager.get_balance(ticker)
                has_coin = balance > 0 and (balance * price) > 5000

                # [A] 매도 판단 (RiskManager에게 위임)
                if has_coin:
                    avg_price = order_manager.get_avg_buy_price(ticker)
                    action, msg = risk_manager.check_exit_signal(ticker, price, avg_price)
                    
                    if action == "SELL":
                        print(f"\n{msg} -> 매도 실행")
                        if order_manager.sell_market_order(ticker, balance):
                            order_manager.simulation_sell(ticker, price)
                    else:
                        # 보유 중 로그 (예: [XRP +0.5%])
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 매수 판단 (SignalMaker에게 위임)
                else:
                    is_buy, reason = signal_maker.check_buy_signal(ticker, price, kimp)
                    if is_buy:
                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        if order_manager.get_balance("KRW") >= TRADE_AMOUNT:
                            if order_manager.buy_market_order(ticker, TRADE_AMOUNT):
                                order_manager.simulation_buy(ticker, TRADE_AMOUNT, price)
                                risk_manager.register_buy(ticker) # 매수 보고
                                await asyncio.sleep(1)
                    else:
                        # 관망 중 로그 (예: [XRP ⚪])
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