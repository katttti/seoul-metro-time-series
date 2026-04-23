"""
generate_test_data.py — 테스트용 synthetic subway_raw_all.csv 생성

실제 API 없이 02_preprocessing.py ~ 05_decomposition.py 파이프라인 검증용.
주간 계절성, COVID 충격, 연간 추세를 모방한 가짜 데이터를 생성한다.

출력:
  data/raw/subway_raw_all.csv

실행:
  python src/generate_test_data.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import RAW_DIR, TARGET_STATIONS, COVID_DATE, ensure_dirs

# ── 설정 ───────────────────────────────────────────────────────────────────────
START_DATE = "2018-01-01"
END_DATE   = "2024-12-31"
SEED       = 42

# 역별 기준 일평균 승하차 (실제 수치에 근사)
BASE_BOARDING = {
    "강남":   90_000,
    "잠실":   75_000,
    "신도림": 65_000,
    "홍대입구": 55_000,
}

# 기타 2호선 역 (전체 수집 모방)
OTHER_STATIONS = ["교대", "선릉", "역삼", "삼성", "건대입구", "합정", "당산"]
OTHER_BASE = 30_000

COVID_SHOCK = 0.42       # COVID 기간 평균 감소율
COVID_RECOVERY_DAYS = 600  # 완전 회복까지 일수


def make_multiplier(dates: pd.DatetimeIndex) -> np.ndarray:
    """날짜 배열 → 승하차 비율 배열 (계절성 + COVID 충격)"""
    rng = np.random.default_rng(SEED)
    n = len(dates)

    # 요일 효과: 월=1.15, 화=1.10, 수=1.08, 목=1.07, 금=1.12, 토=0.75, 일=0.60
    dow_effect = np.array([1.15, 1.10, 1.08, 1.07, 1.12, 0.75, 0.60])
    weekday_mult = np.array([dow_effect[d.weekday()] for d in dates])

    # 연간 추세 (연 1% 성장)
    years = (dates - pd.Timestamp(START_DATE)).days / 365.25
    trend = 1.0 + 0.01 * years

    # COVID 충격: 2020-03-01 ~ 회복
    covid_start = pd.Timestamp(COVID_DATE)
    shock = np.ones(n)
    for i, d in enumerate(dates):
        if d >= covid_start:
            days_since = (d - covid_start).days
            if days_since < COVID_RECOVERY_DAYS:
                t = days_since / COVID_RECOVERY_DAYS
                shock[i] = 1.0 - COVID_SHOCK * (1 - t)
            # 회복 후 약간 낮은 수준 유지 (재택근무 정착)
            else:
                shock[i] = 0.88

    # 노이즈 (±8%)
    noise = rng.normal(1.0, 0.08, n)

    return weekday_mult * trend * shock * noise


def generate() -> pd.DataFrame:
    ensure_dirs()
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    mult = make_multiplier(dates)

    rows = []
    all_stations = {s: BASE_BOARDING[s] for s in TARGET_STATIONS}
    all_stations.update({s: OTHER_BASE for s in OTHER_STATIONS})

    for i, d in enumerate(dates):
        date_str = d.strftime("%Y%m%d")
        m = max(mult[i], 0.1)  # 음수 방지
        for station, base in all_stations.items():
            boarding  = int(base * m * np.random.default_rng(SEED + i).uniform(0.95, 1.05))
            alighting = int(boarding * np.random.default_rng(SEED + i + 1).uniform(0.92, 1.08))
            rows.append({
                "USE_DT":           date_str,
                "LINE_NUM":         "2호선",
                "SUB_STA_NM":       station,
                "RIDE_PASGR_NUM":   boarding,
                "ALIGHT_PASGR_NUM": alighting,
            })

    df = pd.DataFrame(rows)
    out = RAW_DIR / "subway_raw_all.csv"
    df.to_csv(out, index=False)
    print(f"생성 완료: {len(df):,}행 → {out}")
    print(f"날짜 범위: {df['USE_DT'].min()} ~ {df['USE_DT'].max()}")
    print(f"역 수: {df['SUB_STA_NM'].nunique()}")
    return df


if __name__ == "__main__":
    generate()
