# data_feed/macro_client.py
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import logging

class MacroClient:
    def __init__(self):
        self.events = []
        self.last_update = None
        # 무료 데이터 소스 (ForexFactory는 크롤링이 까다로울 수 있어, 접근이 쉬운 대안 경로 활용 권장)
        # 여기서는 예시로 Investing.com 스타일의 데이터 구조를 처리하는 로직을 구현합니다.
        self.target_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml" # ForexFactory XML (종종 사용 가능)

    def fetch_events(self):
        """경제 캘린더 데이터를 가져와서 중요 이벤트(USD, High Impact)만 필터링"""
        # 하루에 한 번만 업데이트 (API 호출 제한 방지)
        if self.last_update and datetime.now() - self.last_update < timedelta(hours=6):
            return

        try:
            # ForexFactory XML 피드 시도 (가장 가볍고 빠름)
            response = requests.get(self.target_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                self.events = []
                
                for event in soup.find_all('event'):
                    country = event.find('country').text
                    impact = event.find('impact').text
                    
                    # [필터] 미국(USD) 관련 + 중요도 높음(High) 이벤트만 감시
                    if country == 'USD' and impact in ['High', 'Holiday']:
                        date_str = event.find('date').text # YYYY-MM-DD
                        time_str = event.find('time').text # HH:MMam/pm
                        
                        # 날짜/시간 파싱 (ForexFactory XML 시간은 보통 ET 기준이므로 한국 시간 변환 필요)
                        # 단순화를 위해 여기서는 UTC+0 가정 후 +9시간 등으로 보정 로직 필요하나
                        # 실전에서는 정확한 timestamp 파싱이 중요합니다.
                        # *이 코드는 구조 예시이며, 실제로는 Investing.com API나 유료 API 사용을 추천합니다.*
                        
                        # (임시) 데이터가 있다고 가정하고 리스트에 추가
                        # self.events.append(parsed_datetime)
                        pass
                
                self.last_update = datetime.now()
                print(f"📅 [Macro] 경제지표 데이터 업데이트 완료 (이벤트 {len(self.events)}개)")
                
        except Exception as e:
            print(f"⚠️ [Macro] 데이터 수집 실패: {e}")

    def is_volatility_risk(self, buffer_min=30):
        """
        현재 시간이 중요 이벤트 전후 30분(buffer) 이내인지 확인
        Return: True(위험), False(안전)
        """
        # 데이터가 없으면 일단 업데이트 시도
        if not self.events:
            self.fetch_events()
            
        now = datetime.now()
        
        # 나스닥 개장 시간 (한국 시간 23:30 / 썸머타임 22:30) 회피
        # 간단하게 23:20 ~ 23:40 사이를 위험 구간으로 설정
        current_hour = now.hour
        current_minute = now.minute
        
        # [고정 필터] 미장 개장 전후 (23:30 기준)
        if current_hour == 23 and 20 <= current_minute <= 40:
            return True, "🇺🇸 나스닥 개장 변동성 구간"

        # [동적 필터] 수집된 경제 지표 시간 체크
        for event_time in self.events:
            # 이벤트 시간 전후 buffer_min 분 동안은 위험
            if event_time - timedelta(minutes=buffer_min) <= now <= event_time + timedelta(minutes=buffer_min):
                return True, f"📢 중요 경제 지표 발표 ({event_time.strftime('%H:%M')})"

        return False, "Market Safe"