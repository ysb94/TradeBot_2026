# main.py
# [최종] 자동 튜닝(Self-Optimizing) 엔진 탑재

import asyncio
import time
import config  # [중요] 설정을 동적으로 바꾸기 위해 모듈 전체를 import
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from data_feed.macro_client import MacroClient
from market_scanner import get_strategy_recommendation  # [신규] 분석기 호출

async def auto_tuner_loop():
    """
    [AI 자동 튜닝 스케줄러]
    4시간마다 시장을 분석하여 config 설정을 실시간으로 수정합니다.
    """
    while True:
        # 봇 시작 직후엔 바로 실행하지 않고, 4시간(14400초) 대기 후 첫 실행
        # (원한다면 테스트를 위해 60초 등으로 줄여볼 수 있음)
        await asyncio.sleep(14400) 
        
        print(f"\n🧠 [Auto Tuner] 시장 분석 및 설정 최적화 시작... ({time.strftime('%H:%M')})")
        
        try:
            # 1. 시장 분석 수행 (비용 0원)
            new_settings = get_strategy_recommendation()
            
            # 2. 설정값 유효성 검사 (안전장치)
            # AI가 터무니없는 값을 주면 무시하도록 범위 제한
            if not (10 <= new_settings['RSI_BUY_THRESHOLD'] <= 50):
                print(f"⚠️ [Tuner] RSI 추천값 이상({new_settings['RSI_BUY_THRESHOLD']}) -> 변경 취소")
                continue

            # 3. 메모리 상의 설정값 즉시 교체 (봇 재시작 불필요!)
            old_rsi = config.RSI_BUY_THRESHOLD
            
            config.TARGET_COINS = new_settings['TARGET_COINS']
            config.FOLLOWER_COINS = new_settings['FOLLOWER_COINS']
            config.RSI_BUY_THRESHOLD = new_settings['RSI_BUY_THRESHOLD']
            config.BB_MULTIPLIER = new_settings['BB_MULTIPLIER']
            config.MAX_KIMP_THRESHOLD = new_settings['MAX_KIMP_THRESHOLD']
            config.REVERSE_KIMP_THRESHOLD = new_settings['REVERSE_KIMP_THRESHOLD']
            config.CURRENT_EXCHANGE_RATE = new_settings['CURRENT_EXCHANGE_RATE']
            
            print(f"✅ [Tuner] 업데이트 완료!")
            print(f"   - 주도주: {len(config.TARGET_COINS)}개 로테이션")
            print(f"   - RSI 기준: {old_rsi} -> {config.RSI_BUY_THRESHOLD}")
            print(f"   - 김프 제한: {config.MAX_KIMP_THRESHOLD}%")
            
        except Exception as e:
            print(f"⚠️ [Tuner] 최적화 실패: {e}")

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - AI Auto Pilot")
    print(f"   Mode: {'🧪 Simulation' if config.IS_SIMULATION else '💳 Real Trading'}")
    print(f"========================================")
    
    # 객체 생성
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    risk_manager = RiskManager()
    macro_client = MacroClient()

    # [신규] 백그라운드에서 자동 튜닝 스케줄러 실행
    asyncio.create_task(auto_tuner_loop())
    
    # 데이터 수집 시작
    asyncio.create_task(aggregator.run())
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            # ---------------------------------------------------------
            # 🛑 [0] 거시경제 필터 (Macro Filter)
            # ---------------------------------------------------------
            if config.ENABLE_MACRO_FILTER:
                is_risk, reason = macro_client.is_volatility_risk()
                if is_risk:
                    print(f"\n🚫 [MACRO] 매매 일시 정지: {reason}")
                    print(f"   (변동성 완화 대기 중... 1분 Sleep)")
                    await asyncio.sleep(60)
                    continue 

            print("\r", end="", flush=True) 

            # 0. 자산 조회
            current_prices = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
            total_assets = order_manager.get_total_assets(current_prices)
            print(f"💰 {total_assets:,.0f}원 | ", end="", flush=True)

            # ---------------------------------------------------------
            # 🔥 [1] 긴급 매수 (변수명 앞에 config. 붙여야 함)
            # ---------------------------------------------------------
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                for coin in config.FOLLOWER_COINS: # config.FOLLOWER_COINS 사용
                    if risk_manager.is_in_cooldown(coin): continue
                    if order_manager.get_balance(coin) > 0: continue
                    
                    price = aggregator.market_data[coin]['upbit']
                    if price and order_manager.buy_limit_safe(coin, config.TRADE_AMOUNT):
                        order_manager.simulation_buy(coin, config.TRADE_AMOUNT, price)
                        risk_manager.register_buy(coin)
                
                aggregator.surge_detected = False
                print("✅ 긴급 매수 완료. 3초 대기...\n")
                await asyncio.sleep(3)
                continue

            # ---------------------------------------------------------
            # 🎯 [2] 일반 매매 (config.TARGET_COINS 사용)
            # ---------------------------------------------------------
            # 딕셔너리가 실행 중에 바뀔 수 있으므로 list()로 복사해서 순회
            for ticker in list(config.TARGET_COINS.keys()):
                
                # 데이터가 아직 없으면 스킵
                if ticker not in aggregator.market_data: continue
                
                data = aggregator.market_data[ticker]
                price = data['upbit']
                kimp = data['kimp']

                if price is None or kimp is None: continue

                balance = order_manager.get_balance(ticker)
                # 최소 주문 금액(5000원) 이상 있어야 보유 중으로 판단
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
                        
                        if ob_health == "BAD" or "손절" in msg:
                            sell_strategy = "MARKET"
                            print(f"   ⚠️ 급한 매도 (호가창 나쁨 or 손절) -> 시장가 실행")

                        if action == "SELL_ALL":
                            if order_manager.sell_percentage(ticker, 1.0, sell_strategy):
                                order_manager.simulation_sell(ticker, price)
                        elif action == "SELL_HALF":
                            order_manager.sell_percentage(ticker, config.PARTIAL_SELL_RATIO, sell_strategy)
                    else:
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 매수 관리
                else:
                    if risk_manager.is_in_cooldown(ticker): continue

                    is_buy, reason = signal_maker.check_buy_signal(ticker, price, kimp)
                    if is_buy:
                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        if order_manager.get_balance("KRW") >= config.TRADE_AMOUNT:
                            if order_manager.buy_limit_safe(ticker, config.TRADE_AMOUNT):
                                order_manager.simulation_buy(ticker, config.TRADE_AMOUNT, price)
                                risk_manager.register_buy(ticker)
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
        # 윈도우 환경설정 (필요시)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")