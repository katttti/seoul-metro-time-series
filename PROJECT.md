# PROJECT.md — 서울 지하철 2호선 승하차 시계열 분석

## 프로젝트 개요

**제목**: 월요일의 무게 — 팬데믹 이후, 서울 지하철 2호선 통근은 어떻게 달라졌나  
**목적**: 서울 지하철 2호선 주요 역의 일별 승하차 시계열 데이터를 분석하여 COVID-19 전후 구조적 변화와 주간 계절성 패턴 변화를 검증한다.  
**산출물**: 분석 결과 + 5분 발표용 PPT (연구계획 + 기초 분석 결과 포함)

---

## 1. 프로젝트 구조

```
time-series-micro-research/
├── PROJECT.md                   # 이 파일 (Claude Code 프로젝트 가이드)
├── data/
│   ├── raw/                     # API에서 받은 원본 CSV/JSON
│   └── processed/               # 전처리 완료 데이터
├── src/
│   ├── 01_data_collection.py    # 데이터 수집
│   ├── 02_preprocessing.py      # 전처리 & 정제
│   ├── 03_eda.py                # EDA & 기초통계량
│   ├── 04_stationarity.py       # 정상성 검정 & ACF/PACF
│   ├── 05_decomposition.py      # 시계열 분해 (STL)
│   ├── 06_structural_break.py   # 구조적 변화 탐지 (2차 발표)
│   ├── 07_modeling.py           # SARIMA / SARIMAX (2차 발표)
│   └── utils.py                 # 공통 유틸 (경로 상수, 플롯 스타일, 한글 폰트)
├── outputs/
│   ├── figures/                 # 분석 플롯 PNG
│   └── tables/                  # 기초통계량·검정결과 CSV
└── requirements.txt
```

---

## 2. 환경 & 의존성

- **Python**: 3.10+
- **핵심 라이브러리**: pandas, numpy, matplotlib, seaborn, statsmodels, scipy, requests
- **선택 라이브러리**: ruptures (구조적 변화), pmdarima (auto_arima), scikit-learn (RMSE/MAPE)
- **API 키**: 환경변수 `SEOUL_API_KEY`에 저장 — 코드에 하드코딩 절대 금지
  - `.env` 파일 + `python-dotenv` 사용 또는 쉘 `export SEOUL_API_KEY="5865505a4a6b696d37356c4743584c"`

```
# requirements.txt 내용
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
seaborn>=0.12
statsmodels>=0.14
scipy>=1.10
requests>=2.28
python-dotenv>=1.0
ruptures>=1.1
pmdarima>=2.0
scikit-learn>=1.3
```

---

## 3. 데이터 수집 (01_data_collection.py)

### 3.1 데이터 소스

| 항목 | 값 |
|------|-----|
| 출처 | 서울 열린데이터광장 (data.seoul.go.kr) |
| API | `CardSubwayStatsNew` (지하철 승하차 인원 정보) |
| 형식 | REST API → JSON 응답 |
| 기간 | 2018-01-01 ~ 현재 가용 최신일 |
| 대상 노선 | 2호선 |
| 대상 역 | **전역 수집** → 분석 시 강남·잠실·신도림·홍대입구 4개 역 중심 |

### 3.2 API 호출 형식

```
http://openapi.seoul.go.kr:8088/{API_KEY}/json/CardSubwayStatsNew/{START_IDX}/{END_IDX}/{DATE}
```

- `{DATE}`: `20180101` 형식 (YYYYMMDD)
- 한 번에 최대 1,000건 반환 → 페이지네이션 필수
- 2호선 필터링은 응답 수신 후 Python에서 처리 (API 파라미터에 노선 필터 없음)

### 3.3 수집 전략

```
1. 날짜 리스트 생성: pd.date_range('2018-01-01', '2025-12-31')
2. 날짜별 API 호출:
   - start=1, end=1000 → 다음 페이지 확인 → 반복
   - rate limit 방지: time.sleep(0.5)
   - HTTP 에러 시 3회 재시도 (exponential backoff)
3. 응답 JSON 파싱:
   - 성공: row 데이터 추출 → DataFrame append
   - 실패: 해당 날짜를 failed_dates 리스트에 기록
4. 최종 저장: data/raw/subway_raw_all.csv
5. 실패 로그: data/raw/failed_dates.txt
```

