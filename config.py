# config.py
# 설정값 (API Key, 목표 수익률 등)

import os

try:
    from dotenv import load_dotenv

    load_dotenv()  # .env 로드 (프로젝트 루트의 .env)
except Exception:
    # python-dotenv 미설치/미사용 환경에서도 동작하게 둠
    pass



# 환율 설정 (추후 실시간 크롤링으로 대체 예정)
# 현재 대략적인 환율을 입력하세요 (예: 1450원)
CURRENT_EXCHANGE_RATE = 1450.0 

# 타겟 코인 설정 (일단 대장주 비트코인으로 테스트)
TARGET_COINS = {
    "KRW-BTC": "btcusdt",
    "KRW-ETH": "ethusdt",
    "KRW-SOL": "solusdt",
    "KRW-XRP": "xrpusdt",
    "KRW-DOGE": "dogeusdt"
}
# [전략 설정]
# 1. 기술적 지표 기준
RSI_PERIOD = 14
RSI_BUY_THRESHOLD = 80      # (기존 30 -> 70 수정)
BB_MULTIPLIER = 2.0         # 볼린저 밴드 승수

# 2. 김치 프리미엄 필터
MAX_KIMP_THRESHOLD = 10.0    # (기존 5.0 -> 10.0 수정)
REVERSE_KIMP_THRESHOLD = -1.0 # 역프(-1%) 발생 시 적극 매수

# 3. 리스크 관리
STOP_LOSS_PCT = -1.5        # -1.5% 도달 시 손절
TAKE_PROFIT_PCT = 1.0       # 1.0% 도달 시 익절


# [4. 주문 및 API 설정]
# 주의: 실제 돈을 쓰지 않으려면 True로 설정하세요.
IS_SIMULATION = True  # True: 모의투자(로그만 출력), False: 실전매매

# 업비트 API 키 (IS_SIMULATION = False 일 때만 사용됨)
# 업비트 웹사이트 > 마이페이지 > Open API 관리에서 발급
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")

# 1회 매수 금액 (KRW)
TRADE_AMOUNT = 6000 # 테스트용 6천원 (업비트 최소 주문금액 5천원)