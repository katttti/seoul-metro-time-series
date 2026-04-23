"""
utils.py — 공통 경로 상수, 플롯 스타일, 디렉토리 초기화
모든 분석 스크립트가 이 모듈을 import해서 사용한다.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# ── 경로 상수 ──────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).parent.parent
RAW_DIR       = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR   = PROJECT_ROOT / "outputs" / "figures"
TABLES_DIR    = PROJECT_ROOT / "outputs" / "tables"

# ── 분석 대상 ──────────────────────────────────────────────────────────────────
TARGET_STATIONS = ["강남", "잠실", "신도림", "홍대입구"]
# 원시 역명 → 분석용 약칭 매핑 (전처리에서 사용)
RAW_STATION_FILTER = ["강남", "잠실(송파구청)", "신도림", "홍대입구"]
STATION_RENAME     = {"잠실(송파구청)": "잠실"}
COVID_DATE      = "2020-03-01"   # 코로나 구조 변화 기준일

# ── 한글 폰트 탐색 (NanumGothic 우선, 없으면 AppleGothic, 없으면 기본) ──────────
def _resolve_korean_font() -> str:
    candidates = ["NanumGothic", "NanumBarunGothic", "AppleGothic", "Malgun Gothic"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return plt.rcParams["font.family"]  # 폴백: 기본 폰트


# ── 플롯 스타일 ────────────────────────────────────────────────────────────────
def set_plot_style() -> None:
    """전역 matplotlib/seaborn 스타일 설정. 모든 스크립트 상단에서 호출."""
    font = _resolve_korean_font()
    plt.rcParams.update({
        "font.family":        font,
        "axes.unicode_minus": False,
        "figure.figsize":     (14, 6),
        "figure.dpi":         150,
        "savefig.bbox":       "tight",
        "axes.spines.top":    False,
        "axes.spines.right":  False,
    })
    sns.set_palette("muted")


# ── 디렉토리 초기화 ────────────────────────────────────────────────────────────
def ensure_dirs() -> None:
    """분석에 필요한 출력 디렉토리를 없으면 생성한다."""
    for d in [RAW_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── 플롯 저장 헬퍼 ────────────────────────────────────────────────────────────
def save_fig(filename: str) -> None:
    """FIGURES_DIR에 PNG 저장. filename 예: 'fig01_timeseries_overview.png'"""
    path = FIGURES_DIR / filename
    plt.savefig(path)
    print(f"  저장: {path}")


if __name__ == "__main__":
    ensure_dirs()
    set_plot_style()
    print("utils OK")
    print(f"  PROJECT_ROOT : {PROJECT_ROOT}")
    print(f"  RAW_DIR      : {RAW_DIR}")
    print(f"  PROCESSED_DIR: {PROCESSED_DIR}")
    print(f"  FIGURES_DIR  : {FIGURES_DIR}")
    print(f"  TABLES_DIR   : {TABLES_DIR}")
    print(f"  한글 폰트     : {_resolve_korean_font()}")
