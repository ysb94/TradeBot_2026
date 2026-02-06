📋 남은 개발 로드맵 (To-Do List)
현재 봇은 '방어력(매크로 회피)'과 '기본 공격력(RSI+VWAP)'을 갖췄습니다. 다음 단계는 **'적의 속임수 간파(호가창)'**와 **'거물급 정보(고래)'**를 장착할 차례입니다.

🥇 1순위: 호가창 '속임수' 판독기 (Advanced Tape Reading)
[상태: 부분 구현됨 (단순 비율만 확인 중)] 현재 order_manager.py는 매수/매도 잔량의 단순 합계 비율만 보고 있습니다. 세력이 허수 주문을 넣었다 빼는 행위나, 순식간에 긁어가는 속도를 감지하지 못합니다.

❌ 미구현 기능:

허수 주문(Fake Wall) 감지: 호가창 스냅샷을 1초 단위로 비교하여, 체결 없이 사라지는 대량 주문(취소 주문)을 포착하고 해당 방향 진입을 차단하는 로직.

스윕(Sweep) 감지: 누군가 시장가로 매도 1~3호가를 한 번에 긁어가는 **'체결 속도'**를 계산하여 추세에 동참(Momentum Trading)하는 로직.

📥 더 필요한 데이터:

trade 웹소켓 구독: 현재 aggregator.py는 ticker만 받습니다. trade 타입(체결 내역)을 추가 구독하여 **'초당 체결 건수'**와 '체결 강도' 데이터를 실시간 수집해야 합니다.

🥈 2순위: 온체인 고래 감시 (Whale Alert)
[상태: 미구현] 리플(XRP)이나 이더리움(ETH) 같은 코인은 거래소로 대량 입금 시 하락할 확률이 높습니다.

❌ 미구현 기능:

거래소 유입 급증 감지: 특정 코인이 업비트 지갑으로 대량 이체될 때, 매수를 멈추거나 보유 물량을 매도하는 방어 로직.

📥 더 필요한 데이터:

On-chain Data API: CryptoQuant, Whale Alert 등의 외부 API 연동 필요 (주기적 호출).


🚀 추천하는 다음 단계 (Next Step)
가장 효과적이고 코드 수정이 자연스러운 순서는 **[1순위: 호가창 속임수 판독기]**입니다.

aggregator.py 수정: 업비트 웹소켓에서 trade 데이터 추가 수신.

order_manager.py 고도화: 체결 속도(Velocity)와 주문 취소율(Cancellation Rate) 계산 로직 추가.

이 기능을 추가하면, 단순히 "싸니까 산다"가 아니라 **"누군가 급하게 사니까 같이 산다"**는 스마트한 매매가 가능해집니다.


------------------------------------------------------------






사용자님의 아이디어는 매우 훌륭합니다. 이는 전문적인 퀀트 트레이딩에서 사용하는 "유니버스 선정(Universe Selection) -> 알파 모델(Alpha Model) -> 포트폴리오 구성(Portfolio Construction)" 단계와 정확히 일치하는 접근 방식입니다.

제안하신 **'깔때기(Funnel)식 필터링'**과 '유동성에 따른 매수 금액 조절' 방식에 대한 분석과 구현 방향을 정리해 드립니다.

1. 🔍 깔때기식 전수 조사 (Funnel Filtering)
**"코인을 미리 제한하지 말고, 전체에서 시작해서 걸러내자"**는 아이디어는 기회를 놓치지 않는다는 점에서 매우 강력합니다.

현재 코드의 한계: 현재 config.py의 TARGET_COINS에 등록된 소수의 코인만 감시합니다. market_scanner.py도 단순히 '거래대금 상위 10개'만 뽑아냅니다. 이렇게 하면 거래대금은 적지만 급등 직전인 '알짜배기' 코인을 놓칠 수 있습니다.

개선 방향 (깔때기 모델):

1단계 (전수 조사): 업비트 원화 마켓 전 종목(100+개) 스캔.

2단계 (기초 필터): 최소 거래대금(예: 10억 이상), 호가창 촘촘함 등 기본적인 '거래 가능성' 확인.

3단계 (기술적 필터): 현재 가격이 볼린저 밴드 하단이거나, RSI가 과매도인 종목만 추출.

4단계 (최종 선정): 이 조건을 통과한 종목들만 TARGET_COINS로 등록하여 웹소켓으로 실시간 감시.

