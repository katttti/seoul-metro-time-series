# TODO — 서울 지하철 2호선 분석 파이프라인

## 1차 발표 (필수)

- [x] **TASK 0** — `src/utils.py` 작성 + `requirements.txt` 오타 수정 + `.env.example`
- [x] **TASK 1** — `src/01_data_collection.py` (API 수집, 페이지네이션, 재시도, 2호선 경로파라미터)
- [ ] **CHECKPOINT A** — raw CSV 존재 및 날짜 범위 검증 ⚠️ API 키 재발급 필요 (현재 키 INFO-200 반환)
- [ ] **TASK 2** — `src/02_preprocessing.py` (정제, 보간, 파생변수)
- [ ] **CHECKPOINT B** — processed CSV 스키마 검증 (10 컬럼, null=0, 4개 역)
- [ ] **TASK 3** — `src/03_eda.py` → fig01~04 + descriptive_stats.csv
- [ ] **TASK 4** — `src/04_stationarity.py` → fig05~07 + stationarity_tests.csv
- [ ] **TASK 5** — `src/05_decomposition.py` → fig08~09
- [ ] **CHECKPOINT C** — fig01~09 + 2개 CSV 전부 존재 확인

## 2차 발표 (이후)

- [ ] **TASK 6** — `src/06_structural_break.py` → fig10 + structural_break_results.csv
- [ ] **TASK 7** — `src/07_modeling.py` → fig11 + model_metrics.csv

## 비고

- API 키: `SEOUL_API_KEY` 환경변수 또는 `.env` 파일
  - ⚠️ 현재 키(`5865505a...`) INFO-200 반환 — 서울 열린데이터광장에서 재발급 필요
  - URL: https://data.seoul.go.kr/dataList/OA-12252/S/1/datasetView.do
- API URL 형식: `/{key}/json/CardSubwayStatsNew/{start}/{end}/{YYYYMMDD}/2호선`
- COVID 분기점: `2020-03-01`
- 한글 폰트: NanumGothic (없으면 폴백 필요)
- 전체 실행 시간: 01_data_collection 최초 실행 10~30분 소요
