import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import time
import os
from datetime import datetime
import pandas as pd
import numpy as np
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_KEY = "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"
CSV_FILE_PATH = "global_buffett_ridicule_index.csv"

client = OpenAI(api_key=API_KEY)

# =====================================================================
# 1. 고해상도 초정밀 심리 분석 프롬프트
# =====================================================================
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
예시 : "지금 안 사면 벼락거지 됨", "무지성 롱 가즈아", "가치투자(버핏) 왜 함? 단타가 최고지" 등 상승장에 취해 도박적이고 오만한 태도를 보일 때. (강도에 따라 세밀하게 분산)
- 0 ~ 47점 (비명/공포/절망): 주가 하락에 비관하거나, 폭락에 대한 두려움을 나타내는 글 또는 워렌 버핏을 찬양하고 가치투자를 찬양하는 글.
예시 : 계좌 녹음, 손실 인증, 폭락에 대한 두려움, 장투의 후회, 하락장에서의 자조 섞인 농담. 앞으로 워렌 버핏 투자를 따라갈거다. 가치투자가 최고다., 아가리 쩌억 벌리고 매수 대기한다. (강도에 따라 세밀하게 분산)

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

def crawl_dcinside(gallery_id, is_mgallery=True):
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")
    options.add_argument("--disable-cache")

    timestamp = int(time.time())
    if is_mgallery:
        url = f"https://gall.dcinside.com/mgallery/board/lists?id={gallery_id}&t={timestamp}"
    else:
        url = f"https://gall.dcinside.com/board/lists/?id={gallery_id}&t={timestamp}"
        
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
                time_elem = row.select_one(".gall_date")
                if time_elem:
                    post_time = time_elem.get("title") or time_elem.text.strip()
                    if ":" not in post_time:
                        continue 
                        
                title_elem = row.select_one(".gall_tit.ub-word a:not(.reply_numbox)")
                if title_elem:
                    t = title_elem.text.strip()
                    if t: titles.append((t, f"디시_{gallery_id}"))
                    
    except Exception as e:
        print(f"   ❌ 디시인사이드({gallery_id}) 우회 오류: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
            
    return titles

def crawl_reddit(subreddit):
    url = f"https://old.reddit.com/r/{subreddit}/"
    titles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        title_elements = soup.select("p.title a.title")
        for elem in title_elements:
            t = elem.text.strip()
            if t: titles.append((t, f"레딧_{subreddit}"))
    except: pass
    return titles

def crawl_naver_finance(item_code="005930"):
    url = f"https://finance.naver.com/item/board.naver?code={item_code}"
    titles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        title_elements = soup.select(".title a")
        for elem in title_elements:
            t = elem.text.strip()
            if t: titles.append((t, "네이버_종토방"))
    except: pass
    return titles

def crawl_coinpan():
    url = "https://coinpan.com/free"
    titles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        title_elements = soup.select("td.title a")
        for elem in title_elements:
            t = elem.text.strip()
            if t: titles.append((t, "코인판"))
    except: pass
    return titles

def crawl_dynamic_sources():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")
    options.add_argument("--disable-cache")
    
    fmkorea_titles = []
    stocktwits_titles = []
    blind_titles = []
    yahoo_titles = []
    
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=148)
        
        # 1. 에펨코리아 주식판
        try:
            driver.get("https://www.fmkorea.com/stock")
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for elem in soup.select(".title a"):
                t = elem.get_text().strip()
                if "comment_link" in elem.get('class', []) or not t: continue
                if len(t) > 3: fmkorea_titles.append((t, "에펨코리아"))
        except: pass

        # 3. 스톡트위츠 (SPY)
        try:
            driver.get("https://stocktwits.com/symbol/SPY")
            time.sleep(6)
            driver.execute_script("""
                let nodes = document.querySelectorAll("[class*='modal'], [class*='signup'], [class*='register'], [class*='cookie'], [id*='cookie'], [class*='banner']");
                nodes.forEach(n => n.remove());
                document.body.style.overflow = 'auto';
            """)
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 600);")
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            messages = soup.select("div[class*='MessageCard_body']") or soup.select("[data-testid='message-body']") or soup.select("div[class*='body_']") or soup.select(".stream-list .message-item")
            for msg in messages:
                t = msg.text.strip()
                if t and len(t) > 6: stocktwits_titles.append((t, "스톡트위츠_SPY"))
        except Exception as e:
            print(f"   ❌ 스톡트위츠 우회 장애: {str(e)[:30]}")

        # 4. 야후 파이낸스 (QQQ ETF 타겟 정밀 분석형 관통 로직)
        try:
            target_url = "https://finance.yahoo.com/quote/QQQ/community/"
            driver.get(target_url)
            time.sleep(6) 
            
            if "consent" in driver.current_url or "guce" in driver.current_url:
                buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]")
                if buttons:
                    try:
                        buttons[0].click()
                        time.sleep(4)
                        driver.get(target_url)
                        time.sleep(6)
                    except: pass
            
            driver.execute_script("window.scrollTo(0, 1500);")
            time.sleep(5) 
            
            iframes = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'spotim') or contains(@name, 'spotim') or contains(@id, 'spotim')]")
            
            if iframes:
                driver.switch_to.frame(iframes[0])
                time.sleep(3)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(5)
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                driver.switch_to.default_content()
                
                comments = soup.select(
                    'div[data-spotim-module="message"] p, '
                    '[data-test="comment-body"], '
                    '[class*="RichTextElement"], '
                    'div.spcv_message-text'
                )
                
                for elem in comments:
                    t = elem.get_text(separator=' ', strip=True)
                    if t and len(t) > 5:
                        yahoo_titles.append((t, "야후파이낸스_QQQ"))
            else:
                print("   ⚠️ 야후 파이낸스: 댓글 Iframe을 찾을 수 없습니다. (UI 변경 또는 로딩 지연)")
                    
        except Exception as e:
            print(f"   ❌ 야후 파이낸스 우회 장애: {str(e)[:30]}")

    except Exception as e: pass
    finally:
        if driver:
            try: driver.quit()
            except: pass
            
    return fmkorea_titles, stocktwits_titles, blind_titles, yahoo_titles

