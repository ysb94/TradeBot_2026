import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =========================================================
# [1. 시스템 및 API 설정]
# =========================================================
IS_SIMULATION = True  # 실전 여부 (True=가상매매)
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")

# 루프 딜레이 및 데이터 설정
LOOP_DELAY = 1              # 메인 루프 대기 시간 (초)
OHLCV_INTERVAL = "minute1"  # 캔들 조회 기준
OHLCV_COUNT = 200           # 캔들 조회 개수
MIN_ORDER_VALUE = 5005       # 최소 주문 가능 금액 (업비트 5000원 + 여유분)

# [가상 매매 설정]
SIMULATION_BALANCE = 1_000_000_000 # 모의 투자 시작 금액
# =========================================================
# [2. 타겟 및 자산 설정]
# =========================================================
CURRENT_EXCHANGE_RATE = 1465.09
TRADE_AMOUNT = 10_000_000  # 1회 진입 금액 (1억원)

# ✅ [신규] 리스크 관리 (Dynamic Sizing) 설정
MAX_ASSET_RATIO = 0.25     # 자산의 25%까지만 한 종목에 투자 (몰빵 방지)
MAX_OB_RATIO = 0.1         # 매도 잔량의 10%까지만 주문 (슬리피지 방지)

TARGET_COINS = {
    "KRW-XRP": "xrpusdt",
    "KRW-BTC": "btcusdt",
    "KRW-ETH": "ethusdt",
    "KRW-SOL": "solusdt",
    "KRW-DOGE": "dogeusdt",
    "KRW-AXS": "axsusdt",
    "KRW-ADA": "adausdt",
    "KRW-SXP": "sxpusdt",
}
FOLLOWER_COINS = ["KRW-XRP", "KRW-SOL", "KRW-ETH", "KRW-DOGE"]

# =========================================================
# [3. 지표 파라미터 (Indicators)]
# =========================================================
RSI_LONG_PERIOD = 14     # RSI 장기 (추세용)
RSI_SHORT_PERIOD = 9     # RSI 단기 (골든크로스용)
BB_PERIOD = 20           # 볼린저밴드 기간
BB_STD_DEV = 2           # 볼린저밴드 승수 (표준편차)

# =========================================================
# [4. 매수 전략 (Entry Strategy)]
# =========================================================
RSI_BUY_THRESHOLD = 30       # 매수 기준 RSI
BB_MULTIPLIER = 2.2          # (market_scanner 추천값 등)
MAX_TICKS_FOR_BEP = 15       # BEP 틱 제한
MAX_KIMP_THRESHOLD = 6.0     # 김프 제한
REVERSE_KIMP_THRESHOLD = -1.0 # 역프 기준

# 정밀 진입 조건
VWAP_BUY_FACTOR = 0.995      # VWAP * 0.995 이상일 때 지지로 판단
RSI_REVERSE_OFFSET = 10       # 역프일 때 RSI 완화 수치 (+10)

# =========================================================
# [5. 매도 및 리스크 관리 (Exit & Risk)]
# =========================================================
STOP_LOSS_PCT = -1.5         # 가격 손절 (%)
TRAILING_START = 0.5         # 트레일링 시작 (%)
TRAILING_DROP = 0.3          # 트레일링 낙폭 (%)

# 지표 손절 기준
VWAP_STOP_FACTOR = 0.99      # VWAP * 0.99 밑으로 깨지면 손절
RSI_PANIC_SELL = 15          # RSI가 이 값 밑으로 급락하면 투매로 간주

# 시간 손절 (Time Cut)
TIME_CUT_SECONDS = 180       # 진입 후 N초 경과 시 검사
TIME_CUT_MIN_PROFIT = 0.2    # N초 지났는데 수익이 이 값(%) 미만이면 종료

# 쿨타임 (재진입 금지 시간, 초)
COOLDOWN_STOP_LOSS = 3600    # 손절 후 1시간 휴식
COOLDOWN_VWAP_BREAK = 1800   # 지지 붕괴 시 30분 휴식
COOLDOWN_TIME_CUT = 600      # 시간 손절 시 10분 휴식

# 분할 익절 기준
PARTIAL_SELL_RATIO = 0.5     # 분할 매도 비율 (50%)
PARTIAL_SELL_MIN_PROFIT = 0.3 # 최소 0.3% 수익일 때만 분할 익절
RSI_SELL_THRESHOLD = 70      # 과매수 매도 기준

# =========================================================
# [6. 호가창 분석 (Orderbook)]
# =========================================================
OB_DEPTH_COUNT = 5           # 분석할 호가 단계 수 (1~5호가)
OB_BAD_RATIO = 3.0           # 매도벽이 매수벽의 3배면 나쁨 (시장가 매도)
OB_GOOD_RATIO = 2.0          # 매수벽이 매도벽의 2배면 좋음

# =========================================================
# [7. 기타 필터 (Macro & Binance)]
# =========================================================
BINANCE_SURGE_THRESHOLD = 0.3
ENABLE_MACRO_FILTER = True
PRE_EVENT_BUFFER = 30
POST_EVENT_BUFFER = 30
MANUAL_BLOCK_TIMES = [
#"2026-03-15 21:30",
    # 필요한 만큼 추가

# 수동 경재 캘린더
]


# =========================================================
# [8. AI 위원회 및 뉴스 API 설정] (신규 추가)
# =========================================================
# 1. API 키 (.env에서 로드)
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 2. 사용할 AI 모델 정의 (가성비 vs 성능)
MODEL_CHAIRMAN = "gpt-4o"            # 의장 (GPT-4o)
MODEL_BULL = "gemini-2.5-flash"     # 공격수 (Gemini Flash - 무료/저렴)
MODEL_BEAR = "claude-haiku-4-5" # 수비수 (Claude Haiku - 저렴)