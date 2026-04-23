"""
02_preprocessing.py — raw CSV → 분석용 processed CSV

입력:
  data/raw/subway_raw_all.csv

출력:
  data/processed/subway_line2_daily.csv
    컬럼: station, boarding, alighting, total,
           day_of_week, is_weekend, is_holiday, month, year, covid_dummy
    인덱스: date (DatetimeIndex)

실행:
  python src/02_preprocessing.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import (
    RAW_DIR, PROCESSED_DIR, RAW_STATION_FILTER, STATION_RENAME, COVID_DATE, ensure_dirs
)

INPUT_CSV  = RAW_DIR      / "subway_raw_all.csv"
OUTPUT_CSV = PROCESSED_DIR / "subway_line2_daily.csv"

# 공휴일 패키지 (없으면 하드코딩 fallback)
try:
    import holidays
    _KR_HOLIDAYS = holidays.KR(years=range(2018, 2026))
    def is_holiday(date) -> int:
        return int(date in _KR_HOLIDAYS)
except ImportError:
    # 주요 공휴일 하드코딩 (간소화)
    _FIXED_HOLIDAYS = {
        (1, 1), (3, 1), (5, 5), (6, 6), (8, 15), (10, 3), (10, 9), (12, 25)
    }
    def is_holiday(date) -> int:
        return int((date.month, date.day) in _FIXED_HOLIDAYS)


def load_raw() -> pd.DataFrame:
    print(f"원본 로드: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV, dtype=str)
    print(f"  raw shape: {df.shape}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # Step 1: 컬럼 매핑
    df = df.rename(columns={
        "USE_DT":           "date",
        "LINE_NUM":         "line",
        "SUB_STA_NM":       "station",
        "RIDE_PASGR_NUM":   "boarding",
        "ALIGHT_PASGR_NUM": "alighting",
    })

    # Step 2: date → datetime
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"])

    # Step 3: 2호선 필터
    df = df[df["line"] == "2호선"].copy()

    # boarding/alighting → 숫자
    df["boarding"]  = pd.to_numeric(df["boarding"],  errors="coerce").fillna(0).astype(int)
    df["alighting"] = pd.to_numeric(df["alighting"], errors="coerce").fillna(0).astype(int)

    # Step 4: (date, station) 중복 제거 (합산)
    df = (
        df.groupby(["date", "station"], as_index=False)
          .agg({"boarding": "sum", "alighting": "sum"})
    )

    # Step 5: 원시 역명으로 필터
    df = df[df["station"].isin(RAW_STATION_FILTER)].copy()

    # Step 6: 역명 약칭 적용 (잠실(송파구청) → 잠실)
    df["station"] = df["station"].replace(STATION_RENAME)

    print(f"  2호선 4개역 필터 후: {df.shape}")
    return df


def interpolate_missing(df: pd.DataFrame) -> pd.DataFrame:
    """결측 날짜를 전후 동일 요일 평균으로 보간 (요일 효과 보존)."""
    full_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    records = []

    actual_stations = df["station"].unique().tolist()
    for station in actual_stations:
        sub = df[df["station"] == station].set_index("date").reindex(full_dates)
        sub["station"] = station

        missing = sub["boarding"].isna()
        if missing.any():
            for col in ["boarding", "alighting"]:
                # 동일 요일 평균으로 채움
                sub[col] = sub[col].fillna(
                    sub.groupby(sub.index.dayofweek)[col].transform("mean")
                )
            sub[col] = sub[col].fillna(0)

        sub.index.name = "date"
        records.append(sub.reset_index())

    result = pd.concat(records, ignore_index=True)
    print(f"  보간 후: {result.shape}")
    return result


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    # Step 7-8: 파생변수
    df["total"]       = df["boarding"] + df["alighting"]
    df["day_of_week"] = df["date"].dt.dayofweek          # 0=월 ~ 6=일
    df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)
    df["is_holiday"]  = df["date"].apply(is_holiday)
    df["month"]       = df["date"].dt.month
    df["year"]        = df["date"].dt.year
    df["covid_dummy"] = (df["date"] >= pd.Timestamp(COVID_DATE)).astype(int)
    return df


def validate(df: pd.DataFrame) -> None:
    assert df["station"].nunique() == 4, f"역 수 오류: {df['station'].nunique()}"
    core_cols = ["boarding", "alighting", "total"]
    nulls = df[core_cols].isnull().sum().sum()
    assert nulls == 0, f"null 존재: {nulls}"
    print("  검증 OK — 4개역, null=0")


def main() -> None:
    ensure_dirs()

    df = load_raw()
    df = clean(df)
    df = interpolate_missing(df)
    df = add_features(df)

    # DatetimeIndex 설정 후 저장
    df = df.set_index("date").sort_index()

    validate(df)

    df.to_csv(OUTPUT_CSV)
    print(f"\n저장: {OUTPUT_CSV}")
    print(f"shape: {df.shape}  |  기간: {df.index.min().date()} ~ {df.index.max().date()}")
    print(df.dtypes)


if __name__ == "__main__":
    main()
