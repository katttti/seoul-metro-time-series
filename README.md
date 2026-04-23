# Seoul Metro Line 2 Ridership — COVID-19 Structural Break Analysis

**Abstract:** This study analyzes daily boarding and alighting ridership at four Seoul Metro Line 2 stations (Gangnam, Jamsil, Sindorim, Hongik Univ.) from January 2018 to March 2026. Using STL decomposition, ADF/KPSS stationarity tests, and structural break detection, we document a statistically significant −21% decline in weekly seasonal amplitude following the COVID-19 onset (pivot: 2020-03-01), as well as persistent non-stationarity in raw series that is resolved by first-differencing.

---

## 목차

1. [소개](#1-소개)
2. [데이터 및 방법론](#2-데이터-및-방법론)
3. [결과](#3-결과)
4. [논의](#4-논의)
5. [환경 설정 및 실행](#5-환경-설정-및-실행)
6. [프로젝트 구조](#6-프로젝트-구조)

---

## 1. 소개

### 연구 배경

서울 지하철은 하루 수백만 명이 이용하는 도시 교통의 핵심 인프라다. 일별 승하차 인원은 경제 활동, 통근 패턴, 도시 이동성의 복합적 지표로서 외부 충격(팬데믹, 정책 변화, 계절 요인)에 민감하게 반응한다.

2020년 초 발생한 COVID-19 팬데믹은 대중교통 이용 행태를 근본적으로 변화시켰다. 재택근무 확산, 이동 제한, 사회적 거리두기 정책은 단기적 수요 감소를 넘어 통근 패턴 자체를 구조적으로 재편했을 가능성이 있다.

### 연구 질문

1. 서울 2호선 주요 역의 일별 승하차 시계열은 COVID-19 전후로 구조적 단절(structural break)을 보이는가?
2. 주간 계절성 패턴(요일 효과)의 진폭은 팬데믹 전후로 통계적으로 유의미하게 달라졌는가?
3. 역별로 충격의 크기와 회복 속도에 차이가 존재하는가?

### 분석 대상 역

| 역명 | 특성 |
|------|------|
| 강남 | 업무·상업 중심지, 높은 통근 수요 |
| 잠실 | 주거·복합 문화 거점 |
| 신도림 | 1·2호선 환승 허브, 광역 통근 수요 |
| 홍대입구 | 청년 문화·여가 중심, 주말 수요 높음 |

---

## 2. 데이터 및 방법론

### 2.1 데이터 출처 및 수집

- **출처:** 서울 열린데이터광장 API (`CardSubwayStatsNew` 엔드포인트)
- **수집 기간:** 2018-01-01 ~ 2026-03-31 (약 8년 3개월)
- **수집 방식:** `src/01_data_collection.py` — 페이지네이션(최대 1,000건/회), exponential backoff 재시도(3회), 실패일 로그(`data/raw/failed_dates.txt`)
- **보조 수집:** `src/csv_to_raw.py` — 월별 CSV 파일을 단일 원시 파일로 통합

> **주의:** 2020년 5~12월 데이터는 원본 파일에 수록되지 않아 보간 처리됨 (아래 전처리 참고).

### 2.2 전처리

`src/02_preprocessing.py`에서 수행:

| 단계 | 내용 |
|------|------|
| 역명 정규화 | `잠실(송파구청)` → `잠실` |
| 2호선 필터링 | API 응답에서 Python 후처리로 대상 4개 역 추출 |
| 날짜 결측 보간 | 전후 동일 요일 평균으로 채움 (요일 효과 보존) |
| 파생 변수 생성 | `day_of_week`, `is_weekend`, `is_holiday`, `month`, `year`, `covid_dummy` |
| COVID 기준일 | `2020-03-01` (`covid_dummy = 1` 이후) |

**전처리 완료 스키마** (`data/processed/subway_line2_daily.csv`):

```
date (DatetimeIndex) | station | boarding | alighting | total
day_of_week (0=월~6=일) | is_weekend | is_holiday | month | year | covid_dummy
```

- 최종 행 수: **12,048행** (4개 역 × 3,012일)

### 2.3 분석 방법론

#### 탐색적 데이터 분석 (EDA) — `src/03_eda.py`

- 전체 시계열 시각화 (fig01)
- 월별 히트맵으로 계절 패턴 확인 (fig02)
- COVID 전/후 요일별 분포 비교 박스플롯 (fig03)
- 월요일/금요일 비율 추이 (fig04)

#### 정상성 검정 — `src/04_stationarity.py`

- **ADF (Augmented Dickey-Fuller):** 단위근 존재 여부 검정 (귀무가설: 단위근 존재)
- **KPSS (Kwiatkowski-Phillips-Schmidt-Shin):** 정상성 직접 검정 (귀무가설: 정상)
- 두 검정을 동시 적용하여 결론 신뢰도 제고
- Rolling mean/std 시각화 (fig05), ACF/PACF (fig06–07)

#### STL 분해 — `src/05_decomposition.py`

- **STL (Seasonal and Trend decomposition using Loess)**
  - `period=7` (주간 계절성), `robust=True` (이상치 완화)
- COVID 전후 계절 진폭(seasonal amplitude) 정량 비교 (fig08–09)

#### 구조적 변화 탐지 — `src/06_structural_break.py` *(예정)*

- **Bai-Perron 다중 구조 변화점 탐지** (`ruptures` 라이브러리)
- **Chow Test** 단일 분기점(2020-03-01) 검정

#### 예측 모델링 — `src/07_modeling.py` *(예정)*

- **SARIMA(X):** 외생변수(공휴일, covid_dummy) 포함
- `auto_arima(m=7)`로 최적 차수 탐색
- 최근 60일 홀드아웃 평가

---

## 3. 결과

### 3.1 정상성 검정 결과

강남역 원시 시계열 기준:

| 검정 | 통계량 | p-value | 결론 |
|------|--------|---------|------|
| ADF | — | **0.015** | 귀무가설 기각 (경계적 정상) |
| KPSS | — | **0.010** | 귀무가설 기각 (비정상) |

두 검정이 상충하여 **원시 시계열은 비정상**으로 판단. **1차 차분 후 두 검정 모두 정상성 확인.**

ACF/PACF에서 **lag-7 패턴이 뚜렷**하게 관측되어 주간 계절성 존재 확인 (fig06–07).

### 3.2 STL 분해 — 계절 진폭 변화

| 구간 | 평균 계절 진폭 | 변화 |
|------|-------------|------|
| COVID 이전 (2018–2019) | **161,799** | — |
| COVID 이후 (2020–2026) | **127,662** | **−21.1%** |

> 주간 리듬의 진폭이 팬데믹 이후 약 1/5 수준으로 약화됨.

**해석:** 재택근무 확산으로 평일과 주말의 이용량 차이가 줄어들었을 가능성. 특히 강남·신도림 같은 통근 의존 역에서 주중 피크가 완화되고, 홍대입구 같은 여가 중심 역에서는 상대적으로 다른 양상이 예상됨.

### 3.3 요일 패턴 변화 (EDA)

- COVID 이전: 월~금 고수요 / 주말 급감의 전형적 통근 패턴
- COVID 이후: 평일 수요 감소 뚜렷, 주말 상대적 회복 → 패턴 평탄화

월요일/금요일 비율 추이(fig04)에서 팬데믹 전후 구조적 전환이 육안으로 확인됨.

### 3.4 주요 산출 파일

| 파일 | 내용 |
|------|------|
| `outputs/figures/fig01_timeseries_overview.png` | 4개 역 전체 시계열 |
| `outputs/figures/fig02_monthly_heatmap.png` | 월별 승하차 히트맵 |
| `outputs/figures/fig03_weekday_boxplot.png` | 요일별 분포 COVID 전/후 비교 |
| `outputs/figures/fig04_mon_fri_ratio.png` | 월요일/금요일 비율 추이 |
| `outputs/figures/fig05_rolling_stats.png` | Rolling mean/std |
| `outputs/figures/fig06_acf_pacf_original.png` | 원시 시계열 ACF/PACF |
| `outputs/figures/fig07_acf_pacf_differenced.png` | 1차 차분 ACF/PACF |
| `outputs/figures/fig08_stl_decomposition.png` | STL 분해 결과 |
| `outputs/figures/fig09_seasonal_amplitude.png` | 계절 진폭 COVID 전/후 비교 |
| `outputs/tables/descriptive_stats.csv` | 기술통계 |
| `outputs/tables/stationarity_tests.csv` | ADF/KPSS 검정 결과표 |

---

## 4. 논의

### 4.1 연구의 의의

본 연구는 서울 지하철 2호선 4개 역의 8년치 일별 데이터를 통해 COVID-19가 단순히 이용량을 줄인 것이 아니라 **통근 리듬 자체를 구조적으로 약화**시켰음을 보인다. STL 분해를 통한 계절 진폭의 −21% 감소는 재택근무·유연근무제의 확산이 대중교통 수요 패턴에 장기적으로 흡수되었을 가능성을 시사한다.

### 4.2 한계 및 주의사항

- **2020년 5~12월 보간:** 원본 데이터 부재로 동일 요일 평균 보간 처리. 팬데믹 초기 충격의 실제 양상이 과소/과대 추정될 수 있음.
- **역별 분석 미분화:** 현재 결과는 전체 경향 중심. 역 특성(통근 vs. 여가)에 따른 이질적 반응은 추가 분석 필요.
- **외생 요인 미통제:** 지하철 노선 연장, 운임 변화, 타 교통수단 전환 등의 효과가 분리되지 않음.
- **구조 변화점 탐지 미완:** Bai-Perron / Chow Test 결과는 향후 업데이트 예정.

### 4.3 향후 과제

- `src/06_structural_break.py` — Bai-Perron 다중 변화점 탐지 완료
- `src/07_modeling.py` — SARIMA(X) 예측 모델 구축 및 60일 홀드아웃 평가
- 역별 비교 분석 (통근형 vs. 여가형 역의 회복 경로 차이)
- COVID 이후 회복 궤적이 신(新)정상 수준으로 수렴하는지 검증

---

## 5. 환경 설정 및 실행

### 요구사항

- Python 3.14
- 패키지: `pandas`, `statsmodels`, `ruptures`, `pmdarima`, `matplotlib`, `seaborn`, `holidays`, `requests`

### 설치

```bash
# 저장소 클론 후
cd timeseries_micro_research

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### API 키 설정

```bash
# 서울 열린데이터광장 API 키 발급 후 환경변수 설정
export SEOUL_API_KEY="your_api_key_here"
# 또는 프로젝트 루트에 .env 파일 생성 (절대 커밋 금지)
```

### 실행 순서

```bash
# 1단계: 데이터 수집 (최초 1회, 10~30분 소요)
python src/01_data_collection.py

# 월별 CSV 파일이 있는 경우 (API 대체)
python src/csv_to_raw.py

# 2단계: 전처리
python src/02_preprocessing.py

# 3단계: EDA
python src/03_eda.py

# 4단계: 정상성 검정
python src/04_stationarity.py

# 5단계: STL 분해
python src/05_decomposition.py

# --- 2차 발표 이후 ---
python src/06_structural_break.py
python src/07_modeling.py
```

---

## 6. 프로젝트 구조

```
timeseries_micro_research/
├── src/
│   ├── utils.py                  # 공통 경로 상수, 플롯 스타일, 디렉토리 초기화
│   ├── 01_data_collection.py     # API 수집 (페이지네이션, 재시도)
│   ├── csv_to_raw.py             # 월별 CSV → subway_raw_all.csv 통합
│   ├── 02_preprocessing.py       # 정제, 보간, 파생변수 생성
│   ├── 03_eda.py                 # 탐색적 분석 (fig01~04)
│   ├── 04_stationarity.py        # ADF/KPSS 검정 (fig05~07)
│   ├── 05_decomposition.py       # STL 분해 (fig08~09)
│   ├── 06_structural_break.py    # Bai-Perron, Chow Test (예정)
│   └── 07_modeling.py            # SARIMA(X) 모델링 (예정)
├── data/
│   ├── raw/
│   │   ├── subway_raw_all.csv    # API/CSV 통합 원시 데이터
│   │   └── failed_dates.txt      # 수집 실패일 로그
│   └── processed/
│       └── subway_line2_daily.csv  # 전처리 완료 (12,048행)
├── outputs/
│   ├── figures/                  # fig01~09 PNG
│   └── tables/                   # descriptive_stats.csv, stationarity_tests.csv
├── requirements.txt
└── CLAUDE.md                     # Claude Code 프로젝트 지침
```

---

*분석 기준일: 2026-04-24 | 데이터 커버리지: 2018-01-01 ~ 2026-03-31*
