import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(layout="wide", page_title="글로벌 포트폴리오 매니저")

# 2. 환율 정보 가져오기 (에러 방지용 예외 처리 강화)
@st.cache_data(ttl=3600)
def get_usd_krw():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", interval="1m")
        if not ex_data.empty:
            val = ex_data['Close'].iloc[-1]
            return float(val)
        return 1350.0
    except:
        return 1350.0

exchange_rate = get_usd_krw()

# 3. 데이터 저장 및 로드 설정
DATA_FILE = "portfolio_v2.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except:
            pass
    return pd.DataFrame(columns=["종목코드", "평단가", "수량", "통화", "목표수익률"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

portfolio_df = load_data()

# 4. 사이드바 구성 (입력 및 설정)
with st.sidebar:
    st.header("⚙️ 포트폴리오 설정")
    with st.form("add_form", clear_on_submit=True):
        ticker = st.text_input("종목코드 (예: AAPL 또는 005930.KS)")
        currency = st.selectbox("통화", ["KRW", "USD"])
        price = st.number_input("매수 평단가", min_value=0.0, step=0.1)
        qty = st.number_input("보유 수량", min_value=0.0, step=0.1)
        target = st.number_input("목표 수익률(%)", min_value=0.0, value=10.0)
        
        if st.form_submit_button("종목 추가"):
            if ticker:
                new_row = pd.DataFrame([[ticker, price, qty, currency, target]], 
                                     columns=portfolio_df.columns)
                portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
                save_data(portfolio_df)
                st.rerun()

    if st.button("데이터 전체 초기화"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.rerun()
            
    st.write(f"현재 적용 환율: 1$ = {exchange_rate:,.2f}원")

# 5. 메인 화면 구성
st.title("📊 포트폴리오")
st.caption(f"최근 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if not portfolio_df.empty:
    results = []
    alert_list = []

    for _, row in portfolio_df.iterrows():
        t = str(row["종목코드"]).strip()
        stock_data = yf.download(t, period="1d")
        
        if not stock_data.empty:
            # 데이터 추출 (TypeError 방지를 위해 명시적 형변환)
            curr_p = float(stock_data['Close'].iloc[-1])
            is_usd = row["통화"] == "USD"
            unit = "$" if is_usd else "원"
            
            # 계산 로직
            buy_price = float(row["평단가"])
            quantity = float(row["수량"])
            
            total_buy = buy_price * quantity
            total_curr = curr_p * quantity
            total_curr_krw = total_curr * (exchange_rate if is_usd else 1)
            
            # 수익률 계산 (분모가 0인 경우 방지)
            roi = ((curr_p - buy_price) / buy_price * 100) if buy_price > 0 else 0
            
            # 목표 수익률 알림 체크
            try:
                target_val = float(row["목표수익률"])
                if roi >= target_val:
                    alert_list.append(f"🚨 {t} 목표 수익률({target_val}%) 달성! (현재: {roi:.2f}%)")
            except:
                pass

            # 결과 리스트에 데이터 추가
            results.append({
                "종목": t,
                "현재가": f"{curr_p:,.2f}{unit}",
                "수익률": roi,
                "평가금액(원화)": total_curr_krw,
                "통화": row["통화"]
            })

    # 화면에 데이터 표시
    if results:
        res_df = pd.DataFrame(results)

        # 알림 메시지 출력
        for msg in alert_list:
            st.toast(msg)

        # 상단 요약 지표
        total_val_krw = res_df["평가금액(원화)"].sum()
        st.metric("총 통합 자산 (원화 환산)", f"{total_val_krw:,.0f}원")

        # 레이아웃 분할
        c1, c2 = st.columns([3, 2])
        
        with c1:
            st.subheader("실시간 보유 현황")
            # 수익률 소수점 정리 및 표시
            st.dataframe(res_df.style.format({'수익률': '{:.2f}%', '평가금액(원화)': '{:,.0f}'}))

        with c2:
            st.subheader("자산 배분")
            fig = px.pie(res_df, values='평가금액(원화)', names='종목', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("왼쪽 사이드바에서 종목 정보를 입력하고 '종목 추가' 버튼을 눌러주세요.")
