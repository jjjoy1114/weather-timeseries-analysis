"""창원 기온 분석에서 여러 번 쓰는 공통 함수 모음.

노트북(.ipynb)마다 같은 코드를 반복하지 않도록, 데이터 수집·불러오기·
품질 점검·연평균·추세 계산을 이 파일 하나에 모아 두었습니다.
"""

import numpy as np
import pandas as pd
import requests

# 창원 좌표 (Open-Meteo가 이 위치의 기온을 찾아 줌)
CHANGWON_LAT = 35.2281
CHANGWON_LON = 128.6811
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_daily_mean(start_date, end_date, lat=CHANGWON_LAT, lon=CHANGWON_LON):
    """Open-Meteo 과거기상 API에서 일별 평균기온을 받아 표(DataFrame)로 돌려준다.

    start_date, end_date: "YYYY-MM-DD" 형식 문자열
    반환: 컬럼 [날짜, 평균기온]
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean",
        "timezone": "Asia/Seoul",
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=120)
    response.raise_for_status()  # 요청이 실패하면 여기서 바로 오류를 알려 줌
    daily = response.json()["daily"]
    return pd.DataFrame({"날짜": pd.to_datetime(daily["time"]), "평균기온": daily["temperature_2m_mean"]})


def load_csv(path):
    """저장해 둔 CSV를 불러와 날짜 순으로 정렬해 돌려준다."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["날짜"] = pd.to_datetime(df["날짜"])
    return df.sort_values("날짜").reset_index(drop=True)


def check_quality(df):
    """결측치 개수, 기간상 날 수, 실제 데이터 수, 최저·최고를 한 번에 확인한다."""
    expected = (df["날짜"].max() - df["날짜"].min()).days + 1
    return {
        "기간": f'{df["날짜"].min().date()} ~ {df["날짜"].max().date()}',
        "결측치": int(df["평균기온"].isna().sum()),
        "기간상 날 수": expected,
        "실제 데이터 수": len(df),
        "최저": float(df["평균기온"].min()),
        "최고": float(df["평균기온"].max()),
    }


def yearly_mean(df):
    """연도별 평균기온 (index=연도)."""
    return df.groupby(df["날짜"].dt.year)["평균기온"].mean()


def linear_trend(series):
    """연도별 값에 직선을 맞춰 '1년에 몇 도씩 변하는지'(기울기)를 구한다.

    반환: (기울기[°C/년], 직선 위의 값들 Series)
    """
    x = np.asarray(series.index, dtype=float)
    y = series.to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return slope, pd.Series(slope * x + intercept, index=series.index)


def decade_means(yearly, edges=(1996, 2006, 2016, 2026)):
    """10년 단위 평균 (예: 1996~2005, 2006~2015, 2016~2025)."""
    out = {}
    for a, b in zip(edges[:-1], edges[1:]):
        part = yearly[(yearly.index >= a) & (yearly.index < b)]
        out[f"{a}~{b - 1}"] = part.mean()
    return pd.Series(out)
