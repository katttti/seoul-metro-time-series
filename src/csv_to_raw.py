"""
csv_to_raw.py — 서울 열린데이터광장 월별 CSV → subway_raw_all.csv 변환

data/raw/CARD_SUBWAY_MONTH_*.csv (cp949 인코딩) 전체를 읽어
2호선 데이터만 필터링 후 subway_raw_all.csv로 저장.

사용법:
  python src/csv_to_raw.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import RAW_DIR, ensure_dirs

OUTPUT_CSV = RAW_DIR / "subway_raw_all.csv"

COLUMN_MAP = {
    "사용일자": "USE_DT",
    "노선명":   "LINE_NUM",
    "역명":     "SUB_STA_NM",
    "승차총승객수": "RIDE_PASGR_NUM",
    "하차총승객수": "ALIGHT_PASGR_NUM",
}


def load_csv(path: Path) -> pd.DataFrame:
    print(f"읽는 중: {path.name}")
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            df = pd.read_csv(
                path, encoding=enc, dtype=str,
                index_col=False, on_bad_lines="skip"
            )
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"인코딩 감지 실패: {path.name}")
    df.columns = [c.strip() for c in df.columns]

    # 컬럼 매핑
    df = df.rename(columns=COLUMN_MAP)

    expected = list(COLUMN_MAP.values())
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 없음 {missing}. 실제 컬럼: {list(df.columns)}")

    df = df[expected].copy()
    df["USE_DT"] = df["USE_DT"].astype(str).str.strip()
    df["RIDE_PASGR_NUM"]   = pd.to_numeric(df["RIDE_PASGR_NUM"],   errors="coerce").fillna(0).astype(int)
    df["ALIGHT_PASGR_NUM"] = pd.to_numeric(df["ALIGHT_PASGR_NUM"], errors="coerce").fillna(0).astype(int)

    # 2호선만
    df = df[df["LINE_NUM"] == "2호선"].reset_index(drop=True)
    print(f"  2호선 {len(df):,}행  날짜: {df['USE_DT'].min()} ~ {df['USE_DT'].max()}")
    return df


def main() -> None:
    ensure_dirs()

    csv_files = sorted(RAW_DIR.glob("CARD_SUBWAY_MONTH_*.csv"))
    if not csv_files:
        sys.exit("CARD_SUBWAY_MONTH_*.csv 파일을 data/raw/ 에서 찾을 수 없습니다.")

    print(f"CSV 파일 {len(csv_files)}개 발견\n")

    frames = [load_csv(p) for p in csv_files]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["USE_DT", "SUB_STA_NM"])
    combined = combined.sort_values(["USE_DT", "SUB_STA_NM"]).reset_index(drop=True)

    combined.to_csv(OUTPUT_CSV, index=False)
    print(f"\n저장 완료: {OUTPUT_CSV}")
    print(f"날짜 범위: {combined['USE_DT'].min()} ~ {combined['USE_DT'].max()}")
    print(f"역 목록: {sorted(combined['SUB_STA_NM'].unique())}")
    print(f"총 {len(combined):,}행")


if __name__ == "__main__":
    main()
