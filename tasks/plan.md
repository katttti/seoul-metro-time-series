# 분석 파이프라인 구현 계획

## 의존성 그래프

```
utils.py (독립)
  └── 01_data_collection.py
        └── 02_preprocessing.py
              ├── 03_eda.py           (1차 발표)
              ├── 04_stationarity.py  (1차 발표)
              ├── 05_decomposition.py (1차 발표)
              ├── 06_structural_break.py  [2차]
              └── 07_modeling.py          [2차]
```

`03`, `04`, `05`는 `02` 이후 상호 독립 → 순서 무관.

---

## TASK 0 — Foundation: utils.py

**목적**: 모든 스크립트의 공통 의존성 먼저 구축.

**구현 내용:**
- 경로 상수: `PROJECT_ROOT`, `RAW_DIR`, `PROCESSED_DIR`, `FIGURES_DIR`, `TABLES_DIR`
- `TARGET_STATIONS = ["강남", "잠실", "신도림", "홍대입구"]`
- `COVID_DATE = "2020-03-01"`
- `set_plot_style()`: NanumGothic 폰트, `axes.unicode_minus=False`, dpi=150
- `ensure_dirs()`: 4개 출력 디렉토리 자동 생성
- `requirements.txt` 오타 수정 (`requirement.txt` → `requirements.txt`)
- `.env.example` 생성

**검증:** `python -c "from src.utils import ensure_dirs; ensure_dirs(); print('OK')"`

---

## TASK 1 — 01_data_collection.py

**목적**: 서울 열린데이터광장 API → raw CSV.

**구현 내용:**
- `python-dotenv` `load_dotenv()` → `SEOUL_API_KEY` 읽기
- URL: `http://openapi.seoul.go.kr:8088/{KEY}/json/CardSubwayStatsNew/{start}/{end}/{YYYYMMDD}`
- 날짜 루프: `pd.date_range('2018-01-01', today)`
- 페이지네이션: start=1, end=1000 → totalCount 체크 → 반복
- `time.sleep(0.5)` + 3회 재시도 exponential backoff
- 재개 가능: 기존 CSV에 있는 날짜 skip
- 저장: `data/raw/subway_raw_all.csv`
- 실패 로그: `data/raw/failed_dates.txt`

**검증:** 단일 날짜 테스트 모드로 실행, CSV row > 0 확인.

---

## CHECKPOINT A — raw 데이터 존재 확인

`data/raw/subway_raw_all.csv` row count, 날짜 범위 확인 후 Task 2 진행.

---

## TASK 2 — 02_preprocessing.py

**목적**: raw CSV → 분석용 처리 데이터.

**구현 내용 (PROJECT.md §4.1 Step 1-9):**

| Step | 내용 |
|------|------|
| 1 | 컬럼 한글→영문 매핑 |
| 2 | date → datetime, DatetimeIndex 설정 |
| 3 | `line == '2호선'` 필터 |
| 4 | `(date, station)` 중복 제거 |
| 5 | TARGET_STATIONS 서브셋 |
| 6 | 결측 날짜: 동일 요일 평균 보간 |
| 7 | `is_holiday` 플래그 (`holidays` 패키지 또는 한국 공휴일 하드코딩) |
| 8 | `total`, `day_of_week`, `is_weekend`, `month`, `year` 파생 |
| 9 | `data/processed/subway_line2_daily.csv` 저장 |

**검증:**
- `df.shape[1] == 10` (출력 스키마 컬럼 수)
- `df.isnull().sum()` → 0 (core 컬럼)
- `df['station'].nunique() == 4`

---

## CHECKPOINT B — processed 데이터 검증

강남 2020-03-01 행 존재 + total > 0 확인. 이후 03/04/05 독립 개발 가능.

---

## TASK 3 — 03_eda.py (1차 발표 핵심)

