# 창원 기온 대시보드 (보너스 ① 분석 결과 서비스화)
# 실행 방법: 터미널에서  streamlit run app.py

import pandas as pd
import streamlit as st

# ── 0. 화면 기본 설정 ──
st.set_page_config(page_title="창원 기온 대시보드", page_icon="🌡️", layout="wide")
st.title("🌡️ 창원 일별 평균기온 대시보드 (2023~2025)")
st.caption("데이터: Open-Meteo Historical Weather API (CC BY 4.0) · 일별 평균기온(24시간 평균)")


# ── 1. 데이터 불러오기 (한 번 읽으면 기억해 두기: cache) ──
@st.cache_data
def load_data():
    df = pd.read_csv("data/changwon_temperature_2023_2025.csv", encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df.sort_values("날짜").reset_index(drop=True)


df = load_data()

# ── 2. 왼쪽 사이드바: 사용자가 바꿀 수 있는 조건 ──
st.sidebar.header("🔧 조건 바꾸기")

min_day = df["날짜"].min().date()
max_day = df["날짜"].max().date()

# 주소(URL) 뒤에 ?start=2024-06-01&end=2024-08-31&ma=7 처럼 붙이면 그 조건으로 바로 열림
qp = st.query_params


def from_url(key, default):
    try:
        return min(max(pd.to_datetime(qp[key]).date(), min_day), max_day)
    except Exception:
        return default


MA_OPTIONS = [7, 14, 30, 60]
ma_from_url = int(qp["ma"]) if qp.get("ma", "").isdigit() and int(qp["ma"]) in MA_OPTIONS else 30

period = st.sidebar.date_input(
    "기간 선택",
    value=(from_url("start", min_day), from_url("end", max_day)),
    min_value=min_day,
    max_value=max_day,
)
# 날짜를 하나만 고른 상태면 시작일=종료일로 처리
start, end = (period if len(period) == 2 else (period[0], period[0]))

window = st.sidebar.selectbox("이동평균 기간(일)", MA_OPTIONS, index=MA_OPTIONS.index(ma_from_url))

# ── 3. 계산 (이동평균은 전체 데이터로 먼저 계산 → 기간 앞부분도 값이 나오게) ──
df["이동평균"] = df["평균기온"].rolling(window=window).mean()
df["전일대비변화"] = df["평균기온"].diff()

mask = (df["날짜"].dt.date >= start) & (df["날짜"].dt.date <= end)
sel = df[mask]

if sel.empty:
    st.warning("선택한 기간에 데이터가 없습니다. 기간을 다시 골라 주세요.")
    st.stop()

# ── 4. 요약 숫자 카드 ──
c1, c2, c3, c4 = st.columns(4)
c1.metric("평균기온", f"{sel['평균기온'].mean():.1f}°C")
hot = sel.loc[sel["평균기온"].idxmax()]
c2.metric("가장 더운 날", f"{hot['평균기온']:.1f}°C", hot["날짜"].strftime("%Y-%m-%d"), delta_color="off")
cold = sel.loc[sel["평균기온"].idxmin()]
c3.metric("가장 추운 날", f"{cold['평균기온']:.1f}°C", cold["날짜"].strftime("%Y-%m-%d"), delta_color="off")
changes = sel["전일대비변화"].dropna()  # 첫날은 '전날'이 없어서 빈 값 → 빼고 계산
if changes.empty:
    c4.metric("하루 최대 하락", "-")
else:
    drop = sel.loc[changes.idxmin()]
    c4.metric("하루 최대 하락", f"{drop['전일대비변화']:.1f}°C", drop["날짜"].strftime("%Y-%m-%d"), delta_color="off")

st.caption(f"선택 기간: {start} ~ {end} ({len(sel)}일)")

# ── 5. 그래프 1: 일별 기온 + 이동평균 ──
st.subheader(f"📈 일별 평균기온과 {window}일 이동평균")
chart_df = sel.set_index("날짜")[["평균기온", "이동평균"]].rename(
    columns={"평균기온": "일별 평균기온", "이동평균": f"{window}일 이동평균"}
)
st.line_chart(chart_df)

# ── 6. 그래프 2: 월별 평균기온 (선택 기간 기준) ──
st.subheader("📊 월별 평균기온 (선택 기간, 연-월 순서)")
monthly = sel.groupby(sel["날짜"].dt.strftime("%Y-%m"))["평균기온"].mean().round(1)
st.bar_chart(monthly, x_label="연-월", y_label="평균기온(°C)")

# ── 7. 표: 하루 사이 가장 크게 떨어진 날 TOP 5 ──
st.subheader("❄️ 하루 사이 기온이 가장 크게 떨어진 날 TOP 5")
top5 = sel.nsmallest(5, "전일대비변화")[["날짜", "평균기온", "전일대비변화"]].copy()
top5["날짜"] = top5["날짜"].dt.strftime("%Y-%m-%d")
st.dataframe(top5.reset_index(drop=True), width="stretch")
