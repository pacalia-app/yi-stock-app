import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 0. 설정 및 환율 정보 가져오기 (Fact: 실시간 환율 반영)
st.set_page_config(layout="wide", page_title="글로벌 포트폴리오 매니저")

@st.cache_data(ttl=3600) # 환율은 1시간마다 업데이트
def get_usd_krw():
    try:
        ex_data = yf.download("USDKRW=X", period="1d")
        return ex_data['Close'].iloc[-1]
    except:
        return 1350.0 # 환율 호출 실패 시 기본값 (주의: 실제와 다를 수 있음)

exchange_rate = get_usd_krw()

# 자동 업데이트 설정 (300초 = 5분)
# st.empty()와 연동하여 화면을 주기적으로 새로고침하는 효과를 줍니다.
# streamlit 공식 기능인 st_autorefresh 등을 쓸 수 있으나, 기본 기능으로 구현합니다.

# 1. 데이터 저장 및 로드
DATA_FILE = "portfolio_v2.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["종목코드", "평단가", "수량", "통화", "목표수익률"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

portfolio_df = load_data()

# 2. 사이드바 구성
with st.sidebar:
    st.header("⚙️ 설정 및 추가")
    with st.form("add_form"):
        ticker = st.text_input("종목코드 (예: AAPL 또는 005930.KS)")
        currency = st.selectbox("통화", ["KRW", "USD"])
        price = st.number_input("매수 평단가", min_value=0.0)
        qty = st.number_input("보유 수량", min_value=0.0)
        target = st.number_input("목표 수익률(%)", min_value=0.0, value=10.0)
        if st.form_submit_button("포트폴리오 추가"):
            new_row = pd.DataFrame([[ticker, price, qty, currency, target]], columns=portfolio_df.columns)
            portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
            save_data(portfolio_df)
            st.rerun()

    if st.button("데이터 초기화"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.rerun()
            
    st.write(f"현재 적용 환율: 1$ = {exchange_rate:,.2f}원")

# 3. 메인 화면 및 데이터 처리
st.title("📊 통합 투자 모니터링 시스템")
st.caption(f"최근 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (5분마다 자동 갱신 권장)")

if not portfolio_df.empty:
    results = []
    alert_list = [] # 알림 대상 리스트

    for _, row in portfolio_df.iterrows():
        t = row["종목코드"]
        stock_data = yf.download(t, period="1d")
        if not stock_data.empty:
            curr_p = stock_data['Close'].iloc[-1]
            # 통화별 계산
            is_usd = row["통화"] == "USD"
            unit = "$" if is_usd else "원"
            
            total_buy = row["평단가"] * row["수량"]
            total_curr = curr_p * row["수량"]
            
            # 원화 환산 (Fact: 모든 자산을 원화로 통합 비교)
            total_curr_krw = total_curr * (exchange_rate if is_usd else 1)
            
            roi = ((curr_p - row["평단가"]) / row["평단가"]) * 100
            
            # 알림 체크 (목표 수익률 도달 여부)
            if roi >= row["목표수익률"]:
                alert_list.append(f"🚨 {t} 목표 수익률({row['목표수익률']}%) 달성! (현재: {roi:.2f}%)")

            results.append({
                "종목": t,
                "현재가": f"{curr_p:,.2f}{unit}",
                "수익률": roi,
                "평가금액(원화)": total_curr_krw,
                "통화": row["통화"]
            })

    res_df = pd.DataFrame(results)

    # 알림 표시
    for msg in alert_list:
        st.toast(msg) # 화면 우측 하단에 잠깐 떴다 사라지는 알림

    # 요약 지표
    total_val = res_df["평가금액(원화)"].sum()
    st.metric("총 통합 자산 (원화 환산)", f"{total_val:,.0f}원")

    # 대시보드 배치
    c1, c2 = st.columns([3, 2])
    
    with c1:
        st.subheader("실시간 보유 현황")
        st.dataframe(res_df.style.highlight_max(axis=0, subset=['수익률'], color='#ffcccc'))

    with c2:
        st.subheader("자산 배분 비중")
        fig = px.sunburst(res_df, path=['통화', '종목'], values='평가금액(원화)')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("왼쪽 사이드바에서 종목을 추가하십시오.")
