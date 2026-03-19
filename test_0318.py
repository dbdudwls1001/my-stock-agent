import streamlit as st
import yfinance as yf
import datetime
import pandas as pd
from deep_translator import GoogleTranslator
import time

# --- 1. 페이지 및 환경 설정 ---
st.set_page_config(page_title="US Stock Agent 2026", layout="wide")
ko_translator = GoogleTranslator(source='en', target='ko')

# --- 2. 사이드바 설정 ---
st.sidebar.header("⚙️ 분석 설정")
search_query = st.sidebar.text_input("종목 티커 입력").upper().strip()

st.sidebar.subheader("📅 조회 기간 설정")
start_date = st.sidebar.date_input("시작 날짜", datetime.date.today() - datetime.timedelta(days=30))
end_date = st.sidebar.date_input("종료 날짜", datetime.date.today())

# --- [함수] 데이터 로드 통합 로직 (에러 수정됨) ---
def fetch_stock_data_safe(ticker_str):
    """
    세션을 직접 설정하지 않고 yfinance 내부 로직을 사용하도록 수정.
    재시도 로직을 통해 PLTR 등 데이터 로드 실패율을 낮춥니다.
    """
    # [수정] session 인자를 제거하여 yfinance가 직접 curl_cffi를 다루게 함
    stock_obj = yf.Ticker(ticker_str)
    info_data = None
    
    # 최대 3회 재시도 (점진적 대기 시간 증가)
    for i in range(3):
        try:
            # 최신 버전에서는 proxy나 impersonate 설정 없이도 기본적으로 동작함
            info_data = stock_obj.info
            if info_data and 'symbol' in info_data:
                return stock_obj, info_data
        except Exception:
            time.sleep(1.0 * (i + 1)) 
    return stock_obj, info_data

def get_news_elements(news_item):
    """
    유동적인 뉴스 JSON 구조에서 필요한 정보를 추출하는 통합 추출기
    """
    content = news_item.get('content', news_item)
    
    return {
        'title': content.get('title') or news_item.get('title'),
        'link': content.get('clickThroughUrl', {}).get('url') or content.get('link') or news_item.get('link') or "#",
        'publisher': content.get('publisher') or news_item.get('publisher') or "Yahoo Finance",
        'summary': content.get('summary') or news_item.get('summary', ""),
        'time': content.get('pubDate') or content.get('providerPublishTime') or news_item.get('providerPublishTime') or 0,
        'thumb': content.get('thumbnail') or news_item.get('thumbnail', {})
    }

# --- 3. 메인 분석 로직 ---
if st.sidebar.button("데이터 분석 시작"):
    with st.spinner(f"🚀 {search_query} 데이터를 야후 서버에서 정밀 분석 중..."):
        # 수정된 함수 호출
        stock, info = fetch_stock_data_safe(search_query)
        
        st.title(f"🇺🇸 {search_query} 실시간 데이터 분석기")
        
        tab1, tab2 = st.tabs(["📊 최신 뉴스 분석 (한글)", "📂 기업 상세 정보"])

        # --- [탭 1: 뉴스 분석] ---
        with tab1:
            try:
                raw_news = stock.news
                if raw_news:
                    processed_news = [get_news_elements(n) for n in raw_news]
                    sorted_news = sorted(processed_news, key=lambda x: x['time'], reverse=True)
                    
                    filtered_count = 0
                    for news in sorted_news:
                        if not news['title']: continue
                        
                        pub_time = datetime.datetime.fromtimestamp(int(news['time']))
                        
                        if start_date <= pub_time.date() <= end_date:
                            filtered_count += 1
                            
                            try:
                                t_ko = ko_translator.translate(news['title'])
                                s_ko = ko_translator.translate(news['summary']) if len(news['summary']) > 5 else ""
                            except:
                                t_ko, s_ko = news['title'], news['summary']

                            col1, col2 = st.columns([1, 4])
                            with col1:
                                resolutions = news['thumb'].get('resolutions', [])
                                if resolutions:
                                    st.image(resolutions[0].get('url'), use_container_width=True)
                                else:
                                    st.write("🖼️ No Image")
                            
                            with col2:
                                st.markdown(f"#### [{t_ko}]({news['link']})")
                                st.caption(f"🕒 {pub_time.strftime('%Y-%m-%d %H:%M')} | 출처: {news['publisher']}")
                                if s_ko: st.write(s_ko)
                            st.divider()
                    
                    if filtered_count == 0:
                        st.warning(f"⚠️ {start_date} ~ {end_date} 기간에 해당하는 뉴스가 없습니다.")
                else:
                    st.info("ℹ️ 현재 해당 티커에 대해 제공되는 뉴스가 없습니다.")
            except Exception as e:
                st.error(f"뉴스 처리 중 오류가 발생했습니다.")

        # --- [탭 2: 기업 정보] ---
        with tab2:
            if info:
                c1, c2, c3 = st.columns(3)
                m_cap = info.get('marketCap', 0)
                # 180°C 등 수치는 텍스트로 렌더링
                c1.metric("현재가", f"${info.get('currentPrice', 0):,.2f}")
                c2.metric("시가총액", f"${m_cap/1e8:,.1f}억" if m_cap else "N/A")
                c3.metric("PER(Forward)", f"{info.get('forwardPE', 'N/A')}배")
                
                st.divider()
                st.subheader("📝 기업 개요 (한글 번역)")
                summary_en = info.get('longBusinessSummary', '')
                if summary_en:
                    try:
                        st.write(ko_translator.translate(summary_en))
                    except:
                        st.write(summary_en)
                else:
                    st.write("상세 개요 정보가 없습니다.")
            else:
                st.error("기업 정보를 불러오는 데 실패했습니다.")