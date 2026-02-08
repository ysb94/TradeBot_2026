
# data_feed/aggregator.py
# [최종] 동적 설정 감지 + [NEW] 실시간 체결(Trade) 데이터 수집

import asyncio
import json
import time
import websockets
from collections import deque
import config

class DataAggregator:
    def __init__(self):
        # 초기화 시점에만 config 참조 (이후 loop에서 갱신됨)
        self.market_data = {
            ticker: {"upbit": None, "binance": None, "kimp": None} 
            for ticker in config.TARGET_COINS.keys()
        }
        self.binance_map = {v: k for k, v in config.TARGET_COINS.items()}

        # BTC 급등 감지용
        self.btc_history = deque(maxlen=20) 
        self.surge_detected = False
        self.surge_info = ""

        # ✅ [신규] 체결 내역 저장소 (종목별 최근 100개 저장)
        self.trade_history = {
            ticker: deque(maxlen=100) 
            for ticker in config.TARGET_COINS.keys()
        }

    async def connect_upbit(self):
        """업비트 웹소켓 (Ticker + Trade 구독)"""
        uri = "wss://api.upbit.com/websocket/v1"
        
        while True:
            try:
                current_target_keys = list(config.TARGET_COINS.keys())
                
                # 딕셔너리 동기화
                for ticker in current_target_keys:
                    if ticker not in self.market_data:
                        self.market_data[ticker] = {"upbit": None, "binance": None, "kimp": None}
                    # ✅ [신규] 체결 저장소 동기화
                    if ticker not in self.trade_history:
                        self.trade_history[ticker] = deque(maxlen=100)

                async with websockets.connect(uri) as websocket:
                    subscribe_fmt = [
                        {"ticket": "octopus-bot"},
                        {"type": "ticker", "codes": current_target_keys},
                        {"type": "trade", "codes": current_target_keys} # ✅ [신규] 체결 내용 구독 추가
                    ]
                    await websocket.send(json.dumps(subscribe_fmt))
                    print(f"✅ [Upbit] Ticker & Trade 구독 시작 ({len(current_target_keys)}개)")

                    while True:
                        data = await websocket.recv()
                        data = json.loads(data)
                        code = data['code']
                        dtype = data['type'] # ticker or trade

                        if code not in config.TARGET_COINS: continue

                        # 1. 현재가(Ticker) 처리
                        if dtype == 'ticker':
                            price = float(data['trade_price'])
                            self.market_data[code]['upbit'] = price
                            self.calculate_kimp(code)
                        
                        # ✅ 2. [신규] 체결(Trade) 처리
                        elif dtype == 'trade':
                            # (시간, 가격, 볼륨, 매수/매도주체)
                            # ask_bid: ASK=매도체결(파란색), BID=매수체결(빨간색)
                            trade_info = {
                                'timestamp': time.time(),
                                'price': float(data['trade_price']),
                                'volume': float(data['trade_volume']),
                                'side': data['ask_bid'] 
                            }
                            self.trade_history[code].append(trade_info)
                        
                        # 설정 변경 감지 (타겟 개수 변경 시 재접속)
                        if len(current_target_keys) != len(config.TARGET_COINS):
                            print("🔄 [Upbit] 타겟 변경 감지 -> 재구독 시도")
                            break 

            except Exception as e:
                print(f"⚠️ [Upbit] Error: {e}")
                await asyncio.sleep(2)

    # ... (binance 및 기타 메서드는 기존과 동일하므로 유지) ...
    async def connect_binance(self):
        # (기존 코드 유지)
        while True:
            try:
                current_symbols = list(config.TARGET_COINS.values())
                streams = "/".join([f"{sym}@ticker" for sym in current_symbols])
                uri = f"wss://stream.binance.com:9443/stream?streams={streams}"
                self.binance_map = {v: k for k, v in config.TARGET_COINS.items()}
                print(f"✅ [Binance] 리더-팔로워 엔진 가동 ({len(current_symbols)}개)")
                async with websockets.connect(uri) as websocket:
                    while True:
                        resp = await websocket.recv()
                        resp = json.loads(resp)
                        stream_name = resp['stream'] 
                        symbol = stream_name.split('@')[0]
                        price = float(resp['data']['c'])
                        if symbol in self.binance_map:
                            upbit_code = self.binance_map[symbol]
                            if upbit_code in self.market_data:
                                self.market_data[upbit_code]['binance'] = price
                                self.calculate_kimp(upbit_code)
                        if symbol == "btcusdt":
                            self.detect_btc_surge(price)
                        if len(current_symbols) != len(config.TARGET_COINS):
                            break
            except Exception as e:
                print(f"⚠️ [Binance] Error: {e}")
                await asyncio.sleep(2)

    def detect_btc_surge(self, current_price):
        now = time.time()
        self.btc_history.append((now, current_price))
        prev_price = None
        while self.btc_history and self.btc_history[0][0] < now - 2.0:
            self.btc_history.popleft()
        if len(self.btc_history) > 1:
            prev_price = self.btc_history[0][1]
        if prev_price:
            change_rate = ((current_price - prev_price) / prev_price) * 100
            if change_rate >= config.BINANCE_SURGE_THRESHOLD:
                self.surge_detected = True
                self.surge_info = f"🚀 [LEADER] BTC 급등 감지! (+{change_rate:.2f}% in 1s)"

    def calculate_kimp(self, code):
        u_price = self.market_data[code]['upbit']
        b_price = self.market_data[code]['binance']
        if u_price and b_price:
            b_krw = b_price * config.CURRENT_EXCHANGE_RATE
            self.market_data[code]['kimp'] = ((u_price - b_krw) / b_krw) * 100

    async def run(self):
        await asyncio.gather(
            self.connect_upbit(),
            self.connect_binance()
        )