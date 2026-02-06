✅ 1단계: 기록 시스템 구축 (Data Logging)
목표: 매매가 왜 일어났는지, 결과는 어떤지 엑셀로 남겨서 전략을 검증할 수 있게 만듭니다. (가장 시급함)

[ ] 1-1. 서기 고용 (trade_logger.py 생성)

제공해주신 TradeLogger 클래스 코드로 파일 생성.

CSV 파일 생성 및 헤더(Timestamp, Action, RSI 등) 설정 확인.

[ ] 1-2. 성적표 발행 (strategy/signal_maker.py 수정)

check_buy_signal 함수가 단순히 True/False만 리턴하는 게 아니라, 당시의 지표 값(analysis 딕셔너리)을 함께 리턴하도록 수정.

[ ] 1-3. 업무 지시 (main.py 수정)

main.py에 logger 인스턴스 생성.

매수/매도 성공 시 logger.log()를 호출하여 기록 남기기.

🛡️ 2단계: 안전장치 강화 (Dynamic Sizing)
목표: 작은 코인에 큰돈이 들어가서 물리거나, 슬리피지로 손해 보는 것을 방지합니다.

[ ] 2-1. 이중 안전장치 탑재 (execution/order_manager.py 수정)

calculate_safe_buy_amount함수 추가 (자산 25% 룰 + 호가창 10% 룰).

buy_limit_safe 함수에서 무조건 설정값(TRADE_AMOUNT)을 쓰지 않고, 위 함수로 계산된 '안전 금액'을 사용하도록 변경.

[ ] 2-2. 설정값 정리 (config.py 확인)

SIMULATION_BALANCE등이 제대로 설정되어 있는지 확인.

👁️ 3단계: 호가창 속임수 판독 (Advanced Tape Reading)
목표: 단순 잔량 비율이 아니라, **"실제 체결 속도"**를 보고 세력의 의도를 파악합니다.

[ ] 3-1. 데이터 수신 채널 확장 (data_feed/aggregator.py 수정)

업비트 웹소켓 구독 요청 시, 기존 ticker 타입 외에 trade (체결 내역) 타입 추가.

실시간으로 들어오는 체결 데이터를 저장할 구조(self.trade_history) 마련.

[ ] 3-2. 체결 속도 분석기 구현 (execution/order_manager.py 고도화)

"최근 1초 동안 매수 체결이 얼마나 일어났는가?"를 계산하는 로직 추가.

매수벽이 두꺼운데 체결은 안 되고 있다면 **'허매수'**로 판단하는 로직 구현.

🔍 4단계: 종목 발굴 자동화 (Funnel Filtering)
목표: 소수의 지정된 코인만 보는 게 아니라, 시장 전체에서 기회를 포착합니다.

[ ] 4-1. 광범위 스캐너 개발 (market_scanner.py 업그레이드)

업비트 원화 마켓 전 종목(100+개)을 대상으로 1차 스캔.

거래대금 + RSI 과매도 + 볼린저 밴드 하단 조건을 만족하는 후보군 추출.

[ ] 4-2. 자동 타겟 변경 (Dynamic Targeting)

main.py의 auto_tuner_loop가 스캐너의 결과를 받아와서 config.TARGET_COINS를 실시간으로 갈아끼우도록 연동.