주의할 점:

API 제한: 100개 코인의 캔들/호가 정보를 1초마다 가져오면 업비트 API 요청 제한(초당 10~30회)에 걸립니다. 따라서 1단계(전수 조사)는 10분~1시간 간격으로 수행하고, 여기서 선별된 5~10개만 **웹소켓(실시간)**으로 감시하는 구조가 효율적입니다.

2. 💸 유동성 기반 매수 금액 조절 (Dynamic Sizing)
**"작은 코인은 매물대에 맞춰 매수 금액을 줄이자"**는 아이디어는 슬리피지(Slippage)와 미체결 위험을 방지하는 핵심 리스크 관리 기법입니다.

현재 코드: config.py의 TRADE_AMOUNT(예: 6000원)로 고정되어 있습니다. 코인이 크든 작든 똑같은 돈을 태우므로, 호가가 얇은 코인에서는 불리하게 체결될 수 있습니다.

구현 로직 제안 (order_manager.py 수정): 주문을 넣기 전에 호가창의 두께(Depth)를 확인하고, **"매도 1~3호가 총잔량의 10%까지만 매수"**하는 식으로 로직을 변경합니다.


자산 관리 (Portfolio Sizing): "내 전체 시드의 N% 까지만 진입한다." (올인 방지)

유동성 관리 (Liquidity Sizing): "호가창 매물대의 10% 까지만 진입한다." (슬리피지 방지)


파이썬
# (예시 로직)
def calculate_safe_amount(ticker, target_amount):
    orderbook = pyupbit.get_orderbook(ticker)
    # 매도 1~3호가 물량을 합침 (즉시 살 수 있는 물량)
    ask_depth = sum([u['ask_size'] * u['ask_price'] for u in orderbook['orderbook_units'][:3]])

    # 호가창 물량의 10%만 진입하도록 제한 (충격 방지)
    max_allowed = ask_depth * 0.1 

    # 설정된 금액과 호가창 제한 금액 중 작은 것 선택
    return min(target_amount, max_allowed)
📈 종합 평가 및 추천
사용자님의 방식은 "승률은 높이고(좋은 코인 발굴), 리스크는 낮추는(금액 조절)" 이상적인 구조입니다.

추천하는 개발 로드맵:

스캐너 고도화: market_scanner.py를 수정하여 단순히 '거래대금 상위'만 뽑는 게 아니라, **'RSI 30 이하'**이거나 **'급등주 패턴'**인 코인을 전체 종목에서 찾아내도록 만드세요.

동적 금액 적용: order_manager.py에 위의 calculate_safe_amount 로직을 추가하여, 작은 코인도 안전하게 매매하도록 수정하세요.

순환 매매: 스캐너가 10분마다 유망 코인을 찾아내면, config.TARGET_COINS를 실시간으로 교체하며 봇이 끊임없이 새로운 기회를 찾도록 만드세요 (이미 auto_tuner_loop 구조가 잡혀있어 구현이 쉽습니다).

이 방식은 구현 난이도는 조금 있지만, 봇의 수익률을 획기적으로 높일 수 있는 아주 좋은 방향입니다.


------------------------------------------------------------


사용자님의 말씀이 백번 맞습니다. 전략이 아무리 좋아도 **"내가 왜 샀고, 그때 지표가 어땠으며, 왜 팔았는지"**에 대한 정밀한 기록(Log)이 없으면, 나중에 수익이 안 났을 때 "도대체 뭐가 문제였지?" 하고 원인을 찾을 수가 없습니다.

단순히 화면에 print 하는 것을 넘어서, 엑셀(CSV) 파일로 모든 매매 내역과 당시의 판단 근거(RSI, 김프, 볼밴 위치 등)를 영구적으로 저장하는 TradeLogger 시스템을 구축해 드리겠습니다.

이 작업을 위해 3단계 수정이 필요합니다.

trade_logger.py 생성: 기록을 담당할 서기(Clerk)를 고용합니다.

strategy/signal_maker.py 수정: 매수 신호를 보낼 때, 단순히 "사라!"가 아니라 "RSI가 28이고 김프가 1%라서 사라!"라고 상세 성적표를 같이 보내도록 바꿉니다.