def analyze_title_with_llm(title):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"분석할 글 제목: {title}"}
            ],
            temperature=0.4
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"buffett_ridicule": True, "reason": "오류", "insanity_score": 50}

if __name__ == "__main__":
    print("==================================================")
    print("🚀 글로벌 8대 커뮤니티 통합 버핏 조롱지수(BRI) 가동")
    print("==================================================")
    
    print("1. 미국 주식 마이너 갤러리(stockus) 수집 중...")
    dc_us = crawl_dcinside("stockus", is_mgallery=True)
    print("   -> 완료.")
    
    print("3. 국내 주식 마이너 갤러리(krstock) 수집 중...")
    dc_kr = crawl_dcinside("krstock", is_mgallery=True)
    print("   -> 완료.")
    
    print("4. 에펨코리아, 스톡트위츠, 야후 파이낸스 실시간 우회 크롤링 시작...")
    fmkorea, stocktwits, blind, yahoo = crawl_dynamic_sources()
    
    reddit = crawl_reddit("wallstreetbets")
    print("5. 레딧(WallStreetBets) 수집 완료.")
    naver = crawl_naver_finance("005930")
    print("6. 네이버 증권 종목토론방 수집 완료.")
    coinpan = crawl_coinpan()
    print("7. 코인판 자유게시판 수집 완료.")
    
    print("8. 스톡트위츠 스트림 융합 중...")
    print("9. 야후 파이낸스 메시지 보드 융합 중...")
    
    print("\n==================================================")
    print("🔍 [MATRIX ENGINE] 실시간 커뮤니티별 수집 현황 검증")
    print("==================================================")
    print(f"   - [디시 미주갤] 데이터 : {len(dc_us)}개")
    print(f"   - [디시 국주갤] 데이터 : {len(dc_kr)}개")
    print(f"   - [에펨코리아]  데이터 : {len(fmkorea)}개")
    print(f"   - [레딧 WSB]   데이터 : {len(reddit)}개")
    print(f"   - [네이버 종토]  데이터 : {len(naver)}개")
    print(f"   - [스톡트위츠]  데이터 : {len(stocktwits)}개")
    print(f"   - [코인판 자유]  데이터 : {len(coinpan)}개")
    print(f"   - [야후파이낸]  데이터 : {len(yahoo)}개")
    print("==================================================\n")
    
    all_collected_posts = []
    all_collected_posts.extend(dc_us)
    all_collected_posts.extend(dc_kr)
    all_collected_posts.extend(fmkorea)
    all_collected_posts.extend(reddit)
    all_collected_posts.extend(naver)
    all_collected_posts.extend(stocktwits)
    all_collected_posts.extend(coinpan)
    all_collected_posts.extend(yahoo)
    
    BLOCK_WORDS = [
        "공지", "안내", "규칙", "점검", "추천도서", "은어 길라잡이", "이용제한", 
        "블라인드", "이벤트", "서버 이전", "정책", "길라잡이", "이전 주식 갤러리", "새 주갤 주소"
    ]
    
    clean_posts = []
    for title, source in list(set(all_collected_posts)):
        title_strip = title.strip()
        if len(title_strip) <= 5 or title_strip.isdigit():
            continue
        if any(bw in title_strip for bw in BLOCK_WORDS):
            continue
        clean_posts.append((title_strip, source))
        
    all_collected_posts = clean_posts
    print(f"   -> 필터링을 거쳐 총 {len(all_collected_posts)}개의 고순도 유니크 데이터를 전수 분석 대상으로 확정했습니다.\n")
    
    if not all_collected_posts:
        os._exit(0)
        
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_to_save = []
    raw_scores = []
    
    print("11. 통합 데이터 대상 고도화 AI 전수 심리 분석 시작...")
    
    display_idx = 1
    total_display_len = len(all_collected_posts)
    
    for title, source in all_collected_posts:
        # 번호 규칙 적용 (2번 생략)
        if display_idx == 2:
            display_idx += 1
            
        result = analyze_title_with_llm(title)
        score = result.get("insanity_score", 50)
        reason = result.get("reason", "평온")
        raw_scores.append(score)
        
        if score >= 70:
            print(f"   [{display_idx}/{total_display_len}] [{source}] 📈 탐욕 감지({score}점) -> '{title[:30]}...' | {reason}")
        elif score <= 35:
            print(f"   [{display_idx}/{total_display_len}] [{source}] 📉 공포 감지({score}점) -> '{title[:30]}...' | {reason}")
        else:
            print(f"   [{display_idx}/{total_display_len}] [{source}] 분석 완료({score}점) -> '{title[:30]}...'")
            
        rows_to_save.append({
            "timestamp": current_timestamp,
            "source": source,
            "title": title,
            "buffett_ridicule": True,
            "reason": reason,
            "insanity_score": score
        })
        display_idx += 1
        time.sleep(0.08)
        
    # =====================================================================
    # 13. [v3.0] 비대칭 광기 증폭 및 스케일링 복원형 BRI 지수 산출 엔진
    # =====================================================================
    print("\n13. [UPGRADED] 시장 광기 가속도 반영 비선형 BRI 지수 산출 중...")

    # 1. raw_scores를 50점 기준 편차로 변환 (-50 ~ 50)
    deviations = np.array([s - 50 for s in raw_scores])
    
    # 3. 광기 증폭 가중치 부여 (비대칭)
    # 탐욕(양수)은 1.5배 증폭, 공포(음수)는 2.0배 증폭하여 공포 반응을 더 예민하게 설정
    weights = np.where(deviations > 0, 1.5, 2.0)
    
    # 4. 비선형 증폭 (편차의 제곱 적용)
    # 편차가 클수록 지수에 미치는 영향력을 기하급수적으로 키움
    amplified_deviations = deviations * np.abs(deviations) * weights
    
    # 5. 스케일링 및 최종 지수 산출 (오버플로우 방지)
    # 증폭된 평균값의 절대값에 루트를 씌워 원래 스케일로 압축하고 원래 부호를 다시 붙임
    mean_amp = np.mean(amplified_deviations)
    scaled_deviation = np.sign(mean_amp) * np.sqrt(np.abs(mean_amp))
    final_bri_index = 50 + scaled_deviation
    
    # 6. 하드캡핑 (0~100)
    final_bri_index = max(0, min(100, final_bri_index))

    print(f"   - 전수 분석 게시글: {len(raw_scores)}개")
    print(f"   - 📊 오늘의 고감도 BRI 지수: {final_bri_index:.2f} 포인트")
    
    new_df = pd.DataFrame(rows_to_save)
    if os.path.exists(CSV_FILE_PATH):
        existing_df = pd.read_csv(CSV_FILE_PATH)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
    else:
        new_df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
        
    print("📊 통합 데이터 축적 완료! 시스템이 정상적으로 종료되었습니다.")
    print("==================================================")
    os._exit(0)
