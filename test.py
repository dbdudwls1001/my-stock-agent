import streamlit as st
import requests
import datetime
import pandas as pd

# --- 설정 ---
API_KEY = "OAYMnRInI2HQ0jP4ybi0RkB61W6imzQS" 
BASE_URL = "https://financialmodelingprep.com/stable"

st.set_page_config(page_title="US Stock Agent 2026", layout="wide")

st.sidebar.header("⚙️ 분석 설정")
ticker = st.sidebar.text_input("종목 티커 (Ticker)", "AAPL").upper().strip()

st.sidebar.subheader("📅 조회 기간 설정")
start_date = st.sidebar.date_input("시작 날짜", datetime.date.today() - datetime.timedelta(days=7))
end_date = st.sidebar.date_input("종료 날짜", datetime.date.today())
news_limit = st.sidebar.slider("최대 뉴스 개수 (가져올 데이터량)", 10, 100, 50)

if st.sidebar.button("데이터 분석 시작"):
    tab1, tab2 = st.tabs(["📊 주요 뉴스 분석", "📂 SEC 공시 현황"])
    
    # 비교를 위한 날짜 문자열 변환
    from_str = start_date.strftime('%Y-%m-%d')
    to_str = end_date.strftime('%Y-%m-%d')

    with st.spinner(f"🚀 {ticker} 데이터 조회 중..."):
        
        # --- [탭 1: 뉴스 분석] ---
        with tab1:
            # 404 해결을 위한 '하이픈' 경로 적용
            # 2026년 기준 stable API는 stock-news(하이픈)를 권장합니다.
            news_url = f"{BASE_URL}/stock_news?tickers={ticker}&limit={news_limit}&apikey={API_KEY}"
            res = requests.get(news_url)
            
            # 만약 404라면 언더바(_) 버전으로 즉시 재시도
            if res.status_code == 404:
                news_url = f"{BASE_URL}/stock_news?tickers={ticker}&limit={news_limit}&apikey={API_KEY}"
                res = requests.get(news_url)

            if res.status_code == 200:
                news_data = res.json()
                if news_data:
                    # [핵심] API에 날짜를 넣지 않고, 가져온 데이터에서 수동으로 필터링
                    # 이렇게 해야 파라미터 오동작으로 인한 404를 피할 수 있습니다.
                    filtered_news = [
                        n for n in news_data 
                        if from_str <= n.get('publishedDate', '').split(' ')[0] <= to_str
                    ]
                    
                    if filtered_news:
                        for news in filtered_news:
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if news.get('image'): st.image(news['image'], use_container_width=True)
                            with col2:
                                st.markdown(f"#### [{news.get('title')}]({news.get('url')})")
                                st.caption(f"🕒 {news.get('publishedDate')} | {news.get('site')}")
                                st.write(news.get('text', '내용 없음'))
                            st.divider()
                    else:
                        st.info(f"{from_str} ~ {to_str} 기간에 해당하는 뉴스가 데이터에 포함되어 있지 않습니다. 조회 기간을 늘리거나 최대 개수를 늘려보세요.")
                else:
                    st.warning("조회된 뉴스 데이터가 없습니다.")
            else:
                st.error(f"뉴스 API 접근 실패 (코드: {res.status_code})")
                st.write(f"최종 시도 URL: {news_url}")

        # --- [탭 2: SEC 공시] ---
        with tab2:
            # 공시 역시 하이픈(-) 경로 우선 적용
            sec_url = f"{BASE_URL}/sec-filings?symbol={ticker}&limit=100&apikey={API_KEY}"
            sec_res = requests.get(sec_url)
            
            if sec_res.status_code == 200:
                sec_data = sec_res.json()
                if sec_data:
                    df = pd.DataFrame(sec_data)
                    df['fillingDate'] = pd.to_datetime(df['fillingDate']).dt.date
                    mask = (df['fillingDate'] >= start_date) & (df['fillingDate'] <= end_date)
                    df = df.loc[mask, ['fillingDate', 'type', 'finalLink']]
                    
                    if not df.empty:
                        df.columns = ['공시일자', '유형', '원문링크']
                        st.dataframe(df, column_config={"원문링크": st.column_config.LinkColumn("보고서")}, use_container_width=True, hide_index=True)
                    else:
                        st.info("기간 내 공시가 없습니다.")
                else:
                    st.info("공시 데이터가 없습니다.")
            else:
                st.warning(f"공시 API 실패 (코드: {sec_res.status_code})")