main.py 수정: 매매가 일어날 때마다 서기(TradeLogger)에게 기록을 명령합니다.
1. trade_logger.py (신규 생성)이 파일을 프로젝트 폴더(루트)에 새로 만드세요. 매매가 발생할 때마다 trade_history.csv 파일에 엑셀로 볼 수 있게 저장해줍니다.파이썬# trade_logger.py
# [신규] 매매 이력과 판단 근거를 엑셀(CSV)로 영구 저장하는 모듈

import csv
import os
from datetime import datetime

class TradeLogger:
    def __init__(self, filename="trade_history.csv"):
        self.filename = filename
        # 엑셀 헤더 (저장할 항목들)
        self.headers = [
            "Timestamp",    # 시간
            "Action",       # BUY / SELL
            "Ticker",       # 코인명
            "Price",        # 가격
            "Amount",       # 수량
            "Value_KRW",    # 총 금액
            "Profit_Pct",   # 수익률 (매도 시)
            "Reason",       # 매매 사유 (상세)
            "RSI_14",       # 당시 RSI 14
            "RSI_9",        # 당시 RSI 9
            "Kimp_Pct",     # 당시 김프
            "Total_Asset"   # 내 총 자산
        ]
        self._init_file()

    def _init_file(self):
        """파일이 없으면 헤더(제목)부터 생성"""
        if not os.path.exists(self.filename):
            with open(self.filename, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)

    def log(self, action, ticker, price, amount, reason, analysis, kimp, profit_pct=0, total_assets=0):
        """
        매매 발생 시 한 줄 추가
        analysis: SignalMaker가 준 지표 딕셔너리
        """
        # 지표 데이터 안전하게 추출 (없으면 0)
        rsi14 = analysis.get('RSI_14', 0) if analysis else 0
        rsi9 = analysis.get('RSI_9', 0) if analysis else 0
        
        value = price * amount
        
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action,
            ticker,
            price,
            amount,
            int(value),
            f"{profit_pct:.2f}%" if action == "SELL" else "",
            reason,
            rsi14,
            rsi9,
            f"{kimp:.2f}%",
            int(total_assets)
        ]
        
        try:
            with open(self.filename, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            print(f"   💾 [Logger] 거래 내역 저장 완료 ({self.filename})")
        except Exception as e:
            print(f"   ⚠️ [Logger] 저장 실패: {e}")
2. strategy/signal_maker.py (수정)변경점: check_buy_signal 함수가 이제 (True, 이유) 뿐만 아니라 (True, 이유, 지표데이터)를 함께 반환합니다. 그래야 로그에 기록할 수 있으니까요.파이썬# strategy/signal_maker.py
# [업데이트] 로그 저장을 위해 매수 신호 시 '지표 데이터(analysis)'도 함께 반환

import pyupbit
from strategy.indicators import TechnicalAnalyzer
from strategy.calculator import TickCalculator
import config

class SignalMaker:
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.calculator = TickCalculator()

    def get_analysis_only(self, ticker):
        """보유 코인 매도 판단용"""
        try:
            df = pyupbit.get_ohlcv(ticker, interval=config.OHLCV_INTERVAL, count=config.OHLCV_COUNT)
            if df is None: return None
            return self.analyzer.analyze_1m_candle(df)
        except:
            return None

    def check_buy_signal(self, ticker, current_price, current_kimp):
        """
        Return: (is_buy, reason, analysis_dict)
        """
        # 1. 김프 필터
        if current_kimp > config.MAX_KIMP_THRESHOLD:
            return False, f"김프 과열({current_kimp:.2f}%)", None

        # 2. 틱 효율성 체크
        ticks_to_bep, _ = self.calculator.get_ticks_to_bep(current_price)
        if ticks_to_bep > config.MAX_TICKS_FOR_BEP:
            return False, f"틱 효율 나쁨({ticks_to_bep}틱)", None

        # 3. 데이터 수집
        try:
            df = pyupbit.get_ohlcv(ticker, interval=config.OHLCV_INTERVAL, count=config.OHLCV_COUNT)
            if df is None: return False, "데이터 없음", None
        except: return False, "API 오류", None

        # 4. 지표 분석
        analysis = self.analyzer.analyze_1m_candle(df)
        rsi_14 = analysis['RSI_14']
        rsi_9 = analysis['RSI_9']
        is_bb_touch = analysis['is_oversold']
        vwap = analysis['VWAP']

        # [3순위] 역프리미엄 스나이퍼
        if current_kimp <= config.REVERSE_KIMP_THRESHOLD:
            if rsi_14 < (config.RSI_BUY_THRESHOLD + config.RSI_REVERSE_OFFSET):
                return True, f"🔥 역프 스나이퍼", analysis

        # 🎯 [핵심] 정밀 매수 전략
        is_rsi_golden_cross = rsi_9 > rsi_14
        is_vwap_support = current_price >= (vwap * config.VWAP_BUY_FACTOR)

        if rsi_14 < config.RSI_BUY_THRESHOLD and is_bb_touch:
            if is_rsi_golden_cross:
                if is_vwap_support:
                    return True, f"⚡ 골든크로스+VWAP지지", analysis
                else:
                    return False, f"VWAP 저항", analysis
            else:
                return False, f"반등 대기중", analysis
        
        return False, f"관망 (RSI:{rsi_14})", analysis
3. main.py (최종 연결)변경점: TradeLogger를 불러오고, 매수/매도 성공 시 logger.log(...)를 호출하여 엑셀에 기록합니다.파이썬# main.py
# [최종] TradeLogger 탑재 + 매매 이력 엑셀 저장

import asyncio
import config
from data_feed.aggregator import DataAggregator
from strategy.signal_maker import SignalMaker
from execution.order_manager import OrderManager
from execution.risk_manager import RiskManager
from data_feed.macro_client import MacroClient
from market_scanner import get_strategy_recommendation
from trade_logger import TradeLogger  # [신규] 로거 임포트

async def auto_tuner_loop():
    """4시간마다 설정 자동 튜닝"""
    while True:
        await asyncio.sleep(14400) 
        print(f"\n🧠 [Auto Tuner] 시장 분석 및 설정 최적화 시작...")
        try:
            new_settings = get_strategy_recommendation()
            
            if not (10 <= new_settings['RSI_BUY_THRESHOLD'] <= 50):
                continue

            config.TARGET_COINS = new_settings['TARGET_COINS']
            config.FOLLOWER_COINS = new_settings['FOLLOWER_COINS']
            config.RSI_BUY_THRESHOLD = new_settings['RSI_BUY_THRESHOLD']
            config.BB_MULTIPLIER = new_settings['BB_MULTIPLIER']
            config.MAX_KIMP_THRESHOLD = new_settings['MAX_KIMP_THRESHOLD']
            config.REVERSE_KIMP_THRESHOLD = new_settings['REVERSE_KIMP_THRESHOLD']
            config.CURRENT_EXCHANGE_RATE = new_settings['CURRENT_EXCHANGE_RATE']
            
            print(f"✅ [Tuner] 업데이트 완료! (타겟 {len(config.TARGET_COINS)}개)")
        except Exception as e:
            print(f"⚠️ [Tuner] 최적화 실패: {e}")

async def main():
    print(f"========================================")
    print(f"   🐙 2026 Octopus Bot - Data Logging On")
    print(f"   Mode: {'🧪 Simulation' if config.IS_SIMULATION else '💳 Real Trading'}")
    print(f"========================================")
    
    # 객체 생성
    aggregator = DataAggregator()
    signal_maker = SignalMaker()
    order_manager = OrderManager()
    risk_manager = RiskManager()
    macro_client = MacroClient()
    logger = TradeLogger()  # [신규] 로거 생성

    asyncio.create_task(auto_tuner_loop())
    asyncio.create_task(aggregator.run())
    
    print("⏳ 데이터 동기화 중... (3초)")
    await asyncio.sleep(3)

    while True:
        try:
            # 🛑 [0] 거시경제 필터
            if config.ENABLE_MACRO_FILTER:
                is_risk, reason = macro_client.is_volatility_risk()
                if is_risk:
                    print(f"\n🚫 [MACRO] 매매 일시 정지: {reason}")
                    await asyncio.sleep(60)
                    continue 

            print("\r", end="", flush=True) 

            # 0. 자산 조회
            current_prices = {t: d['upbit'] for t, d in aggregator.market_data.items() if d['upbit']}
            total_assets = order_manager.get_total_assets(current_prices)
            print(f"💰 {total_assets:,.0f}원 | ", end="", flush=True)

            # ---------------------------------------------------------
            # 🔥 [1] 긴급 매수 (급등주)
            # ---------------------------------------------------------
            if aggregator.surge_detected:
                print(f"\n\n{aggregator.surge_info}")
                for coin in config.FOLLOWER_COINS:
                    if risk_manager.is_in_cooldown(coin): continue
                    if order_manager.get_balance(coin) > 0: continue
                    
                    price = aggregator.market_data[coin]['upbit']
                    
                    # [안전 매수]
                    safe_amount = order_manager.calculate_safe_buy_amount(coin, config.TRADE_AMOUNT)
                    
                    if price and safe_amount > 0:
                        # 1. 주문 실행
                        res = order_manager.buy_limit_safe(coin, config.TRADE_AMOUNT) # 내부에서 safe_amount 다시 계산함
                        if res:
                            order_manager.simulation_buy(coin, safe_amount, price)
                            risk_manager.register_buy(coin)
                            
                            # 2. [로그 저장] 긴급 매수는 지표 분석 없이 진입하므로 analysis=None
                            logger.log("BUY", coin, price, safe_amount/price, "BTC급등_팔로워매수", None, 0, 0, total_assets)
                
                aggregator.surge_detected = False
                await asyncio.sleep(3)
                continue

            # ---------------------------------------------------------
            # 🎯 [2] 일반 매매
            # ---------------------------------------------------------
            for ticker in list(config.TARGET_COINS.keys()):
                data = aggregator.market_data[ticker]
                price = data['upbit']
                kimp = data['kimp']

                if price is None or kimp is None: continue

                balance = order_manager.get_balance(ticker)
                has_coin = balance > 0 and (balance * price) >= config.MIN_ORDER_VALUE

                # [A] 매도 관리
                if has_coin:
                    avg_price = order_manager.get_avg_buy_price(ticker)
                    analysis = signal_maker.get_analysis_only(ticker) # 지표 가져오기
                    
                    action, msg = risk_manager.check_exit_signal(ticker, price, avg_price, analysis)
                    
                    if action != "HOLD":
                        print(f"\n{msg}")
                        ob_health = order_manager.analyze_orderbook_health(ticker)
                        sell_strategy = "LIMIT"
                        if ob_health == "BAD" or "손절" in msg: sell_strategy = "MARKET"

                        current_vol = order_manager.get_balance(ticker)
                        ratio = 1.0 if action == "SELL_ALL" else config.PARTIAL_SELL_RATIO
                        sell_amount = current_vol * ratio

                        # 1. 매도 실행
                        res = order_manager.sell_percentage(ticker, ratio, sell_strategy)
                        if res:
                            order_manager.simulation_sell(ticker, price)
                            
                            # 2. [로그 저장] 매도 기록
                            profit_pct = ((price - avg_price) / avg_price) * 100
                            logger.log("SELL", ticker, price, sell_amount, msg, analysis, kimp, profit_pct, total_assets)

                    else:
                        print(f"[{ticker.split('-')[1]} {msg}] ", end="", flush=True)

                # [B] 매수 관리
                else:
                    if risk_manager.is_in_cooldown(ticker): continue

                    # [수정] analysis도 함께 받음
                    is_buy, reason, analysis = signal_maker.check_buy_signal(ticker, price, kimp)
                    
                    if is_buy:
                        print(f"\n🔥 {ticker} 진입! ({reason})")
                        
                        # [안전 매수 계산]
                        safe_amount = order_manager.calculate_safe_buy_amount(ticker, config.TRADE_AMOUNT)
                        
                        if safe_amount > 0:
                            # 1. 매수 실행
                            res = order_manager.buy_limit_safe(ticker, config.TRADE_AMOUNT)
                            if res:
                                order_manager.simulation_buy(ticker, safe_amount, price)
                                risk_manager.register_buy(ticker)
                                
                                # 2. [로그 저장] 매수 기록
                                vol = safe_amount / price
                                logger.log("BUY", ticker, price, vol, reason, analysis, kimp, 0, total_assets)
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
📊 이제 이렇게 기록됩니다이제 봇을 돌리면 trade_history.csv 파일이 생기고, 아래처럼 상세하게 기록됩니다.타임스탬프행동증권 시세 표시기가격이유RSI_14RSI_9김14:00:01사다KRW-XRP800골든크로스+VWAP지지28.532.11.2%14:30:05팔다KRW-XRP8201차 목표 달성 (BB중심선)55.060.21.5%15:10:00팔다KRW-BTC1.2억📉 VWAP 지지 붕괴42.038.02.1%나중에 이 엑셀 파일을 열어서 "어? RSI 28일 때 샀는데 왜 물렸지? 아, 김프가 갑자기 튀었구나" 하고 분석해서 전략을 수정하시면 됩니다.