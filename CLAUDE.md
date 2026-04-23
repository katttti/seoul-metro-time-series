# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 목적

서울 지하철 2호선 주요 역(강남·잠실·신도림·홍대입구) 일별 승하차 시계열 데이터를 분석하여 COVID-19 전후 구조적 변화와 주간 계절성 패턴 변화를 검증하는 연구.

## 환경 설정

```bash
# 가상환경 활성화 (.venv, Python 3.14)
source .venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# API 키 설정 (코드에 절대 하드코딩 금지)
export SEOUL_API_KEY="your_key"  # 또는 .env 파일에 작성
```

## 실행 순서

```bash
python src/01_data_collection.py   # 최초 1회 (~10-30분, API 수집)
python src/02_preprocessing.py
python src/03_eda.py
python src/04_stationarity.py
python src/05_decomposition.py
# 2차 발표 이후:
python src/06_structural_break.py
python src/07_modeling.py
```

## 아키텍처

**`src/utils.py`** — 모든 스크립트가 공유하는 공통 유틸:
- `PROJECT_ROOT`, `RAW_DIR`, `PROCESSED_DIR`, `FIGURES_DIR`, `TABLES_DIR` 경로 상수
- `TARGET_STATIONS = ["강남", "잠실", "신도림", "홍대입구"]`
- `set_plot_style()` — NanumGothic 폰트, dpi=150
- `ensure_dirs()` — 출력 디렉토리 자동 생성

**데이터 흐름**:
```
서울 열린데이터광장 API (CardSubwayStatsNew)
  → data/raw/subway_raw_all.csv
  → data/processed/subway_line2_daily.csv  (전처리 완료, DatetimeIndex)
  → outputs/figures/fig{번호:02d}_{설명}.png
  → outputs/tables/{설명}.csv
```

**전처리 출력 스키마** (`subway_line2_daily.csv`):
- `date` (인덱스, datetime), `station`, `boarding`, `alighting`, `total`
- `day_of_week` (0=월~6=일), `is_weekend`, `is_holiday`, `month`, `year`

## 코드 작성 규칙

- 각 스크립트는 함수 기반 모듈 구조 + `if __name__ == "__main__":` 실행 블록
- 모든 플롯: `plt.savefig()` → `outputs/figures/` 저장
- 모든 테이블: `.to_csv()` → `outputs/tables/` 저장
- 플롯 파일명: `fig{번호:02d}_{영문설명}.png`
- COVID 분기점: `2020-03-01` (전처리 시 `covid_dummy` 파생변수 기준)
- 결측일 보간: 전후 동일 요일 평균 (요일 효과 보존)

## 핵심 분석 내용

| 스크립트 | 핵심 산출물 |
|---------|-----------|
| `03_eda.py` | fig01(시계열 전체), fig02(월별 히트맵), fig03(요일 박스플롯 전/후), fig04(월금 비율) |
| `04_stationarity.py` | ADF+KPSS 결과표, fig05(rolling stats), fig06-07(ACF/PACF) |
| `05_decomposition.py` | STL 분해(period=7, robust=True), fig08-09 |
| `06_structural_break.py` | Bai-Perron (ruptures), Chow Test |
| `07_modeling.py` | SARIMA(X), auto_arima(m=7), 최근 60일 홀드아웃 |

## API 주의사항

- `CardSubwayStatsNew` 엔드포인트: 한 번에 최대 1,000건 → 페이지네이션 필수
- 2호선 필터는 API 파라미터 아님 — Python에서 후처리
- rate limit: `time.sleep(0.5)`, HTTP 에러 시 3회 재시도 (exponential backoff)
- 실패 날짜 → `data/raw/failed_dates.txt` 기록
