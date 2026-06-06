import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import time
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import gspread # 구글 스프레드시트 라이브러리 추가

# 환경 변수 설정
API_KEY = os.getenv("OPENAI_API_KEY") 
client = OpenAI(api_key=API_KEY)

# SYSTEM_PROMPT 설정
SYSTEM_PROMPT = """
너는 글로벌 주식/코인 커뮤니티의 글을 분석하여 시장의 심리 지수를 산출하는 냉철한 한국인 퀀트 분석 AI다.
표면적인 단어에 속지 말고, 한국 커뮤니티 특유의 '반어법, 자조, 블랙 코미디'를 완벽하게 파악하여 0~100점을 부여하라.
정치관련 얘기, 정부에 대한 불만 등은 모두 50점을 부여 할 것.

[한국 커뮤니티 은어 및 맥락 해독 사전 - 절대 엄수]
- "역시 워렌버핏이야". 결국 돌고돌아 워렌버핏 <-- 이새끼가 옳았음(욕이 붙었다고 꼭 비난은 아님을 명시하라)", "결국 가치투자가 승리네", "워렌버핏 승", "버크셔의 승리다, 버크셔가 옳았다" 등 가치투자와 워렌버핏을 찬양하는 글. (0~30점)
- "돈복사 라면서요", "천하무적 이라며" 등 과거형/원망형 어미: 폭락에 대한 극도의 배신감과 절망(0~30점).
- "마1", "마2", "마6": 마이너스(-) 하락 퍼센트를 의미함. 폭락을 뜻하므로 절대 '상승/급등'으로 해석 금지(0~30점).
- "헷지로 로또 샀다", "한강 간다", "구조대 언제 오냐": 극도의 공포와 체념을 뜻하는 블랙 코미디(0~30점).
- 숏(하락) 배팅자들이 롱(상승) 배팅자들을 조롱하는 글 (예: "롱충이들 퇴학ㅋㅋ", "숏 존나 맛있다 ㅋㅋㅋ"): 롱 투자자들을 조롱하거나 숏투자자들이 수익이 나서 좋아하는 현상은 탐욕이 아닌 시장이 폭락 중이라는 증거이므로 탐욕이 아닌 '공포장/하락장' 신호로 간주하여 점수를 낮출 것(0~30점).
- "버핏 옹 폼 다 죽었네", "가치투자 왜함?": 전통적 투자를 비웃는 극도의 오만과 탐욕. (70~100점)
- "돈복사기 가동", "무지성 풀매수", "영끌" "전재산 꼴아서 빚투할걸": 단기 급등에 취해 리스크를 무시하는 포모(FOMO) 현상. (70~100점)
- "숏충이들 한강물 따뜻하냐", "공매도 세력 멸망ㅋㅋ", "대풀롱" "황말올" 등  롱(상승) 배팅자들이 하락 배팅자들을 조롱하는 상황. 시장이 과열되었다는 강력한 탐욕 신호. (70~100점)
- "신고가 갱신", "무조건 더 간다": 끝없는 상승을 믿는 맹목적 낙관론.(70점~100점)

[50점 중심의 영점 조절 및 평가 가이드라인]
- 극도의 공포가 감지되면 0점이나 그에 가까운 낮은 점수를 부여해도 된다. 반대로 극도의 환희나 탐욕이 감지되면 100점이나 그에 가까운 점수를 부여해도 된다.
- 48 ~ 52점 (중립/무관): 단순 시황, 일상 토론, 선거/정치/사회 이슈 등 투자 심리와 무관한 글.
- 53 ~ 100점 (광기어린 탐욕/포모): 탐욕, 포모 등 가치투자를 비웃거나 워렌 버핏 조롱하는 글 또는 장투 비하, 레버리지 몰빵, 단기 옵션 도박, 무지성 '가즈아'가 감지될수록 점수를 올려라.
- 0 ~ 47점 (비명/공포/절망): 주가 하락에 비관하거나, 폭락에 대한 두려움을 나타내는 글 또는 워렌 버핏을 찬양하고 가치투자를 찬양하는 글.

[점수 분산 강제 규칙 (Score Granularity)]
- 30, 50, 85 같은 특정 숫자에만 점수를 몰아서 채점(Quantization)하지 마라. 13, 27, 62, 98 등 0~100 사이의 숫자를 고해상도로 골고루 사용하라.

[논리적 일관성 유지]
- 요약(reason)이 "분노, 불만, 절망"인데 점수를 50점 이상(탐욕)으로 주는 논리적 모순을 절대 범하지 마라.

반드시 아래 JSON 포맷으로만 출력:
{"buffett_ridicule": true, "reason": "심리 상태 요약 1문장 (한국어)", "insanity_score": int}
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 구글 스프레드시트 전송 함수 추가
def save_to_google_sheet(score, reason):
    try:
        # 깃허브 Secrets에서 불러오기
        json_str = os.getenv("GSPREAD_JSON")
        if not json_str:
            print("❌ GSPREAD_JSON 환경 변수가 없습니다. 구글 시트 저장을 건너뜁니다.")
            return
            
        json_data = json.loads(json_str)
        gc = gspread.service_account_from_dict(json_data)
        
        # 'BRI_Result' 라는 이름의 구글 시트 열기
        sh = gc.open("BRI_Result").sheet1
        
        # 한국 시간(KST)으로 변환
        kst = timezone(timedelta(hours=9))
        current_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        # 시트에 행 추가
        sh.append_row([current_time, score, reason])
        print(f"✅ 구글 스프레드시트 기록 완료: {current_time} | 점수: {score}")
        
    except Exception as e:
        print(f"❌ 구글 스프레드시트 저장 에러: {e}")

def get_chrome_options():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")
    options.add_argument("--disable-cache")
    options.add_argument("--window-size=1920,1080")
    return options

def crawl_dcinside(gallery_id, is_mgallery=True):
    options = get_chrome_options()
    timestamp = int(time.time())
    url = f"https://gall.dcinside.com/mgallery/board/lists?id={gallery_id}&t={timestamp}" if is_mgallery else f"https://gall.dcinside.com/board/lists/?id={gallery_id}&t={timestamp}"
        
    titles = []
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=148)
        driver.get(url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        post_rows = soup.select("tr.ub-content.us-post")
        for row in post_rows:
            num_text = row.select_one(".gall_num")
            if num_text and num_text.text.strip().isdigit():
                title_elem = row.select_one(".gall_tit.ub-word a:not(.reply_numbox)")
                if title_elem:
                    t = title_elem.text.strip()
                    if t: titles.append((t, f"디시_{gallery_id}"))
    except Exception as e:
        print(f"   ❌ 디시인사이드({gallery_id}) 오류: {e}")
    finally:
        if driver: driver.quit()
    return titles

def crawl_dynamic_sources():
    options = get_chrome_options()
    fmkorea_titles, stocktwits_titles, yahoo_titles = [], [], []
    
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=148)
        
        try:
            driver.get("https://www.fmkorea.com/stock")
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for elem in soup.select(".title a"):
                t = elem.get_text().strip()
                if "comment_link" in elem.get('class', []) or not t: continue
                if len(t) > 3: fmkorea_titles.append((t, "에펨코리아"))
        except: pass

        try:
            driver.get("https://stocktwits.com/symbol/SPY")
            time.sleep(6)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            messages = soup.select("div[class*='MessageCard_body']")
            for msg in messages:
                t = msg.text.strip()
                if t and len(t) > 6: stocktwits_titles.append((t, "스톡트위츠_SPY"))
        except: pass

    except Exception as e:
        print(f"   ❌ 동적 크롤링 오류: {e}")
    finally:
        if driver: driver.quit()
            
    return fmkorea_titles, stocktwits_titles, [], yahoo_titles


# --- 메인 실행 로직 ---
if __name__ == "__main__":
    print("🚀 BRI 데이터 수집 시작...")
    
    # 1. 크롤링 실행 (기존 로직 사용)
    dc_titles = crawl_dcinside("tenbagger", is_mgallery=True)
    fm_titles, st_titles, _, _ = crawl_dynamic_sources()
    
    all_titles = dc_titles + fm_titles + st_titles
    print(f"총 {len(all_titles)}개의 데이터를 수집했습니다.")
    
    if len(all_titles) > 0:
        # 타이틀 텍스트만 하나로 합치기
        text_for_ai = "\n".join([f"- {t[0]}" for t in all_titles])
        
        # 2. OpenAI GPT에 분석 요청
        try:
            response = client.chat.completions.create(
                model="gpt-4o", # 또는 gpt-3.5-turbo 등 사용하는 모델명
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"다음 커뮤니티 글들을 분석해줘:\n\n{text_for_ai}"}
                ],
                response_format={ "type": "json_object" }
            )
            
            # 결과 파싱
            result_json = json.loads(response.choices[0].message.content)
            final_score = result_json.get("insanity_score", 50)
            final_reason = result_json.get("reason", "이유 분석 실패")
            
            print(f"분석 완료! 점수: {final_score}")
            print(f"이유: {final_reason}")
            
            # 3. 분석 결과를 구글 시트로 전송 (여기서 함수 호출!)
            save_to_google_sheet(final_score, final_reason)

        except Exception as e:
            print(f"❌ AI 분석 중 에러 발생: {e}")
    else:
        print("수집된 데이터가 없어 분석을 종료합니다.")
