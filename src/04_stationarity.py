"""
04_stationarity.py — 정상성 검정 (ADF, KPSS) + ACF/PACF

분석 대상: 강남역 total 계열

출력:
  outputs/figures/fig05_rolling_stats.png
  outputs/figures/fig06_acf_pacf_original.png
  outputs/figures/fig07_acf_pacf_differenced.png
  outputs/tables/stationarity_tests.csv

실행:
  python src/04_stationarity.py
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.stattools import adfuller, kpss

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import (
    PROCESSED_DIR, FIGURES_DIR, TABLES_DIR,
    COVID_DATE, set_plot_style, save_fig, ensure_dirs
)

INPUT_CSV    = PROCESSED_DIR / "subway_line2_daily.csv"
FOCUS_STATION = "강남"
COVID_TS      = pd.Timestamp(COVID_DATE)


def load_series() -> pd.Series:
    df = pd.read_csv(INPUT_CSV, index_col="date", parse_dates=True)
    s = df[df["station"] == FOCUS_STATION]["total"].sort_index()
    print(f"계열 로드: {FOCUS_STATION}역 total  {len(s)}일")
    return s


# ── ADF + KPSS 검정 ────────────────────────────────────────────────────────────
def run_tests(s: pd.Series, label: str) -> dict:
    # ADF (귀무: 단위근 있음 → 비정상)
    adf_stat, adf_p, _, _, adf_crit, _ = adfuller(s.dropna(), autolag="AIC")
    # KPSS (귀무: 정상)
    kpss_stat, kpss_p, _, kpss_crit = kpss(s.dropna(), regression="c", nlags="auto")

    result = {
        "계열":       label,
        "ADF 통계량":  round(adf_stat, 4),
        "ADF p값":     round(adf_p, 4),
        "ADF 결론":    "정상" if adf_p < 0.05 else "비정상",
        "KPSS 통계량": round(kpss_stat, 4),
        "KPSS p값":    round(kpss_p, 4),
        "KPSS 결론":   "정상" if kpss_p > 0.05 else "비정상",
    }
    print(f"  {label}: ADF p={adf_p:.4f} ({result['ADF 결론']}), KPSS p={kpss_p:.4f} ({result['KPSS 결론']})")
    return result


def save_stationarity_table(s: pd.Series) -> list[dict]:
    s_diff1   = s.diff().dropna()
    s_diff7   = s.diff(7).dropna()
    s_diff1_7 = s.diff().diff(7).dropna()

    series_list = [
        (s,          "원계열"),
        (s_diff1,    "1차 차분"),
        (s_diff7,    "계절 차분(7일)"),
        (s_diff1_7,  "1차+계절 차분"),
    ]

    records = [run_tests(ts, lbl) for ts, lbl in series_list]
    out = TABLES_DIR / "stationarity_tests.csv"
    pd.DataFrame(records).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"  저장: {out}")
    return records


# ── fig05: Rolling stats ──────────────────────────────────────────────────────
def fig05_rolling(s: pd.Series) -> None:
    roll = s.rolling(window=30)
    fig, axes = plt.subplots(3, 1, figsize=(16, 9), sharex=True)
    fig.suptitle(f"{FOCUS_STATION}역 총 승하차 — 원계열 + Rolling Statistics (window=30)", fontsize=13)

    axes[0].plot(s.index, s.values, linewidth=0.7, alpha=0.9, color="steelblue")
    axes[0].axvline(COVID_TS, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
    axes[0].set_ylabel("총 승하차")
    axes[0].set_title("원계열", fontsize=10)

    axes[1].plot(roll.mean().index, roll.mean().values, color="darkorange", linewidth=1.2)
    axes[1].axvline(COVID_TS, color="red", linestyle="--", linewidth=1.2, alpha=0.7)
    axes[1].set_ylabel("Rolling Mean")
    axes[1].set_title("30일 이동평균", fontsize=10)

    axes[2].plot(roll.std().index, roll.std().values, color="forestgreen", linewidth=1.2)
    axes[2].axvline(COVID_TS, color="red", linestyle="--", linewidth=1.2, alpha=0.7, label="COVID 기준")
    axes[2].set_ylabel("Rolling Std")
    axes[2].set_title("30일 이동표준편차", fontsize=10)
    axes[2].legend(fontsize=9)

    plt.tight_layout()
    save_fig("fig05_rolling_stats.png")
    plt.close()


# ── fig06: ACF/PACF 원계열 ────────────────────────────────────────────────────
def fig06_acf_original(s: pd.Series) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 8))
    fig.suptitle(f"{FOCUS_STATION}역 원계열 ACF / PACF (lags=60)", fontsize=13)

    plot_acf( s, ax=axes[0], lags=60, alpha=0.05, title="ACF — 원계열")
    plot_pacf(s, ax=axes[1], lags=60, alpha=0.05, title="PACF — 원계열", method="ywm")

    for ax in axes:
        # 7일 주기 수직선
        for lag in range(7, 61, 7):
            ax.axvline(lag, color="orange", linestyle=":", linewidth=0.8, alpha=0.6)

    plt.tight_layout()
    save_fig("fig06_acf_pacf_original.png")
    plt.close()


# ── fig07: ACF/PACF 차분 후 ───────────────────────────────────────────────────
def fig07_acf_differenced(s: pd.Series) -> None:
    s_d = s.diff().diff(7).dropna()

    fig, axes = plt.subplots(2, 1, figsize=(16, 8))
    fig.suptitle(f"{FOCUS_STATION}역 1차+계절 차분(7일) 후 ACF / PACF (lags=40)", fontsize=13)

    plot_acf( s_d, ax=axes[0], lags=40, alpha=0.05, title="ACF — 1차+계절 차분")
    plot_pacf(s_d, ax=axes[1], lags=40, alpha=0.05, title="PACF — 1차+계절 차분", method="ywm")

    for ax in axes:
        for lag in range(7, 41, 7):
            ax.axvline(lag, color="orange", linestyle=":", linewidth=0.8, alpha=0.6)

    # spike 주석 (lag=1, 7)
    for ax, lag_x, acf_y in [(axes[0], 1, None), (axes[0], 7, None)]:
        ax.annotate(f"lag={lag_x}", xy=(lag_x, 0), xytext=(lag_x + 1, 0.15),
                    fontsize=8, color="red",
                    arrowprops={"arrowstyle": "->", "color": "red", "lw": 0.8})

    plt.tight_layout()
    save_fig("fig07_acf_pacf_differenced.png")
    plt.close()


def main() -> None:
    ensure_dirs()
    set_plot_style()

    s = load_series()

    print("정상성 검정 테이블 저장 중...")
    save_stationarity_table(s)

    print("fig05 rolling stats...")
    fig05_rolling(s)

    print("fig06 ACF/PACF 원계열...")
    fig06_acf_original(s)

    print("fig07 ACF/PACF 차분 후...")
    fig07_acf_differenced(s)

    print("\n완료: fig05~07 + stationarity_tests.csv")


if __name__ == "__main__":
    main()
