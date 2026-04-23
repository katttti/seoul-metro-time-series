"""
03_eda.py — 탐색적 데이터 분석 (EDA)

입력:
  data/processed/subway_line2_daily.csv

출력:
  outputs/figures/fig01_timeseries_overview.png
  outputs/figures/fig02_monthly_heatmap.png
  outputs/figures/fig03_weekday_boxplot.png
  outputs/figures/fig04_mon_fri_ratio.png
  outputs/tables/descriptive_stats.csv

실행:
  python src/03_eda.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import (
    PROCESSED_DIR, FIGURES_DIR, TABLES_DIR,
    TARGET_STATIONS, COVID_DATE, set_plot_style, save_fig, ensure_dirs
)

INPUT_CSV = PROCESSED_DIR / "subway_line2_daily.csv"
COVID_TS  = pd.Timestamp(COVID_DATE)
DOW_LABELS = ["월", "화", "수", "목", "금", "토", "일"]


def load() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV, index_col="date", parse_dates=True)
    print(f"로드: {df.shape}  {df.index.min().date()} ~ {df.index.max().date()}")
    return df


# ── fig01: 4개 역 시계열 오버뷰 ──────────────────────────────────────────────────
def fig01_timeseries(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)
    fig.suptitle("서울 지하철 2호선 주요 역 일별 총 승하차 (2018–2024)", fontsize=14, y=1.01)

    for ax, station in zip(axes, TARGET_STATIONS):
        sub = df[df["station"] == station]["total"]
        ax.plot(sub.index, sub.values, linewidth=0.8, alpha=0.85, label=station)
        ax.axvline(COVID_TS, color="red", linestyle="--", linewidth=1.2, alpha=0.7, label="COVID 기준")
        ax.set_ylabel("승하차 합계", fontsize=9)
        ax.set_title(station, fontsize=10, pad=3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e4:.0f}만"))

    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    save_fig("fig01_timeseries_overview.png")
    plt.close()


# ── fig02: 역×연월 히트맵 ─────────────────────────────────────────────────────
def fig02_heatmap(df: pd.DataFrame) -> None:
    pivot = (
        df.assign(ym=df.index.to_period("M").astype(str))
          .groupby(["station", "ym"])["total"]
          .mean()
          .unstack("station")
          [TARGET_STATIONS]  # 역 순서 고정
    )

    fig, ax = plt.subplots(figsize=(20, 5))
    sns.heatmap(
        pivot.T / 1e4,
        cmap="YlOrRd",
        ax=ax,
        linewidths=0,
        cbar_kws={"label": "평균 승하차 (만)"},
    )
    # COVID 기준 수직선 (ym 인덱스 위치)
    ym_list = list(pivot.index)
    covid_ym = COVID_TS.to_period("M").strftime("%Y-%m")
    if covid_ym in ym_list:
        ax.axvline(ym_list.index(covid_ym), color="blue", linewidth=1.5, linestyle="--", alpha=0.7)

    # x축 연도만 표시
    years = sorted({ym[:4] for ym in ym_list})
    tick_pos = [ym_list.index(f"{y}-01") for y in years if f"{y}-01" in ym_list]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(years, rotation=0)
    ax.set_title("역별 연월 평균 승하차 히트맵", fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.tight_layout()
    save_fig("fig02_monthly_heatmap.png")
    plt.close()


# ── fig03: COVID 전/후 요일 박스플롯 (강남역) ────────────────────────────────────
def fig03_weekday_boxplot(df: pd.DataFrame) -> None:
    station = "강남"
    sub = df[df["station"] == station].copy()
    sub["period"] = sub.index.map(lambda d: "Post-COVID" if d >= COVID_TS else "Pre-COVID")
    sub["요일"] = sub["day_of_week"].map(lambda x: DOW_LABELS[x])
    sub["요일"] = pd.Categorical(sub["요일"], categories=DOW_LABELS, ordered=True)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    fig.suptitle(f"{station}역 — COVID 전/후 요일별 총 승하차 분포", fontsize=13)

    for ax, period in zip(axes, ["Pre-COVID", "Post-COVID"]):
        data = sub[sub["period"] == period]
        sns.boxplot(data=data, x="요일", y="total", ax=ax, palette="muted",
                    order=DOW_LABELS, flierprops={"marker": ".", "markersize": 3})
        ax.set_title(period, fontsize=11)
        ax.set_xlabel("")
        ax.set_ylabel("승하차 합계" if ax == axes[0] else "")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e4:.0f}만"))

    plt.tight_layout()
    save_fig("fig03_weekday_boxplot.png")
    plt.close()


# ── fig04: 연도별 월/금 비율 (강남역) ────────────────────────────────────────────
def fig04_mon_fri_ratio(df: pd.DataFrame) -> None:
    station = "강남"
    sub = df[df["station"] == station].copy()

    yearly = []
    for year, grp in sub.groupby("year"):
        mon = grp[grp["day_of_week"] == 0]["total"].mean()
        fri = grp[grp["day_of_week"] == 4]["total"].mean()
        if fri > 0:
            yearly.append({"year": year, "ratio": mon / fri})

    ratio_df = pd.DataFrame(yearly)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(ratio_df["year"], ratio_df["ratio"], color="steelblue", alpha=0.8)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, label="비율=1 (동일)")
    ax.axvline(2020, color="red", linestyle="--", linewidth=1.2, alpha=0.7, label="COVID 기준")
    ax.set_xlabel("연도")
    ax.set_ylabel("월/금 평균 승하차 비율")
    ax.set_title(f"{station}역 — 연도별 월요일/금요일 평균 승하차 비율")
    ax.legend()
    plt.tight_layout()
    save_fig("fig04_mon_fri_ratio.png")
    plt.close()


# ── descriptive_stats.csv ─────────────────────────────────────────────────────
def save_descriptive_stats(df: pd.DataFrame) -> None:
    records = []
    for station in TARGET_STATIONS:
        sub = df[df["station"] == station]["total"]
        pre  = sub[sub.index < COVID_TS]
        post = sub[sub.index >= COVID_TS]
        for period, s in [("전체", sub), ("Pre-COVID", pre), ("Post-COVID", post)]:
            records.append({
                "역": station,
                "기간": period,
                "평균": round(s.mean()),
                "중앙값": round(s.median()),
                "표준편차": round(s.std()),
                "최솟값": int(s.min()),
                "최댓값": int(s.max()),
                "관측수": len(s),
            })

    out = TABLES_DIR / "descriptive_stats.csv"
    pd.DataFrame(records).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"  저장: {out}")


def main() -> None:
    ensure_dirs()
    set_plot_style()
    df = load()

    print("fig01 시계열...")
    fig01_timeseries(df)

    print("fig02 히트맵...")
    fig02_heatmap(df)

    print("fig03 요일 박스플롯...")
    fig03_weekday_boxplot(df)

    print("fig04 월/금 비율...")
    fig04_mon_fri_ratio(df)

    print("descriptive_stats.csv...")
    save_descriptive_stats(df)

    print("\n완료: fig01~04 + descriptive_stats.csv")


if __name__ == "__main__":
    main()
