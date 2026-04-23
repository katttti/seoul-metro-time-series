"""
01_data_collection.py — 서울 열린데이터광장 CardSubwayStatsNew API 수집

출력:
  data/raw/subway_raw_all.csv   — 전체 수집 데이터 (누적 append)
  data/raw/failed_dates.txt     — 수집 실패 날짜 목록

환경변수:
  SEOUL_API_KEY  — 서울 열린데이터광장 인증키 (.env 또는 export)

실행:
  python src/01_data_collection.py                  # 전체 수집 (2018-01-01 ~ 오늘)
  python src/01_data_collection.py --test 20230101  # 단일 날짜 테스트
"""

import argparse
import time
import requests
import pandas as pd
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
import os
import sys

# 프로젝트 루트를 sys.path에 추가 (src/ 내부에서 utils import)
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import RAW_DIR, ensure_dirs

load_dotenv()

# ── 설정 ───────────────────────────────────────────────────────────────────────
BASE_URL      = "http://openapi.seoul.go.kr:8088"
SERVICE       = "CardSubwayStatsNew"
PAGE_SIZE     = 1000
SLEEP_SEC     = 0.5
MAX_RETRY     = 3
START_DATE    = "2018-01-01"
TARGET_LINE   = "2호선"          # API 경로 파라미터로 노선 필터
OUTPUT_CSV    = RAW_DIR / "subway_raw_all.csv"
FAILED_LOG    = RAW_DIR / "failed_dates.txt"

# API 응답 → 저장 컬럼 매핑
EXPECTED_COLS = ["USE_DT", "LINE_NUM", "SUB_STA_NM", "RIDE_PASGR_NUM", "ALIGHT_PASGR_NUM"]


# ── API 호출 ───────────────────────────────────────────────────────────────────
def fetch_page(api_key: str, date: str, start: int, end: int) -> dict:
    """단일 페이지 호출. HTTP 오류 시 exponential backoff으로 MAX_RETRY 재시도.

    URL 형식: /{key}/json/CardSubwayStatsNew/{start}/{end}/{YYYYMMDD}/{호선}
    호선 파라미터 없으면 API가 INFO-200 반환 (빈 결과).
    """
    line_encoded = quote(TARGET_LINE)
    url = f"{BASE_URL}/{api_key}/json/{SERVICE}/{start}/{end}/{date}/{line_encoded}"
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == MAX_RETRY:
                raise
            wait = 2 ** attempt
            print(f"    재시도 {attempt}/{MAX_RETRY} (대기 {wait}s): {e}")
            time.sleep(wait)


def collect_date(api_key: str, date_str: str) -> list[dict]:
    """하루치 전체 데이터를 페이지네이션으로 수집. 빈 날이면 [] 반환."""
    rows = []
    start = 1

    while True:
        end = start + PAGE_SIZE - 1
        data = fetch_page(api_key, date_str, start, end)

        # 응답 최상위 키 탐색 (서비스명 또는 오류키)
        if SERVICE not in data:
            # 데이터 없음 or API 오류
            result_code = data.get("RESULT", {}).get("CODE", "")
            if result_code in ("INFO-200", "INFO-100"):  # 정상 빈 결과
                break
            raise RuntimeError(f"API 오류 ({date_str}): {data}")

        payload     = data[SERVICE]
        total_count = int(payload.get("list_total_count", 0))
        page_rows   = payload.get("row", [])

        rows.extend(page_rows)

        if end >= total_count:
            break
        start = end + 1
        time.sleep(SLEEP_SEC)

    return rows


# ── 날짜 이미 수집됐는지 확인 ────────────────────────────────────────────────
def load_collected_dates() -> set[str]:
    if not OUTPUT_CSV.exists():
        return set()
    try:
        df = pd.read_csv(OUTPUT_CSV, usecols=["USE_DT"], dtype=str)
        return set(df["USE_DT"].dropna().unique())
    except Exception:
        return set()


# ── 메인 수집 루프 ─────────────────────────────────────────────────────────────
def run(date_list: list[str], api_key: str) -> None:
    ensure_dirs()

    collected = load_collected_dates()
    print(f"이미 수집된 날짜: {len(collected)}일")

    failed: list[str] = []
    new_rows: list[dict] = []

    for i, date_str in enumerate(date_list, 1):
        if date_str in collected:
            continue

        print(f"[{i}/{len(date_list)}] {date_str} 수집 중...", end=" ", flush=True)
        try:
            rows = collect_date(api_key, date_str)
            new_rows.extend(rows)
            print(f"{len(rows)}건")
        except Exception as e:
            print(f"실패: {e}")
            failed.append(date_str)

        time.sleep(SLEEP_SEC)

        # 500일마다 중간 저장 (메모리 관리)
        if len(new_rows) >= PAGE_SIZE * 10:
            _append_csv(new_rows)
            new_rows = []

    # 남은 행 저장
    if new_rows:
        _append_csv(new_rows)

    # 실패 로그
    if failed:
        with open(FAILED_LOG, "a") as f:
            f.write("\n".join(failed) + "\n")
        print(f"\n실패 날짜 {len(failed)}건 → {FAILED_LOG}")

    print(f"\n완료. 출력: {OUTPUT_CSV}")


def _append_csv(rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    # 필요한 컬럼만 유지 (없는 컬럼은 무시)
    cols = [c for c in EXPECTED_COLS if c in df.columns]
    df = df[cols]

    write_header = not OUTPUT_CSV.exists()
    df.to_csv(OUTPUT_CSV, mode="a", header=write_header, index=False)
    print(f"  → {len(df)}행 저장 (누적)")


# ── CLI ────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="서울 지하철 승하차 데이터 수집")
    parser.add_argument("--test", metavar="YYYYMMDD", help="단일 날짜만 테스트 수집")
    parser.add_argument("--start", default=START_DATE, help=f"수집 시작일 (기본: {START_DATE})")
    parser.add_argument("--end",   default=None,       help="수집 종료일 (기본: 오늘)")
    args = parser.parse_args()

    api_key = os.getenv("SEOUL_API_KEY", "")
    if not api_key:
        sys.exit("오류: SEOUL_API_KEY 환경변수가 없습니다. .env 파일 또는 export로 설정하세요.")

    if args.test:
        date_list = [args.test]
    else:
        end = args.end or pd.Timestamp.today().strftime("%Y-%m-%d")
        dates = pd.date_range(args.start, end, freq="D")
        date_list = [d.strftime("%Y%m%d") for d in dates]

    print(f"수집 대상: {len(date_list)}일 ({date_list[0]} ~ {date_list[-1]})")
    run(date_list, api_key)


if __name__ == "__main__":
    main()
