"""
05_decomposition.py — STL 시계열 분해 + 계절 진폭 분석

분석 대상: 강남역 total 계열

출력:
  outputs/figures/fig08_stl_decomposition.png
  outputs/figures/fig09_seasonal_amplitude.png

실행:
  python src/05_decomposition.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import (
    PROCESSED_DIR, COVID_DATE, set_plot_style, save_fig, ensure_dirs
)

INPUT_CSV     = PROCESSED_DIR / "subway_line2_daily.csv"
FOCUS_STATION = "강남"
COVID_TS      = pd.Timestamp(COVID_DATE)
STL_PERIOD    = 7


def load_series() -> pd.Series:
    df = pd.read_csv(INPUT_CSV, index_col="date", parse_dates=True)
    s = df[df["station"] == FOCUS_STATION]["total"].sort_index().asfreq("D")
    # 소수 결측 보간 (STL은 NaN 불허)
    s = s.interpolate(method="time")
    print(f"계열 로드: {FOCUS_STATION}역 total  {len(s)}일  (결측: {s.isna().sum()})")
    return s


def run_stl(s: pd.Series):
    stl = STL(s, period=STL_PERIOD, robust=True)
    return stl.fit()


# ── fig08: STL 4단 분해 플롯 ──────────────────────────────────────────────────
def fig08_stl(s: pd.Series, result) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(f"{FOCUS_STATION}역 STL 분해 (period=7, robust=True)", fontsize=14)

    components = [
        (s,               "원계열",  "steelblue"),
        (result.trend,    "추세",    "darkorange"),
        (result.seasonal, "계절성",  "forestgreen"),
        (result.resid,    "잔차",    "gray"),
    ]

    for ax, (data, label, color) in zip(axes, components):
        ax.plot(data.index, data.values, linewidth=0.8, color=color, alpha=0.9)
        ax.axvline(COVID_TS, color="red", linestyle="--", linewidth=1.2, alpha=0.6, label="COVID 기준")
        ax.set_ylabel(label, fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e4:.0f}만" if abs(x) > 1e3 else f"{x:.0f}"))

    axes[0].legend(fontsize=8, loc="upper right")
    plt.tight_layout()
    save_fig("fig08_stl_decomposition.png")
    plt.close()


# ── fig09: 연간 계절 진폭 추이 ────────────────────────────────────────────────
def fig09_amplitude(result) -> None:
    seasonal = pd.Series(result.seasonal, index=result.seasonal.index if hasattr(result.seasonal, 'index') else None)
    if not hasattr(seasonal, 'index') or seasonal.index is None:
        # result.seasonal이 ndarray인 경우
        seasonal = pd.Series(result.seasonal.values if hasattr(result.seasonal, 'values') else result.seasonal,
                             index=pd.date_range(start="2018-01-01", periods=len(result.seasonal), freq="D"))

    # 연간 계절 진폭 = (연간 max - min)
    amp = (
        seasonal.groupby(seasonal.index.year)
                .apply(lambda g: g.max() - g.min())
                .rename("amplitude")
    )

    # 전후 기간 분리
    pre_years  = amp[amp.index < COVID_TS.year].index.tolist()
    post_years = amp[amp.index >= COVID_TS.year].index.tolist()

    print(f"\n계절 진폭 (연간 max-min)")
    print(f"  COVID 전 ({pre_years[0]}-{pre_years[-1]}): 평균 {amp[pre_years].mean():,.0f}")
    print(f"  COVID 후 ({post_years[0]}-{post_years[-1]}): 평균 {amp[post_years].mean():,.0f}")

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#e07b54" if y >= COVID_TS.year else "#4a90d9" for y in amp.index]
    bars = ax.bar(amp.index, amp.values, color=colors, alpha=0.85, edgecolor="white")

    ax.axvline(COVID_TS.year - 0.5, color="red", linestyle="--", linewidth=1.5, alpha=0.8, label="COVID 기준 (2020)")
    ax.set_xlabel("연도", fontsize=11)
    ax.set_ylabel("계절 진폭 (연간 max − min)", fontsize=11)
    ax.set_title(f"{FOCUS_STATION}역 연간 주간 계절 진폭 추이 (STL seasonal component)", fontsize=13)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e4:.1f}만"))

    # 범례 패치
    import matplotlib.patches as mpatches
    pre_patch  = mpatches.Patch(color="#4a90d9", alpha=0.85, label="Pre-COVID")
    post_patch = mpatches.Patch(color="#e07b54", alpha=0.85, label="Post-COVID")
    ax.legend(handles=[pre_patch, post_patch, plt.Line2D([], [], color="red",
              linestyle="--", label="COVID 기준")], fontsize=10)

    plt.tight_layout()
    save_fig("fig09_seasonal_amplitude.png")
    plt.close()


def main() -> None:
    ensure_dirs()
    set_plot_style()

    s = load_series()

    print("STL 분해 실행 중 (robust=True)...")
    result = run_stl(s)

    print("fig08 STL 분해 플롯...")
    fig08_stl(s, result)

    print("fig09 계절 진폭 추이...")
    fig09_amplitude(result)

    print("\n완료: fig08~09")


if __name__ == "__main__":
    main()