### 3.4 주의사항

- API 일일 호출 한도 확인 — 대량 수집 시 **월 단위 묶어서 호출**하는 전략도 고려
- `CardSubwayStatsNew`의 정확한 응답 필드명은 첫 호출 후 확인하여 코드에 반영
- 공공 API 특성상 특정 날짜 데이터 누락 가능 → 결측 날짜 목록 별도 관리

---

## 4. 전처리 (02_preprocessing.py)

### 4.1 정제 파이프라인

```
Step 1: 컬럼명 매핑 (한글 → 영문)
   USE_DT → date | LINE_NUM → line | SUB_STA_NM → station
   RIDE_PASGR_NUM → boarding | ALIGHT_PASGR_NUM → alighting

Step 2: 타입 변환
   date: str → datetime → DatetimeIndex 설정
   boarding, alighting: int 변환

Step 3: 2호선 필터
   line == '2호선' 행만 추출

Step 4: 중복 제거
   (date, station) 기준 중복 확인 → 합산 또는 제거

Step 5: 대상 역 서브셋 생성
   강남, 잠실, 신도림, 홍대입구

Step 6: 결측 처리
   - 빠진 날짜 탐지: pd.date_range와 대조
   - 보간: 전후 동일 요일 평균 (요일 효과 보존)

Step 7: 이상치 플래깅
   - is_holiday: 공휴일/설/추석 (한국 공휴일 리스트 하드코딩 또는 holidays 패키지)
   - 극단 이벤트(폭설, 태풍): 수동 확인 후 is_extreme 플래그

Step 8: 파생변수 추가
   total = boarding + alighting
   day_of_week (0=월 ~ 6=일)
   is_weekend (토·일)
   month, year, quarter

Step 9: 저장
   data/processed/subway_line2_daily.csv
```

### 4.2 출력 데이터 스키마

| 컬럼 | 타입 | 설명 |
|------|------|------|
| date | datetime | 날짜 (인덱스) |
| station | str | 역명 |
| boarding | int | 승차 인원 |
| alighting | int | 하차 인원 |
| total | int | 승+하차 합계 |
| day_of_week | int | 0(월)~6(일) |
| is_weekend | bool | 주말 여부 |
| is_holiday | bool | 공휴일 여부 |
| month | int | 월 |
| year | int | 연도 |

---

## 5. 분석 파이프라인

---

### ★ Phase 1~3: 1차 발표 범위 (필수 완료)

---

#### Phase 1: EDA & 기초통계량 (03_eda.py)

**목표**: 데이터의 전체 특성 파악 + 시각적 패턴 확인

```
[통계 테이블]
• 역별 기초통계량: mean, std, min, max, median, skewness, kurtosis
• COVID 전(~2020-02-29) / 후(2020-03-01~) 분리 통계 비교

[시각화 — 최소 4개 플롯]
• fig01_timeseries_overview.png
  → 4개 역 일별 total 시계열 (서브플롯 4행)
  → 2020-03-01 수직선 (빨간 점선) + 사회적 거리두기 해제일 표시
  → 이 한 장이 발표 Slide 3의 핵심

• fig02_monthly_heatmap.png
  → 역(행) × 연-월(열) 평균 total 히트맵
  → 2020년 급락이 색상으로 한눈에 보이도록

• fig03_weekday_boxplot.png
  → 요일별(월~일) total 박스플롯
  → 좌: COVID 전, 우: COVID 후 (side-by-side)
  → 주간 계절성 + 팬데믹 효과 동시 시각화

• fig04_mon_fri_ratio.png
  → 연도별 월요일 평균 total / 금요일 평균 total 비율 추이
  → 재택 가설: "금요일 재택 증가 → 비율 상승?"

[출력]
• outputs/tables/descriptive_stats.csv
• outputs/figures/fig01 ~ fig04
```

---

#### Phase 2: 정상성 검정 & ACF/PACF (04_stationarity.py)