**산출물:**
- `outputs/tables/descriptive_stats.csv` — 역별 기초통계 + pre/post COVID 분리
- `fig01_timeseries_overview.png` — 4행 서브플롯, 2020-03-01 빨간 점선
- `fig02_monthly_heatmap.png` — 역×연월 평균 total 히트맵
- `fig03_weekday_boxplot.png` — pre/post COVID 요일 박스플롯 side-by-side
- `fig04_mon_fri_ratio.png` — 연도별 월요일/금요일 비율 추이

**검증:** 4 PNG + 1 CSV 존재; fig01에서 2020 급락 시각적 확인.

---

## TASK 4 — 04_stationarity.py (1차 발표)

**분석 대상**: 강남역 `total` 계열

**산출물:**
- `outputs/tables/stationarity_tests.csv` — ADF+KPSS 결과 (4개 계열)
- `fig05_rolling_stats.png` — 원계열 + rolling mean/std (window=30)
- `fig06_acf_pacf_original.png` — 원계열 ACF/PACF (lag=60)
- `fig07_acf_pacf_differenced.png` — 1차+계절차분 후 ACF/PACF (lag=40), spike 주석

**검증:** 차분 후 계열이 ADF p<0.05 + KPSS p>0.05 동시 충족.

---

## TASK 5 — 05_decomposition.py (1차 발표)

**산출물:**
- `fig08_stl_decomposition.png` — STL 4단 플롯 (강남역 전체 기간)
- `fig09_seasonal_amplitude.png` — 연간 계절 진폭 추이 (COVID 전후 비교)
- 터미널 출력: 2018-19 vs 2022-24 진폭 수치

**설정:** `STL(period=7, robust=True)`

**검증:** 2 PNG 존재; 진폭 플롯에서 2020 변화 가시적.

---

## CHECKPOINT C — 1차 발표 deliverables 완료

fig01~fig09 (9개) + descriptive_stats.csv + stationarity_tests.csv 존재 확인.

---

## TASK 6 — 06_structural_break.py (2차 발표)

**산출물:**
- Chow Test: F-statistic, p-value (2020-03-01 기준)
- Bai-Perron: `ruptures.Pelt(model='rbf')` 자동 분기점 탐지
- `fig10_structural_breaks.png` — 원계열 + 탐지된 분기점 수직선
- `outputs/tables/structural_break_results.csv`

**검증:** 2020-Q1 근방 분기점 탐지; Chow test p < 0.05.

---

## TASK 7 — 07_modeling.py (2차 발표)

**설정:**
- 훈련/테스트: 최근 60일 홀드아웃
- `pmdarima.auto_arima(seasonal=True, m=7, stepwise=True)`
- 수동 `SARIMA(1,1,1)(1,1,1,7)` 비교
- SARIMAX exog: `is_weekend`, `is_holiday`, `covid_dummy`
- 잔차 진단: Ljung-Box, QQ-plot, residual ACF

**산출물:**
- `fig11_forecast_vs_actual.png`
- `outputs/tables/model_metrics.csv` — RMSE/MAE/MAPE (SARIMA vs SARIMAX)

**검증:** holdout MAPE < 20%; Ljung-Box p > 0.05.

---

## 라이브러리 참조

| 용도 | 라이브러리 |
|------|-----------|
| 경로 | `pathlib.Path` |
| API 키 | `python-dotenv` |
| STL | `statsmodels.tsa.seasonal.STL` |
| ADF/KPSS | `statsmodels.tsa.stattools.adfuller, kpss` |
| ACF/PACF | `statsmodels.graphics.tsaplots.plot_acf, plot_pacf` |
| 구조변화 | `ruptures` |
| 자동 ARIMA | `pmdarima.arima.auto_arima` |
| 공휴일 | `holidays` 패키지 |

## 전체 실행 순서 (end-to-end 검증)

```bash
source .venv/bin/activate
export SEOUL_API_KEY="..."
python src/01_data_collection.py
python src/02_preprocessing.py
python src/03_eda.py
python src/04_stationarity.py
python src/05_decomposition.py
# 2차 발표:
python src/06_structural_break.py
python src/07_modeling.py
```

최종 산출물: fig01~fig11 (11개) + 4개 CSV 테이블.
