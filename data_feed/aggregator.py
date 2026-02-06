# data_feed/aggregator.py
# [최종] 동적 설정 변경(Dynamic Config) 자동 감지 및 재연결 기능 탑재

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

    async def connect_upbit(self):
        """업비트 웹소켓 (설정 변경 자동 감지)"""
        uri = "wss://api.upbit.com/websocket/v1"
        
        while True:
            try:
                # 1. 루프 시작 시점의 최신 타겟 가져오기
                current_target_keys = list(config.TARGET_COINS.keys())
                
                # 2. Market Data 딕셔너리 동기화 (없는 키 추가)
                for ticker in current_target_keys:
                    if ticker not in self.market_data:
                        self.market_data[ticker] = {"upbit": None, "binance": None, "kimp": None}
                        print(f"➕ [Aggregator] 신규 감시 추가: {ticker}")

                async with websockets.connect(uri) as websocket:
                    subscribe_fmt = [
                        {"ticket": "octopus-bot"},
                        {"type": "ticker", "codes": current_target_keys}
                    ]
                    await websocket.send(json.dumps(subscribe_fmt))
                    print(f"✅ [Upbit] 구독 시작 ({len(current_target_keys)}개 종목)")

                    while True:
                        data = await websocket.recv()
                        data = json.loads(data)
                        code = data['code']
                        price = float(data['trade_price'])
                        
                        # 삭제된 코인 데이터가 들어오면 무시
                        if code not in config.TARGET_COINS: continue
                        
                        self.market_data[code]['upbit'] = price
                        self.calculate_kimp(code)
                        
                        # 🔥 [핵심] 설정 변경 감지 (타겟 개수가 달라지면 재접속)
                        if len(current_target_keys) != len(config.TARGET_COINS):
                            print("🔄 [Upbit] 타겟 변경 감지 -> 재구독 시도")
                            break # 내부 루프 탈출 -> 바깥 루프에서 재접속

            except Exception as e:
                print(f"⚠️ [Upbit] Error: {e}")
                await asyncio.sleep(2)

    async def connect_binance(self):
        """바이낸스 웹소켓 (설정 변경 자동 감지)"""
        while True:
            try:
                # 1. 최신 타겟 및 스트림 주소 생성
                current_symbols = list(config.TARGET_COINS.values())
                streams = "/".join([f"{sym}@ticker" for sym in current_symbols])
                uri = f"wss://stream.binance.com:9443/stream?streams={streams}"
                
                # 2. 맵핑 업데이트
                self.binance_map = {v: k for k, v in config.TARGET_COINS.items()}

                print(f"✅ [Binance] 리더-팔로워 엔진 가동 ({len(current_symbols)}개)")
                
                async with websockets.connect(uri) as websocket:
                    while True:
                        resp = await websocket.recv()
                        resp = json.loads(resp)
                        
                        stream_name = resp['stream'] 
                        symbol = stream_name.split('@')[0]
                        price = float(resp['data']['c'])
                        
                        # 데이터 업데이트
                        if symbol in self.binance_map:
                            upbit_code = self.binance_map[symbol]
                            # 삭제된 코인이면 스킵
                            if upbit_code in self.market_data:
                                self.market_data[upbit_code]['binance'] = price
                                self.calculate_kimp(upbit_code)

                        # BTC 급등 감지
                        if symbol == "btcusdt":
                            self.detect_btc_surge(price)
                        
                        # 🔥 [핵심] 설정 변경 감지
                        if len(current_symbols) != len(config.TARGET_COINS):
                            print("🔄 [Binance] 타겟 변경 감지 -> 재구독 시도")
                            break # 재접속

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