**목표**: 시계열의 정상성 여부 판단 + 자기상관 구조 파악

**분석 대상**: 강남역 `total` 계열 (대표 역), 나머지 역은 부록

```
[정상성 검정]
• ADF 검정 (Augmented Dickey-Fuller)
  - 원계열 / 1차 차분 / 계절 차분(lag=7) / 1차+계절 차분
  - 결과 테이블: test statistic, p-value, 1%/5%/10% critical values
  - 예상: 원계열은 비정상 → 1차+계절 차분 후 정상

• KPSS 검정 (보조 확인)
  - ADF와 교차 검증 (ADF: 단위근 존재 귀무가설 / KPSS: 정상성 귀무가설)

[자기상관 분석]
• fig06_acf_pacf_original.png
  → 원계열 ACF (lag=60): lag 7,14,21,28에 강한 spike 예상
  → 원계열 PACF (lag=60)

• fig07_acf_pacf_differenced.png
  → 1차 차분 + 계절 차분(7) 후 ACF/PACF (lag=40)
  → SARIMA 차수 후보 식별 근거 (q, Q 값)
  → spike 위치에 화살표 주석 추가

[보조 시각화]
• fig05_rolling_stats.png
  → 원계열 + rolling mean(window=30) + rolling std(window=30)
  → 비정상성의 시각적 증거

[출력]
• outputs/tables/stationarity_tests.csv (ADF·KPSS 결과 통합)
• outputs/figures/fig05 ~ fig07
```

---

#### Phase 3: 시계열 분해 (05_decomposition.py)

**목표**: Trend / Seasonal / Residual 분리, 계절성 변화 확인

```
[STL 분해]
• statsmodels.tsa.seasonal.STL 사용
  - period=7 (주간 계절성)
  - robust=True (이상치 영향 최소화)

[시각화]
• fig08_stl_decomposition.png
  → 4단 플롯: Observed / Trend / Seasonal / Residual
  → 강남역 기준, 전체 기간

• fig09_seasonal_amplitude.png
  → 계절 성분(seasonal component)의 연간 평균 진폭(amplitude) 추이
  → COVID 전(2018~2019) vs 후(2022~2024) 진폭 비교
  → "주간 계절성이 약해졌는가?"에 대한 정량적 답

[출력]
• outputs/figures/fig08, fig09
```

---

### ○ Phase 4~5: 2차 발표 범위 (1차 이후 확장)

---

#### Phase 4: 구조적 변화 탐지 (06_structural_break.py)

```
• Chow Test: 2020-03-01 기준 사전 분할 → F-test
• Bai-Perron (ruptures 라이브러리):
  - 알고리즘: Pelt 또는 BinSeg
  - cost function: 'rbf' 또는 'l2'
  - 분기점 자동 탐지 → 원계열 위에 수직선 시각화
• COVID 이외의 추가 분기점 발견 여부 확인 & 해석
```

#### Phase 5: SARIMA / SARIMAX (07_modeling.py)

```
• 훈련/테스트 분할: 최근 60일 홀드아웃
• auto_arima (pmdarima): seasonal=True, m=7, stepwise=True
• 수동 비교: SARIMA(1,1,1)(1,1,1,7) vs auto 결과
• 잔차 진단: Ljung-Box / QQ-plot / 잔차 ACF
• SARIMAX 확장 외생변수: is_weekend, is_holiday, covid_dummy
• 예측 성능: RMSE, MAE, MAPE + 실제 vs 예측 플롯
```

---

## 6. 코드 작성 규칙

### 6.1 공통 유틸 (src/utils.py)

```python
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# ── 경로 상수 ──
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR      = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR  = PROJECT_ROOT / "outputs" / "figures"
TABLES_DIR   = PROJECT_ROOT / "outputs" / "tables"

# ── 분석 대상 역 ──
TARGET_STATIONS = ["강남", "잠실", "신도림", "홍대입구"]

# ── 플롯 스타일 ──
def set_plot_style():
    plt.rcParams.update({
        'font.family': 'NanumGothic',  # 시스템에 설치된 한글 폰트
        'axes.unicode_minus': False,
        'figure.figsize': (14, 6),
        'figure.dpi': 150,
        'savefig.bbox': 'tight',
    })
    sns.set_palette("muted")

# ── 디렉토리 자동 생성 ──
def ensure_dirs():
    for d in [RAW_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR]:
        d.mkdir(parents=True, exist_ok=True)
```

