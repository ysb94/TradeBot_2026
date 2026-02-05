# aggregator.py
# asyncio를 사용하여 업비트와 바이낸스의 웹소켓을 **병렬(동시)**로 연결하고, 데이터가 들어올 때마다 즉시 김프를 계산
#
import asyncio
import json
import websockets
from config import CURRENT_EXCHANGE_RATE, TARGET_COINS

class DataAggregator:
    def __init__(self):
        # 다중 종목 데이터 저장소 초기화
        # 구조: { "KRW-BTC": {"upbit": 0, "binance": 0, "kimp": 0}, ... }
        self.market_data = {
            ticker: {"upbit": None, "binance": None, "kimp": None} 
            for ticker in TARGET_COINS.keys()
        }
        
        # 바이낸스 심볼 역참조용 (btcusdt -> KRW-BTC 찾기 위해)
        self.binance_map = {v: k for k, v in TARGET_COINS.items()}

    async def connect_upbit(self):
        """업비트: 여러 종목 한 번에 구독"""
        uri = "wss://api.upbit.com/websocket/v1"
        target_codes = list(TARGET_COINS.keys()) # ["KRW-BTC", "KRW-SOL", ...]

        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    subscribe_fmt = [
                        {"ticket": "octopus-bot"},
                        {"type": "ticker", "codes": target_codes}
                    ]
                    await websocket.send(json.dumps(subscribe_fmt))
                    print(f"✅ [Upbit] 5개 종목 구독 완료: {target_codes}")

                    while True:
                        data = await websocket.recv()
                        data = json.loads(data)
                        code = data['code']
                        price = float(data['trade_price'])
                        
                        # 데이터 업데이트
                        self.market_data[code]['upbit'] = price
                        self.calculate_kimp(code)
                        
            except Exception as e:
                print(f"⚠️ [Upbit] Error: {e}")
                await asyncio.sleep(2)

    async def connect_binance(self):
        """바이낸스: Combined Stream으로 여러 종목 한 번에 구독"""
        # 스트림 형식: streamname1/streamname2/...
        streams = "/".join([f"{sym}@ticker" for sym in TARGET_COINS.values()])
        uri = f"wss://stream.binance.com:9443/stream?streams={streams}"
        
        while True:
            try:
                print(f"✅ [Binance] 다중 스트림 연결 시도...")
                async with websockets.connect(uri) as websocket:
                    print("✅ [Binance] 연결 성공!")
                    
                    while True:
                        resp = await websocket.recv()
                        resp = json.loads(resp)
                        # resp 구조: {"stream": "btcusdt@ticker", "data": {...}}
                        
                        stream_name = resp['stream'] # 예: btcusdt@ticker
                        symbol = stream_name.split('@')[0] # btcusdt
                        price = float(resp['data']['c']) # 현재가
                        
                        # 해당 심볼의 업비트 코드 찾기
                        if symbol in self.binance_map:
                            upbit_code = self.binance_map[symbol]
                            self.market_data[upbit_code]['binance'] = price
                            self.calculate_kimp(upbit_code)
                            
            except Exception as e:
                print(f"⚠️ [Binance] Error: {e}")
                await asyncio.sleep(2)

    def calculate_kimp(self, code):
        """개별 코인 김프 계산"""
        u_price = self.market_data[code]['upbit']
        b_price = self.market_data[code]['binance']

        if u_price and b_price:
            b_krw = b_price * CURRENT_EXCHANGE_RATE
            kimp = ((u_price - b_krw) / b_krw) * 100
            self.market_data[code]['kimp'] = kimp

    async def run(self):
        await asyncio.gather(
            self.connect_upbit(),
            self.connect_binance()
        )