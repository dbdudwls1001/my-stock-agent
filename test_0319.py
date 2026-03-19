import streamlit as st
import yfinance as yf
import datetime
import pandas as pd
from deep_translator import GoogleTranslator
import time
import os
import plotly.express as px
from collections import Counter
import re

# --- 0. 파일 입출력 및 초기 설정 ---
WATCHLIST_FILE = "my_watchlist.txt"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return [line.strip().upper() for line in f.readlines() if line.strip()]
    return ["NVDA", "PLTR", "QQQ", "SCHD"]

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        for ticker in watchlist:
            f.write(f"{ticker}\n")

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# --- [유틸리티] 키워드 및 감성 분석 ---
def get_translated_keywords(text, translator, num=5):
    words = re.findall(r'\b[A-Z]{2,}\b|\b[a-zA-Z]{4,}\b', text)
    stopwords = ['STOCK', 'MARKET', 'NEWS', 'UPDATE', 'REPORT', 'STOCKS', 'PRICE', 'ANALYSIS']
    meaningful_words = [w.upper() for w in words if w.upper() not in stopwords]
    most_common = [tag[0] for tag in Counter(meaningful_words).most_common(num)]
    translated_tags = []
    for word in most_common:
        try:
            ko_word = translator.translate(word).strip()
            translated_tags.append(ko_word)
        except:
            translated_tags.append(word)
    return translated_tags

def analyze_sentiment(title_en, summary_en):
    text = (title_en + " " + (summary_en if summary_en else "")).upper()
    positive_words = ['UPGRADE', 'BEAT', 'GROWTH', 'BUY', 'SURGE', 'BULLISH', 'PROFIT', 'EXPAND', 'GAIN', 'HIGHER']
    negative_words = ['DOWNGRADE', 'MISS', 'FALL', 'SELL', 'DROP', 'BEARISH', 'LOSS', 'REDUCE', 'LOWER', 'RISK', 'DEBT']
    pos_score = sum(1 for word in positive_words if word in text)
    neg_score = sum(1 for word in negative_words if word in text)
    if pos_score > neg_score: return "🟢 호재"
    elif neg_score > pos_score: return "🔴 악재"
    else: return "⚪ 중립"

def get_stock_summary(ticker_str):
    try:
        stock = yf.Ticker(ticker_str)
        info = stock.info
        if not info: return None
        current_price = (info.get('currentPrice') or info.get('navPrice') or 
                         info.get('regularMarketPrice') or info.get('previousClose') or 0)
        prev_close = info.get('previousClose', 0)
        change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
        is_etf = info.get('quoteType', '').upper() in ['ETF', 'FUND']
        return {"stock": stock, "info": info, "price": current_price, "delta_pct": change_pct, "is_etf": is_etf}
    except:
        return None

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="영진님의 미주 포트폴리오 에이전트", layout="wide")
ko_translator = GoogleTranslator(source='en', target='ko')

# --- 2. 사이드바: 종목 관리 (엔터 이벤트 통합) ---
st.sidebar.header("📁 관심 종목 관리")

# 엔터 이벤트 처리를 위한 콜백 함수
def add_ticker_callback():
    ticker = st.session_state.new_ticker_input.upper().strip()
    if ticker:
        if ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(ticker)
            save_watchlist(st.session_state.watchlist)
            # 알림 메시지는 세션 상태를 활용해 표시하거나 간단히 처리
        else:
            st.sidebar.warning(f"⚠️ {ticker}는 이미 있습니다.")
        # 입력창 초기화
        st.session_state.new_ticker_input = ""

# 엔터 키 입력을 지원하는 텍스트 입력창
st.sidebar.text_input(
    "추가할 티커 입력 후 엔터 (예: TSLA)", 
    key="new_ticker_input", 
    on_change=add_ticker_callback
)

if st.session_state.watchlist:
    st.sidebar.subheader("🗑️ 종목 삭제")
    ticker_to_remove = st.sidebar.selectbox("삭제할 종목 선택", st.session_state.watchlist)
    if st.sidebar.button("선택 종목 삭제"):
        st.session_state.watchlist.remove(ticker_to_remove)
        save_watchlist(st.session_state.watchlist)
        st.sidebar.info(f"🗑️ {ticker_to_remove} 삭제됨")
        st.rerun()

# --- 3. 메인 화면 ---
st.title("📈 나의 관심 종목 실시간 브리핑")
watchlist_str = ", ".join([f"**{t}**" for t in st.session_state.watchlist])
st.write(f"현재 관리 중인 종목: {watchlist_str}")