### 6.2 스크립트 구조

- 각 파일은 **함수 기반** 모듈: 분석 로직을 함수로 분리
- 하단에 `if __name__ == "__main__":` 블록으로 실행
- 모든 플롯은 `plt.savefig()` → `outputs/figures/`에 저장 + `plt.show()` 선택
- 모든 테이블은 `.to_csv()` → `outputs/tables/`에 저장
- print문으로 주요 결과 요약 출력 (터미널 확인용)

### 6.3 네이밍 컨벤션

- 플롯: `fig{번호:02d}_{영문설명}.png` (예: `fig01_timeseries_overview.png`)
- 테이블: `{영문설명}.csv` (예: `descriptive_stats.csv`)

### 6.4 실행 순서

```bash
# 0. 환경 설정
pip install -r requirements.txt
export SEOUL_API_KEY="your_key"   # 또는 .env 파일에 작성

# 1. 데이터 수집 (최초 1회, ~10-30분)
python src/01_data_collection.py

# 2. 전처리
python src/02_preprocessing.py

# 3~5. 1차 발표 분석
python src/03_eda.py
python src/04_stationarity.py
python src/05_decomposition.py

# 6~7. 2차 발표 분석
python src/06_structural_break.py
python src/07_modeling.py
```

---

## 7. 1차 발표 PPT 구성 (5분, 6슬라이드)

| # | 슬라이드 | 시간 | 핵심 콘텐츠 | 사용 산출물 |
|---|---------|------|------------|-----------|
| 1 | 표지 | 10초 | 제목 + 한 줄 훅 ("매일 타는 2호선, 데이터는 뭐라고 말할까?") | — |
| 2 | Introduction | 45초 | 팬데믹 → 재택근무 → 통근 패턴 변화 가설 | 강남역 출근 이미지 |
| 3 | Data | 45초 | 출처·기간·변수 + **원계열 전체 플롯** (COVID 급락 강조) | fig01 |
| 4 | EDA 결과 | 60초 | 기초통계량 표 + 요일별 박스플롯(전/후) + 히트맵 | 통계표, fig02, fig03 |
| 5 | 정상성 & ACF | 90초 | ADF 결과표 + ACF/PACF + STL 분해 | fig06, fig07, fig08 |
| 6 | RQ & 계획 | 30초 | 연구질문 3개 + 향후 분석 로드맵 (구조변화→SARIMA→SARIMAX) | — |

---

## 8. Research Questions

1. **구조적 변화**: 2호선 주요 역의 일별 승하차는 COVID-19 전후로 통계적으로 유의한 구조적 변화(structural break)가 존재하는가?
2. **계절성 변화**: 주간 계절성(월~금 vs 주말)의 진폭이 팬데믹 이후 축소되었는가? (재택·하이브리드 근무 가설)
3. **예측 모형**: SARIMA(X) 모형으로 단기 예측 시, 외생변수(공휴일·COVID 더미) 추가가 예측 성능을 유의미하게 개선하는가?

---

## 9. 작업 체크리스트

### 1차 발표 (필수)

- [ ] `utils.py` 작성 (경로 상수, 플롯 스타일)
- [ ] `requirements.txt` 생성
- [ ] `01_data_collection.py` — API 수집 & raw 저장
- [ ] `02_preprocessing.py` — 정제 & processed 저장
- [ ] `03_eda.py` — 기초통계량 + fig01~04
- [ ] `04_stationarity.py` — ADF/KPSS + ACF/PACF + fig05~07
- [ ] `05_decomposition.py` — STL 분해 + fig08~09
- [ ] PPT 작성 (6슬라이드)

### 2차 발표 (이후)

- [ ] `06_structural_break.py` — Chow / Bai-Perron
- [ ] `07_modeling.py` — SARIMA / SARIMAX / 예측 평가
- [ ] PPT 업데이트
