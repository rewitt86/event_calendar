import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

def final_scraper():
    # 1. 구글 시트 API 인증 및 시트 연결
    print("🔐 구글 시트 인증을 시도합니다...")
    credentials_json = os.environ.get('GCP_CREDENTIALS')
    creds_dict = json.loads(credentials_json)
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # 요청하신 시트 ID와 탭(워크시트) 이름으로 정확히 연결
    SHEET_ID = '1-IkGfDd24o20QgN2rqmNOeHi4wjR_M0lEVRgsxwyyn4'
    sheet = client.open_by_key(SHEET_ID).worksheet('event_calendar')
    
    # 2. 데이터 크롤링
    url = "https://ko.tradingeconomics.com/united-states/calendar"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    cookies = {"calendar-importance": "3"} 

    print("🌐 데이터 수집 및 한국 시간(KST) 변환을 시작합니다...")
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        calendar_table = soup.find('table', id='calendar')
        
        if not calendar_table:
            print("❌ 'calendar' 테이블을 찾을 수 없습니다.")
            return

        rows = calendar_table.find_all('tr', attrs={'data-id': True})
        
        # 첫 줄에 들어갈 헤더(제목) 정의
        sheet_data = [["발표 일시", "지표명", "이전", "예측", "실제"]]

        for row in rows:
            cols = row.find_all('td', recursive=False)
            
            if len(cols) >= 7:
                time_col = cols[0]
                event_col = cols[2]
                
                time_span = time_col.find('span')
                impact_class = " ".join(time_span['class']) if time_span and time_span.has_attr('class') else ""
                
                if 'calendar-date-3' in impact_class:
                    date_text = time_col['class'][0] if time_col.has_attr('class') and len(time_col['class']) > 0 else ""
                    time_text = time_col.text.strip()
                    
                    final_date = date_text
                    final_time = time_text
                    
                    try:
                        dt_obj = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %I:%M %p")
                        kst_dt = dt_obj + timedelta(hours=9)
                        final_date = kst_dt.strftime("%Y-%m-%d")
                        final_time = kst_dt.strftime("%I:%M %p")
                    except ValueError:
                        pass
                    
                    time_formatted = f"[{final_date} | {final_time}]"
                    event_text = " ".join(event_col.text.split())
                    
                    actual_elem = row.find(id='actual')
                    actual_text = actual_elem.text.strip() if actual_elem else ""
                    
                    consensus_elem = row.find(id='consensus')
                    consensus_text = consensus_elem.text.strip() if consensus_elem else ""
                    
                    previous_elem = row.find(id='previous')
                    previous_text = previous_elem.text.strip() if previous_elem else ""
                    
                    # 구글 시트에 삽입할 데이터 행 추가
                    row_data = [time_formatted, event_text, previous_text, consensus_text, actual_text]
                    sheet_data.append(row_data)
                    
        print(f"🎉 총 {len(sheet_data) - 1}개의 핵심 지표 수집 완료!")

        # 3. 구글 시트 초기화 및 데이터 밀어넣기
        if len(sheet_data) > 1:
            print("🧹 기존 시트 데이터를 삭제합니다...")
            sheet.clear() 
            
            print("📝 새로운 데이터를 시트에 기록합니다...")
            sheet.append_rows(sheet_data)
            print("✅ 구글 시트 업데이트가 완벽하게 끝났습니다!")
        else:
            print("⚠️ 수집된 데이터가 없어 시트를 업데이트하지 않았습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    final_scraper()