# main.py
# [최종] 전 종목 자동 스캔 + 완벽한 매도 + 허매수 필터 + 로깅

import asyncio
import time
import config
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from data_feed.macro_client import MacroClient
from trade_logger import TradeLogger
from market_scanner import get_strategy_recommendation # [신규] 스캐너 함수

async def auto_tuner_loop():
    """
    [AI Auto Pilot] 4시간마다 전 종목을 스캔하여 타겟을 교체합니다.
    """
    while True:
        # 봇 시작 직후에는 바로 스캔하지 않고, 4시간 대기
        await asyncio.sleep(14400) 
        
        print(f"\n🧠 [Auto Tuner] 시장 전체 스캔 및 타겟 교체 시작... ({time.strftime('%H:%M')})")
        
        try:
            # 1. 시장 스캔 및 추천 설정 가져오기
            recommendation = get_strategy_recommendation()
            new_targets = recommendation['TARGET_COINS']

            if not new_targets:
                print("⚠️ [Tuner] 스캔 결과 없음 -> 기존 타겟 유지")
                continue

            # 2. 설정 교체 (Memory Swap)
            old_count = len(config.TARGET_COINS)
            config.TARGET_COINS = new_targets
            config.FOLLOWER_COINS = recommendation['FOLLOWER_COINS']
            
            # (선택) 지표 기준도 시장 상황에 맞게 변경
            config.RSI_BUY_THRESHOLD = recommendation['RSI_BUY_THRESHOLD']
            
            print(f"✅ [Tuner] 타겟 리빌딩 완료 ({old_count}개 -> {len(new_targets)}개)")
            print(f"   - 신규 타겟: {list(new_targets.keys())}")
            
            # Aggregator는 내부적으로 config.TARGET_COINS의 길이(개수)가 변하면
            # 자동으로 재접속하도록 설계되어 있습니다. (aggregator.py 참조)
            
        except Exception as e:
            print(f"⚠️ [Tuner] 최적화 실패: {e}")

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - Auto Discovery")
    print(f"   Mode: {'🧪 Simulation' if config.IS_SIMULATION else '💳 Real Trading'}")
    print(f"========================================")
    
    # 객체 생성
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    risk_manager = RiskManager()
    macro_client = MacroClient()
    logger = TradeLogger()

    # [신규] 자동 튜너(스캐너) 백그라운드 실행
    asyncio.create_task(auto_tuner_loop())

    # 데이터 수집 시작
    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            # 🛑 [0] 거시경제 필터
            if config.ENABLE_MACRO_FILTER:
                is_risk, reason = macro_client.is_volatility_risk()
                if is_risk:
                    print(f"\n🚫 [MACRO] {reason} -> 1분 대기")
                    await asyncio.sleep(60)
                    continue 

            print("\r", end="", flush=True) 

            # 0. 자산 조회
            current_prices = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
            total_assets = order_manager.get_total_assets(current_prices)
            print(f"💰 {total_assets:,.0f}원 | ", end="", flush=True)

            # 🔥 [1] 긴급 매수 (FOLLOWER_COINS)
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                for coin in config.FOLLOWER_COINS:
                    if risk_manager.is_in_cooldown(coin): continue
                    if order_manager.get_balance(coin) > 0: continue
                    
                    price = aggregator.market_data[coin]['upbit'] if coin in aggregator.market_data else None
                    if price and order_manager.buy_limit_safe(coin, config.TRADE_AMOUNT):
                        order_manager.simulation_buy(coin, config.TRADE_AMOUNT, price)
                        risk_manager.register_buy(coin)
                        logger.log(coin, "BUY_URGENT", price, None, 0.0, "BTC 급등 추격")
                
                aggregator.surge_detected = False
                await asyncio.sleep(3)
                continue

            # 🎯 [2] 일반 매매 (TARGET_COINS)
            # 딕셔너리가 스캐너에 의해 변경될 수 있으므로 list()로 키 복사
            for ticker in list(config.TARGET_COINS.keys()):
                
                # 아직 데이터 수신 전이면 스킵
                if ticker not in aggregator.market_data: continue
                
                data = aggregator.market_data[ticker]
                price = data['upbit']
                kimp = data['kimp']

                if price is None: continue 

                balance = order_manager.get_balance(ticker)
                has_coin = balance > 0 and (balance * price) >= config.MIN_ORDER_VALUE

                # [A] 매도 관리
                if has_coin:
                    avg_price = order_manager.get_avg_buy_price(ticker)
                    analysis = signal_maker.get_analysis_only(ticker)
                    action, msg = risk_manager.check_exit_signal(ticker, price, avg_price, analysis)
                    
                    if action != "HOLD":
                        print(f"\n{msg}")
                        ob_health = order_manager.analyze_orderbook_health(ticker)
                        sell_strategy = "LIMIT"
                        if ob_health == "BAD" or "손절" in msg: sell_strategy = "MARKET"

                        executed = False
                        if action == "SELL_ALL":
                            if order_manager.sell_percentage(ticker, 1.0, sell_strategy):
                                order_manager.simulation_sell(ticker, price)
                                executed = True
                        elif action == "SELL_HALF":
                            if order_manager.sell_percentage(ticker, config.PARTIAL_SELL_RATIO, sell_strategy):
                                executed = True
                        
                        if executed:
                            profit_rate = ((price - avg_price) / avg_price) * 100
                            logger.log(ticker, action, price, analysis, profit_rate, msg)
                    else:
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 매수 관리
                else:
                    if risk_manager.is_in_cooldown(ticker): continue
                    
                    safe_kimp = kimp if kimp is not None else 0.0
                    
                    is_buy, reason, analysis = signal_maker.check_buy_signal(ticker, price, safe_kimp)
                    
                    if is_buy:
                        # 허매수 필터
                        trades = aggregator.trade_history.get(ticker, None)
                        if order_manager.check_fake_buy(ticker, trades):
                            print(f"\r🚫 {ticker} 허매수 감지 -> 진입 취소")
                            continue

                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        if order_manager.get_balance("KRW") >= config.TRADE_AMOUNT:
                            if order_manager.buy_limit_safe(ticker, config.TRADE_AMOUNT):
                                order_manager.simulation_buy(ticker, config.TRADE_AMOUNT, price)
                                risk_manager.register_buy(ticker)
                                logger.log(ticker, "BUY", price, analysis, 0.0, reason)
                                await asyncio.sleep(1)
                    else:
                        icon = "🟢" if is_buy else "⚪"
                        print(f"[{ticker.split('-')[1]} {icon}] ", end="", flush=True)

            await asyncio.sleep(config.LOOP_DELAY)

        except Exception as e:
            print(f"\n⚠️ Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")