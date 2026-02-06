import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# [1. 기본 설정]
# 2026-02-06 시장 진단: 환율 1,465원 반영
CURRENT_EXCHANGE_RATE = 1465.09 

# 🐙 [다중 종목 감시 설정 - 거래대금 상위 주도주 위주]
# 업비트 티커 : 바이낸스 웹소켓 심볼 (소문자 필수)
TARGET_COINS = {
    # --- 오늘의 대장주 (Top Priority) ---
    "KRW-XRP": "xrpusdt",   # 거래대금 1위 (2.2조)
    "KRW-BTC": "btcusdt",
    "KRW-ETH": "ethusdt",
    
    # --- 변동성 상위 / 밈 코인 ---
    "KRW-SOL": "solusdt",
    "KRW-DOGE": "dogeusdt",
    
    # --- 급등/급락 포착 (스캐너 포착 종목) ---
    "KRW-AXS": "axsusdt",
    "KRW-ADA": "adausdt",
    "KRW-SXP": "sxpusdt",
    
    # 주의: 스캐너에 잡힌 'ENSO'가 'ENS(이더리움네임서비스)'라면 아래 주석 해제 사용
    # "KRW-ENS": "ensusdt",
}

# [2. 전략 설정]
RSI_PERIOD = 14

# 🔥 [핵심 변경] 극단적 공포장(지수 9)이므로 기준을 30 -> 25로 낮춤
# 개미들이 공포에 질려 던질 때만 줍습니다.
RSI_BUY_THRESHOLD = 25      

# 밴드폭을 2.0 -> 2.2로 넓혀서 휩소(속임수) 방지
BB_MULTIPLIER = 2.2         

# [추가됨] 틱 가치 필터 설정
# 본전(BEP)까지 가는데 15틱 이상 올라야 한다면 진입 금지
MAX_TICKS_FOR_BEP = 15

# [3. 리스크 관리]
# 김프가 +1.39%로 안정적이므로 5% 넘어가면 과열로 판단하고 매수 중단
MAX_KIMP_THRESHOLD = 5.0    
REVERSE_KIMP_THRESHOLD = -1.0 # 역프 -1.0% 도달 시 강력 매수

STOP_LOSS_PCT = -1.5        # -1.5% 손절 (변동성 장세라 짧게)
TAKE_PROFIT_PCT = 1.0       # 1.0% 익절

# [4. 주문 및 API 설정]
# ⚠️ 주의: 실전 매매를 원하시면 True를 False로 변경하세요!
IS_SIMULATION = False  
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")
TRADE_AMOUNT = 6000   # 1회 진입 금액 (원)

# -----------------------------------------------------s
# [5. 바이낸스 리더-팔로워 설정]
# -----------------------------------------------------
# 공포장에서는 급등이 짧게 끝날 수 있으므로 기준 유지 (0.3%)
BINANCE_SURGE_THRESHOLD = 0.3 

# BTC가 튀면 따라갈 녀석들 (오늘 거래량 터진 놈들 순서)
FOLLOWER_COINS = ["KRW-XRP", "KRW-SOL", "KRW-ETH", "KRW-DOGE"]