if st.button("🚀 모든 종목 분석 시작"):
    if not st.session_state.watchlist:
        st.error("관심 종목 리스트가 비어 있습니다.")
    else:
        # 화면을 종목 수만큼 분할
        cols = st.columns(len(st.session_state.watchlist))
        
        for idx, ticker in enumerate(st.session_state.watchlist):
            with st.spinner(f"{ticker} 데이터 분석 중..."):
                data = get_stock_summary(ticker)
                if data:
                    with cols[idx]:
                        tag = " (ETF)" if data['is_etf'] else ""
                        st.metric(label=f"{ticker}{tag}", 
                                  value=f"${data['price']:,.2f}",
                                  delta=f"{data['delta_pct']:.2f}%")
                    
                    with st.expander(f"🔍 {ticker} 상세 브리핑"):
                        # [뉴스 분석]
                        st.markdown("**📰 AI 뉴스 최신 브리핑**")
                        try:
                            raw_news = data['stock'].newsa
                            if raw_news:
                                for n in raw_news[:5]:
                                    content = n.get('content', n)
                                    t_en = content.get('title', '')
                                    summary_en = (content.get('summary') or content.get('description') or "")
                                    link = (content.get('clickThroughUrl', {}).get('url') or content.get('link') or "#")
                                    sentiment = analyze_sentiment(t_en, summary_en)
                                    ko_keywords = get_translated_keywords(t_en, ko_translator)
                                    keyword_str = " ".join([f"`#{k}`" for k in ko_keywords])
                                    try:
                                        t_ko = ko_translator.translate(t_en)
                                        brief_ko = ko_translator.translate(summary_en[:200]) if len(summary_en) > 10 else "요약 없음"
                                    except:
                                        t_ko, brief_ko = t_en, summary_en
                                    
                                    st.write(f"**{sentiment.split()[0]} [{t_ko}]({link})**")
                                    st.caption(f"{keyword_str}")
                                    st.info(f"{brief_ko}")
                                    st.markdown("---")
                            else:
                                st.write("최근 뉴스가 없습니다.")
                        except:
                            st.write("뉴스 로드 실패")

                        # [ETF 비중 차트 및 지표]
                        if data['is_etf']:
                            st.subheader("📊 ETF TOP 10 보유 비중")
                            try:
                                holdings = None
                                try:
                                    holdings = data['stock'].get_holdings()
                                except:
                                    if hasattr(data['stock'], 'funds_data'):
                                        holdings = data['stock'].funds_data.top_holdings
                                
                                if holdings is not None and not holdings.empty:
                                    df_plot = holdings.reset_index()
                                    cols_list = df_plot.columns.tolist()
                                    
                                    # 컬럼명 유연하게 감지
                                    val_col = next((c for c in cols_list if any(k in c.lower() for k in ['percent', 'value', 'holding'])), cols_list[-1])
                                    name_col = next((c for c in cols_list if any(k in c.lower() for k in ['symbol', 'ticker', 'holding']) and c != val_col), cols_list[0])

                                    df_plot[val_col] = pd.to_numeric(df_plot[val_col], errors='coerce').fillna(0)
                                    
                                    if df_plot[val_col].sum() > 0:
                                        fig = px.pie(df_plot, values=val_col, names=name_col, hole=0.4,
                                                     color_discrete_sequence=px.colors.qualitative.Pastel)
                                        fig.update_traces(textposition='inside', textinfo='percent+label')
                                        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350)
                                        st.plotly_chart(fig, use_container_width=True)
                                        st.write("📋 상세 비중")
                                        st.table(df_plot[[name_col, val_col]].head(10))
                                    else:
                                        st.info("비중 수치 데이터가 비어 있습니다.")
                                else:
                                    st.warning("보유 종목 데이터를 불러올 수 없습니다.")
                            except:
                                st.error("차트 생성 중 오류가 발생했습니다.")
                        else:
                            # 개별 종목 지표
                            info = data['info']
                            c1, c2, c3 = st.columns(3)
                            c1.metric("PER", f"{info.get('trailingPE', 'N/A')}")
                            c2.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%" if info.get('returnOnEquity') else "N/A")
                            c3.metric("시가총액", f"${info.get('marketCap', 0)/1e9:.1f}B")
                            
                            desc = info.get('longBusinessSummary', '설명 없음')
                            try:
                                desc_ko = ko_translator.translate(desc[:500])
                                st.success(f"**🏢 기업 개요**\n\n{desc_ko}")
                            except:
                                st.success(desc[:300] + "...")

st.divider()
st.caption(f"PM 영진님의 아침 루틴을 응원합니다. | 데이터 기준: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")