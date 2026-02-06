# aggregator.py
# asyncio를 사용하여 업비트와 바이낸스의 웹소켓을 **병렬(동시)**로 연결하고, 데이터가 들어올 때마다 즉시 김프를 계산
#
import asyncio
import json
import time
import websockets
from collections import deque # [추가] 과거 데이터 저장용
import config

class DataAggregator:
    def __init__(self):
        self.market_data = {
            ticker: {"upbit": None, "binance": None, "kimp": None}
            for ticker in config.TARGET_COINS.keys()
        }
        self.binance_map = {v: k for k, v in config.TARGET_COINS.items()}

        # [리더-팔로워용] BTC 가격 기록 (시간, 가격)
        self.btc_history = deque(maxlen=20) 
        self.surge_detected = False # 급등 감지 플래그
        self.surge_info = ""        # 로그용 메시지

    async def connect_upbit(self):
        """업비트: 여러 종목 한 번에 구독"""
        uri = "wss://api.upbit.com/websocket/v1"
        target_codes = list(config.TARGET_COINS.keys())

        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    subscribe_fmt = [
                        {"ticket": "octopus-bot"},
                        {"type": "ticker", "codes": target_codes}
                    ]
                    await websocket.send(json.dumps(subscribe_fmt))
                    print(f"✅ [Upbit] 종목 구독 완료")

                    while True:
                        data = await websocket.recv()
                        data = json.loads(data)
                        code = data['code']
                        price = float(data['trade_price'])
                        
                        self.market_data[code]['upbit'] = price
                        self.calculate_kimp(code)
                        
            except Exception as e:
                print(f"⚠️ [Upbit] Error: {e}")
                await asyncio.sleep(2)

    async def connect_binance(self):
        """바이낸스: 리더(BTC) 감시 및 급등 포착"""
        streams = "/".join([f"{sym}@ticker" for sym in config.TARGET_COINS.values()])
        uri = f"wss://stream.binance.com:9443/stream?streams={streams}"
        
        while True:
            try:
                print(f"✅ [Binance] 리더-팔로워 엔진 가동 중...")
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
                            self.market_data[upbit_code]['binance'] = price
                            self.calculate_kimp(upbit_code)

                        # 🔥 [핵심] BTC(btcusdt) 급등 감지 로직
                        if symbol == "btcusdt":
                            self.detect_btc_surge(price)
                            
            except Exception as e:
                print(f"⚠️ [Binance] Error: {e}")
                await asyncio.sleep(2)

    def detect_btc_surge(self, current_price):
        """BTC 가격이 1초 전 대비 급등했는지 검사"""
        now = time.time()
        self.btc_history.append((now, current_price))

        # 1초 전 데이터 찾기 (약 1.0 ~ 1.5초 전)
        # deque에는 (시간, 가격) 튜플이 저장됨
        prev_price = None
        
        # 가장 오래된 데이터가 너무 옛날(2초 이상)이면 버림
        while self.btc_history and self.btc_history[0][0] < now - 2.0:
            self.btc_history.popleft()

        # 1초 전 데이터 조회 (없으면 가장 오래된 데이터 사용)
        if len(self.btc_history) > 1:
            prev_price = self.btc_history[0][1] # 약 1초 전 가격

        if prev_price:
            # 변동률 계산
            change_rate = ((current_price - prev_price) / prev_price) * 100
            
            # 급등 기준 초과 시 신호 발생
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