import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# [1. 기본 설정]
CURRENT_EXCHANGE_RATE = 1450.0 

# 🐙 [다중 종목 감시 설정 - 20개로 확대]
# 업비트 티커 : 바이낸스 웹소켓 심볼 (소문자 필수)
TARGET_COINS = {
    # --- 메이저 (대장주) ---
    "KRW-BTC": "btcusdt",
    "KRW-ETH": "ethusdt",
    "KRW-SOL": "solusdt",
    "KRW-XRP": "xrpusdt",
    "KRW-ADA": "adausdt",
    
    # --- 밈 코인 (변동성 최상) ---
    "KRW-DOGE": "dogeusdt",
    "KRW-SHIB": "shibusdt",
    "KRW-PEPE": "pepeusdt",
    
    # --- 레이어1 / 플랫폼 (거래량 상위) ---
    "KRW-AVAX": "avaxusdt",
    "KRW-TRX": "trxusdt",
    "KRW-DOT": "dotusdt",
    "KRW-LINK": "linkusdt",
    "KRW-ETC": "etcusdt",
    "KRW-BCH": "bchusdt",
    
    # --- 메타버스 / 게이밍 / AI ---
    "KRW-SAND": "sandusdt",
    "KRW-MANA": "manausdt",
    "KRW-NEAR": "nearusdt",
    "KRW-STX": "stxusdt",     # 비트코인 생태계
    "KRW-SUI": "suiusdt",     # 신규 메이저
    "KRW-SEI": "seiusdt"
}

# [2. 전략 설정]
RSI_PERIOD = 14
RSI_BUY_THRESHOLD = 80      # (테스트용: 80, 실전 추천: 30)
BB_MULTIPLIER = 2.0         


# [추가됨] 틱 가치 필터 설정
# 본전(BEP)까지 가는데 15틱 이상 올라야 한다면 진입 금지 (변동성 대비 효율 낮음)
MAX_TICKS_FOR_BEP = 15


# [3. 리스크 관리]
MAX_KIMP_THRESHOLD = 10.0    # (테스트용: 10%, 실전 추천: 5%)
REVERSE_KIMP_THRESHOLD = -1.0
STOP_LOSS_PCT = -1.5        # -1.5% 손절
TAKE_PROFIT_PCT = 1.0       # 1.0% 익절

# [4. 주문 및 API 설정]
IS_SIMULATION = True  # True: 모의투자, False: 실전매매
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")
TRADE_AMOUNT = 6000


# -----------------------------------------------------
# [5. 바이낸스 리더-팔로워 설정 (신규 추가)]
# -----------------------------------------------------
# 바이낸스 BTC가 "1초(또는 직전 틱)" 만에 이만큼 오르면 급등으로 판단
BINANCE_SURGE_THRESHOLD = 0.3 # 단위: % (0.3% 급등은 초단기적으로 매우 큰 수치임)

# BTC 급등 시 업비트에서 따라서 살 "추종자(Follower)" 코인들
# (베타 계수가 높고 반응 속도가 빠른 메이저 알트 추천)
FOLLOWER_COINS = ["KRW-SOL", "KRW-XRP", "KRW-DOGE", "KRW-ETH"]