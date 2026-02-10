# main.py
# [V13 Update] 매수 전 3대 AI 차트 검증(Double Check) 기능 탑재

import asyncio
import time
import config
import pyupbit # 차트 데이터 조회를 위해 필요
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from data_feed.macro_client import MacroClient
from trade_logger import TradeLogger
from market_scanner import get_strategy_recommendation
from ai_analyst import AIAnalyst # ✅ 직접 임포트

async def auto_tuner_loop():
    """30분마다 거시경제 분석(Macro) -> 전략 업데이트"""
    SCAN_INTERVAL = 1800 
    while True:
        print(f"\n🧠 [Auto Tuner] 전략 최적화 수행... ({time.strftime('%H:%M')})")
        try:
            recommendation = get_strategy_recommendation()
            new_targets = recommendation.get('TARGET_COINS', {})
            
            if new_targets:
                config.TARGET_COINS = new_targets
                config.FOLLOWER_COINS = recommendation.get('FOLLOWER_COINS', [])
                config.RSI_BUY_THRESHOLD = recommendation.get('RSI_BUY_THRESHOLD', 30)
                config.MAX_KIMP_THRESHOLD = recommendation.get('MAX_KIMP_THRESHOLD', 5.0)
                config.STOP_LOSS_PCT = recommendation.get('STOP_LOSS_PCT', -1.5)
                config.PARTIAL_SELL_MIN_PROFIT = recommendation.get('PARTIAL_SELL_MIN_PROFIT', 0.5)
                
                print(f"✅ [Tuner] 전략 업데이트: RSI<{config.RSI_BUY_THRESHOLD}, 손절{config.STOP_LOSS_PCT}%")
                print(f"   ({recommendation.get('REASON', 'Routine Update')})")
        except Exception as e:
            print(f"⚠️ [Tuner] 오류: {e}")

        await asyncio.sleep(SCAN_INTERVAL)

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - AI Committee")
    print(f"   Mode: {'🧪 Simulation' if config.IS_SIMULATION else '💳 Real Trading'}")
    print(f"========================================")
    
    # 객체 생성
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    risk_manager = RiskManager()
    macro_client = MacroClient()
    logger = TradeLogger()
    ai_analyst = AIAnalyst() # ✅ AI 분석관 생성

    # 태스크 시작
    asyncio.create_task(auto_tuner_loop())
    asyncio.create_task(aggregator.run())

    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    # 초기 자산 설정 (서킷 브레이커용)
    current_prices_init = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
    initial_total_assets = order_manager.get_total_assets(current_prices_init)
    is_circuit_break = False

    print(f"💰 초기 자산: {initial_total_assets:,.0f}원")

    while True:
        try:
            # [0] 거시경제 필터
            if config.ENABLE_MACRO_FILTER:
                is_risk, reason = macro_client.is_volatility_risk()
                if is_risk:
                    print(f"\n🚫 [MACRO] {reason} -> 대기")
                    await asyncio.sleep(60)
                    continue 

            print("\r", end="", flush=True) 

            # 자산 현황 및 서킷 브레이커
            current_prices = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
            current_total_assets = order_manager.get_total_assets(current_prices)
            pnl_rate = 0.0
            if initial_total_assets > 0:
                pnl_rate = ((current_total_assets - initial_total_assets) / initial_total_assets) * 100

            status_icon = "🟢" if not is_circuit_break else "🔴"
            print(f"{status_icon} {current_total_assets:,.0f}원 ({pnl_rate:+.2f}%) | ", end="", flush=True)

            if not is_circuit_break and pnl_rate <= -config.MAX_GLOBAL_LOSS_PCT:
                is_circuit_break = True
                print(f"\n🚨 [Circuit Breaker] 누적 손실 {pnl_rate:.2f}% -> 신규 매수 중단")

            # [1] 긴급 매수 (급등 추격) - 서킷 브레이커 시 중단
            if not is_circuit_break and aggregator.surge_detected:
                print(f"\n{aggregator.surge_info}")
                for coin in config.FOLLOWER_COINS:
                    if risk_manager.is_in_cooldown(coin): continue
                    if order_manager.get_balance(coin) > 0: continue
                    
                    price = aggregator.market_data[coin]['upbit']
                    if price and order_manager.buy_limit_safe(coin, config.TRADE_AMOUNT):
                        order_manager.simulation_buy(coin, config.TRADE_AMOUNT, price)
                        risk_manager.register_buy(coin)
                        logger.log(coin, "BUY_URGENT", price, None, 0.0, "BTC 급등 추격")
                aggregator.surge_detected = False

            # [2] 일반 매매 (Target Coins)
            active_tickers = list(config.TARGET_COINS.keys())
            holding_count = 0

            for ticker in active_tickers:
                if ticker not in aggregator.market_data: continue
                
                data = aggregator.market_data[ticker]
                price = data['upbit']
                kimp = data['kimp']
                if price is None: continue 

                balance = order_manager.get_balance(ticker)
                has_coin = balance > 0 and (balance * price) >= config.MIN_ORDER_VALUE

                # [A] 보유 중 -> 매도 로직
                if has_coin:
                    holding_count += 1
                    avg_price = order_manager.get_avg_buy_price(ticker)
                    analysis = signal_maker.get_analysis_only(ticker)
                    action, msg = risk_manager.check_exit_signal(ticker, price, avg_price, analysis)
                    
                    if action != "HOLD":
                        print(f"\n{msg}")
                        # 매도 실행
                        strategy = "MARKET" if "손절" in msg else "LIMIT"
                        executed = False
                        if action == "SELL_ALL":
                            if order_manager.sell_percentage(ticker, 1.0, strategy):
                                order_manager.simulation_sell(ticker, price)
                                executed = True
                        elif action == "SELL_HALF":
                            if order_manager.sell_percentage(ticker, config.PARTIAL_SELL_RATIO, strategy):
                                executed = True
                        
                        if executed:
                            p_rate = ((price - avg_price) / avg_price) * 100
                            logger.log(ticker, action, price, analysis, p_rate, msg)
                    else:
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 미보유 -> 매수 로직
                else:
                    if is_circuit_break: continue
                    if risk_manager.is_in_cooldown(ticker): continue
                    
                    safe_kimp = kimp if kimp is not None else 0.0
                    
                    # 1차: 기술적 지표 (RSI, VWAP 등)
                    is_buy, reason, analysis = signal_maker.check_buy_signal(ticker, price, safe_kimp)
                    
                    if is_buy:
                        # 허매수 필터
                        trades = aggregator.trade_history.get(ticker, None)
                        if order_manager.check_fake_buy(ticker, trades):
                            print(f"\r🚫 {ticker} 허매수 감지 -> 진입 취소")
                            continue
                        
                        # =========================================================
                        # 🚀 2차: AI 위원회 차트 검증 (The AI Chartist)
                        # =========================================================
                        print(f"\n🔎 {ticker} 1차 지표 통과. AI 위원회 검증 요청...")
                        
                        try:
                            # 최근 60분봉 데이터 조회
                            df = pyupbit.get_ohlcv(ticker, interval="minute1", count=60)
                            if df is not None:
                                # AI 3대장 회의 소집
                                ai_result = ai_analyst.verify_buy_signal_consensus(ticker, df)
                                
                                if ai_result and ai_result.get('decision') == "APPROVE":
                                    ai_reason = ai_result.get('reason', 'Approved')
                                    print(f"   ✅ [Chairman 승인] {ai_reason}")
                                    reason += f" / AI:{ai_reason}"
                                else:
                                    reject_reason = ai_result.get('reason') if ai_result else "No Response"
                                    print(f"   ✋ [Chairman 거부] {reject_reason} -> 진입 보류")
                                    # 3분간 쿨타임 (재요청 방지)
                                    risk_manager.cooldowns[ticker] = time.time() + 180
                                    continue 
                            else:
                                print("   ⚠️ 차트 데이터 조회 실패 -> AI 패스하고 진입")
                        except Exception as e:
                            print(f"   ⚠️ AI 검증 에러({e}) -> AI 패스하고 진입")
                        # =========================================================

                        print(f"🔥 {ticker} 매수 진입! ({reason})")
                        if order_manager.get_balance("KRW") >= config.TRADE_AMOUNT:
                            if order_manager.buy_limit_safe(ticker, config.TRADE_AMOUNT):
                                order_manager.simulation_buy(ticker, config.TRADE_AMOUNT, price)
                                risk_manager.register_buy(ticker)
                                logger.log(ticker, "BUY", price, analysis, 0.0, reason)
                                await asyncio.sleep(1)
                    else:
                        print(f"[{ticker.split('-')[1]} ⚪] ", end="", flush=True)

            if is_circuit_break and holding_count == 0:
                print(f"\n🛑 모든 자산 청산 완료. 봇을 종료합니다.")
                break

            await asyncio.sleep(config.LOOP_DELAY)

        except Exception as e:
            print(f"\n⚠️ Main Error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        # 윈도우 환경설정
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 봇 종료")