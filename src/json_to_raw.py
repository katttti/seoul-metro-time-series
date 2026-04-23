"""
json_to_raw.py — 서울 열린데이터광장 JSON 다운로드 파일 → subway_raw_all.csv 변환

사용법:
  python src/json_to_raw.py                              # 자동 탐색 (프로젝트 루트의 *.json)
  python src/json_to_raw.py "파일명.json"                # 특정 파일
  python src/json_to_raw.py "파일1.json" "파일2.json"    # 여러 파일 병합

JSON 컬럼 매핑:
  use_ymd            → USE_DT          (사용일자, YYYYMMDD)
  sbwy_rout_ln_nm    → LINE_NUM        (호선명)
  sbwy_stns_nm       → SUB_STA_NM     (역명)
  gton_tnope         → RIDE_PASGR_NUM  (승차총승객수)
  gtoff_tnope        → ALIGHT_PASGR_NUM(하차총승객수)

출력:
  data/raw/subway_raw_all.csv  (기존 파일 있으면 병합 후 중복 제거)
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import RAW_DIR, PROJECT_ROOT, ensure_dirs

OUTPUT_CSV = RAW_DIR / "subway_raw_all.csv"

COLUMN_MAP = {
    "use_ymd":         "USE_DT",
    "sbwy_rout_ln_nm": "LINE_NUM",
    "sbwy_stns_nm":    "SUB_STA_NM",
    "gton_tnope":      "RIDE_PASGR_NUM",
    "gtoff_tnope":     "ALIGHT_PASGR_NUM",
}
EXPECTED_COLS = list(COLUMN_MAP.values())


def load_json(path: Path) -> pd.DataFrame:
    print(f"읽는 중: {path.name}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # 구조 감지: {"DATA": [...]} 또는 {"CardSubwayStatsNew": {"row": [...]}} 형식
    if "DATA" in data:
        rows = data["DATA"]
    elif "CardSubwayStatsNew" in data:
        rows = data["CardSubwayStatsNew"].get("row", [])
    elif isinstance(data, list):
        rows = data
    else:
        # 최상위 값 중 list 찾기
        rows = next((v for v in data.values() if isinstance(v, list)), [])

    if not rows:
        print(f"  ⚠ 데이터 없음: {path.name}")
        return pd.DataFrame(columns=EXPECTED_COLS)

    df = pd.DataFrame(rows)

    # 소문자/대문자 컬럼 통합
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={k.lower(): v for k, v in COLUMN_MAP.items()})

    # 필요한 컬럼만
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 없음 {missing}. 실제 컬럼: {list(df.columns)}")

    df = df[EXPECTED_COLS].copy()
    df["USE_DT"] = df["USE_DT"].astype(str).str.strip()
    df["RIDE_PASGR_NUM"]   = pd.to_numeric(df["RIDE_PASGR_NUM"],   errors="coerce").fillna(0).astype(int)
    df["ALIGHT_PASGR_NUM"] = pd.to_numeric(df["ALIGHT_PASGR_NUM"], errors="coerce").fillna(0).astype(int)

    print(f"  {len(df):,}행  날짜: {df['USE_DT'].min()} ~ {df['USE_DT'].max()}")
    return df


def find_json_files() -> list[Path]:
    """프로젝트 루트에서 data/ .venv/ .claude/ 제외 JSON 파일 탐색."""
    exclude = {".venv", ".claude", ".vscode", "node_modules"}
    found = []
    for p in PROJECT_ROOT.iterdir():
        if p.suffix == ".json" and p.name not in exclude:
            found.append(p)
    return found


def merge_with_existing(new_df: pd.DataFrame) -> pd.DataFrame:
    if OUTPUT_CSV.exists():
        existing = pd.read_csv(OUTPUT_CSV, dtype=str)
        combined = pd.concat([existing, new_df.astype(str)], ignore_index=True)
        before = len(combined)
        combined = combined.drop_duplicates(subset=["USE_DT", "SUB_STA_NM"])
        print(f"  기존 {len(existing):,}행 + 신규 {len(new_df):,}행 → 중복 제거 후 {len(combined):,}행 ({before - len(combined):,}행 제거)")
        return combined
    return new_df


def main(args: list[str]) -> None:
    ensure_dirs()

    # JSON 파일 목록 결정
    if args:
        json_files = [Path(a) for a in args]
    else:
        json_files = find_json_files()
        if not json_files:
            sys.exit("JSON 파일을 찾을 수 없습니다. 파일 경로를 직접 지정하세요.")
        print(f"자동 탐색: {[f.name for f in json_files]}")

    # 로드 + 병합
    frames = [load_json(p) for p in json_files]
    new_df = pd.concat(frames, ignore_index=True)
    new_df = new_df.drop_duplicates(subset=["USE_DT", "SUB_STA_NM"])

    # 기존 CSV와 병합
    final_df = merge_with_existing(new_df)
    final_df = final_df.sort_values(["USE_DT", "LINE_NUM", "SUB_STA_NM"]).reset_index(drop=True)

    final_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n저장: {OUTPUT_CSV}")
    print(f"날짜 범위: {final_df['USE_DT'].min()} ~ {final_df['USE_DT'].max()}")
    print(f"총 {len(final_df):,}행")


if __name__ == "__main__":
    main(sys.argv[1:])
