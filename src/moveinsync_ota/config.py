import os
from pathlib import Path

T_SECONDS: int = 300

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR: Path = (
    Path(os.environ["MIS_DATA_DIR"])
    if "MIS_DATA_DIR" in os.environ
    else _REPO_ROOT / "input" / "dataset" / "raw" / "MoveInSynch Anonymized Trip Log Dataset"
)

MONTH_FILES: dict[str, str] = {
    "May": "Ride_data _trip-may_2026.csv",
    "June": "Ride_data _trip-June_2026.csv",
    "July": "Ride_data _trip-July_2026.csv",
}

VOL_MIN: int = 500
DETERIORATION_THRESHOLD_PP: float = 5.0
