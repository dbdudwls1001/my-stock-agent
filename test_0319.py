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
        
        q_type = info.get('quoteType', '').upper()
        is_etf = q_type in ['ETF', 'FUND', 'MUTUALFUND'] and q_type != 'EQUITY'
        
        return {"stock": stock, "info": info, "price": current_price, "delta_pct": change_pct, "is_etf": is_etf}
    except:
        return None

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="영진님의 미주 포트폴리오 에이전트", layout="wide")
ko_translator = GoogleTranslator(source='en', target='ko')

# --- 2. 사이드바: 종목 관리 ---
st.sidebar.header("📁 관심 종목 관리")

def add_ticker_logic():
    ticker = st.session_state.new_ticker_input.upper().strip()
    if ticker:
        if ticker not in st.session_state.watchlist:
            st.session_state.watchlist.append(ticker)
            save_watchlist(st.session_state.watchlist)
        else:
            st.sidebar.warning(f"⚠️ {ticker}는 이미 있습니다.")
        st.session_state.new_ticker_input = ""

st.sidebar.text_input("추가할 티커 입력 (예: TSLA)", key="new_ticker_input", on_change=add_ticker_logic)

if st.sidebar.button("➕ 종목 추가", use_container_width=True):
    add_ticker_logic()

st.sidebar.markdown("---")

if st.session_state.watchlist:
    st.sidebar.subheader("🗑️ 종목 삭제")
    ticker_to_remove = st.sidebar.selectbox("삭제할 종목 선택", st.session_state.watchlist)
    if st.sidebar.button("선택 종목 삭제", use_container_width=True):
        st.session_state.watchlist.remove(ticker_to_remove)
        save_watchlist(st.session_state.watchlist)
        st.sidebar.info(f"🗑️ {ticker_to_remove} 삭제됨")
        st.rerun()

# --- 3. 메인 화면 ---
st.title("📈 나의 관심 종목 실시간 브리핑")
watchlist_str = ", ".join([f"**{t}**" for t in st.session_state.watchlist])
st.write(f"현재 관리 중인 종목: {watchlist_str}")

if st.button("🚀 모든 종목 분석 시작", use_container_width=True):
    if not st.session_state.watchlist:
        st.error("관심 종목 리스트가 비어 있습니다.")
    else:
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
                        # [뉴스 분석 영역]
                        st.markdown("**📰 AI 뉴스 최신 브리핑**")
                        try:
                            raw_news = data['stock'].news
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

                        # [데이터 검증 및 시각화 영역]
                        show_etf_chart = False
                        if data['is_etf']:
                            try:
                                holdings = None
                                if hasattr(data['stock'], 'get_holdings'):
                                    holdings = data['stock'].get_holdings()
                                elif hasattr(data['stock'], 'funds_data'):
                                    holdings = data['stock'].funds_data.top_holdings
                                
                                if holdings is not None and not holdings.empty:
                                    show_etf_chart = True
                                    st.subheader("📊 ETF TOP 10 보유 비중")
                                    df_plot = holdings.reset_index()
                                    cols_list = df_plot.columns.tolist()
                                    val_col = next((c for c in cols_list if any(k in c.lower() for k in ['percent', 'value', 'holding'])), cols_list[-1])
                                    name_col = next((c for c in cols_list if any(k in c.lower() for k in ['symbol', 'ticker', 'holding']) and c != val_col), cols_list[0])
                                    df_plot[val_col] = pd.to_numeric(df_plot[val_col], errors='coerce').fillna(0)
                                    
                                    if df_plot[val_col].sum() > 0:
                                        fig = px.pie(df_plot, values=val_col, names=name_col, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                                        fig.update_traces(textposition='inside', textinfo='percent+label')
                                        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350)
                                        st.plotly_chart(fig, use_container_width=True)
                                        st.table(df_plot[[name_col, val_col]].head(10))
                                    else:
                                        show_etf_chart = False
                                else:
                                    show_etf_chart = False
                            except:
                                show_etf_chart = False

                        # [기업 상세 개요 섹션 - 융합 및 보완 부분]
                        if not show_etf_chart:
                            info = data['info']
                            c1, c2, c3 = st.columns(3)
                            c1.metric("PER", f"{info.get('trailingPE', 'N/A')}")
                            c2.metric("ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%" if info.get('returnOnEquity') else "N/A")
                            c3.metric("시가총액", f"${info.get('marketCap', 0)/1e9:.1f}B")
                            
                            st.markdown("---")
                            st.subheader(f"🏢 {ticker} 기업 상세 개요")
                            
                            desc = info.get('longBusinessSummary', '설명 없음')
                            if desc != '설명 없음':
                                try:
                                    # 번역 글자수를 2,000자로 대폭 확장하여 상세 정보 제공
                                    desc_ko = ko_translator.translate(desc[:2000])
                                    st.success(desc_ko)
                                    
                                    # 원문이 매우 길 경우를 대비한 '원문 전체 보기'
                                    if len(desc) > 2000:
                                        with st.expander("영문 원문 전체 보기"):
                                            st.write(desc)
                                except:
                                    # 번역 실패 시 안전하게 원문 노출
                                    st.warning("번역 오류로 인해 영문 원문을 표시합니다.")
                                    st.write(desc)
                            else:
                                st.info("제공된 기업 상세 정보가 없습니다.")

st.divider()
st.caption(f"PM 영진님의 아침 루틴을 응원합니다. | 데이터 기준: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")