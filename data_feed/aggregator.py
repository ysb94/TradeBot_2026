# aggregator.py
# asyncio를 사용하여 업비트와 바이낸스의 웹소켓을 **병렬(동시)**로 연결하고, 데이터가 들어올 때마다 즉시 김프를 계산
#
import asyncio
import json
import websockets
from config import CURRENT_EXCHANGE_RATE, TARGET_COIN_TICKER_UPBIT

class DataAggregator:
    def __init__(self):
        self.prices = {
            "upbit": None,
            "binance": None
        }
        self.kimchi_premium = None

    async def connect_upbit(self):
        """업비트 웹소켓 연결"""
        uri = "wss://api.upbit.com/websocket/v1"
        
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    subscribe_fmt = [
                        {"ticket": "test-bot"},
                        {"type": "ticker", "codes": [TARGET_COIN_TICKER_UPBIT]}
                    ]
                    await websocket.send(json.dumps(subscribe_fmt))
                    print("✅ [Upbit] WebSocket Connected")

                    while True:
                        data = await websocket.recv()
                        data = json.loads(data)
                        self.prices["upbit"] = float(data['trade_price'])
                        await self.update_dashboard()
                        
            except Exception as e:
                print(f"⚠️ [Upbit] Connection Error: {e}")
                await asyncio.sleep(2)

    async def connect_binance(self):
        """바이낸스 웹소켓 연결 (Raw Stream 사용 - CCXT 제거)"""
        # 바이낸스 BTC/USDT 실시간 티커 스트림 URL
        # symbol은 소문자로 써야 함 (btcusdt)
        uri = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
        
        while True:
            try:
                print("✅ [Binance] WebSocket Connecting...")
                async with websockets.connect(uri) as websocket:
                    print("✅ [Binance] WebSocket Connected")
                    
                    while True:
                        data = await websocket.recv()
                        data = json.loads(data)
                        
                        # 바이낸스 스트림 데이터에서 'c'는 현재가(Current Price)를 의미
                        if 'c' in data:
                            self.prices["binance"] = float(data['c'])
                            await self.update_dashboard()
                            
            except Exception as e:
                print(f"⚠️ [Binance] Connection Error: {e}")
                await asyncio.sleep(2)

    async def update_dashboard(self):
        """데이터 통합 및 김프 계산"""
        upbit_price = self.prices["upbit"]
        binance_price = self.prices["binance"]

        if upbit_price and binance_price:
            # 김프 계산
            binance_krw = binance_price * CURRENT_EXCHANGE_RATE
            self.kimchi_premium = ((upbit_price - binance_krw) / binance_krw) * 100
            
            # ▼▼▼ [수정] 이 부분 주석 처리 (#) 또는 삭제 ▼▼▼
            # print(f"\r[실시간] Upbit: {upbit_price:,.0f} KRW | "
            #       f"Binance: ${binance_price:,.2f} | "
            #       f"김프: {self.kimchi_premium:+.2f}%   ", end="", flush=True)
            pass

    async def run(self):
        await asyncio.gather(
            self.connect_upbit(),
            self.connect_binance()
        )