from __future__ import annotations

import csv
import logging
import time
from pathlib import Path
from typing import Iterable

from moveinsync_ota.data.normalise import parse_epoch, parse_delay_reason
from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg
from moveinsync_ota.exceptions import DataLoadError, SchemaValidationError

logger = logging.getLogger(__name__)

REQUIRED_HEADERS: frozenset[str] = frozenset(
    {"product_type", "planned_end_epoch", "actual_end_epoch", "vendor_id", "delay_reason"}
)


def validate_headers(fieldnames: list[str]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in fieldnames:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        raise SchemaValidationError(f"Duplicate column headers: {sorted(set(duplicates))}")
    missing = REQUIRED_HEADERS - seen
    if missing:
        raise SchemaValidationError(f"Missing required headers: {sorted(missing)}")


def parse_stream(
    rows: Iterable[dict],
    period: str,
    T_seconds: int,
) -> tuple[dict[str, VendorPeriodAgg], int, int, int]:
    """Return (vendor_stats, total_rows, spot20_excluded, null_epoch_excluded).

    Exclusion order (must match calibration exactly):
      1. SPOT_2.0 product_type
      2. null planned_end_epoch
      3. null actual_end_epoch
      -> eligible
    """
    vendor_stats: dict[str, VendorPeriodAgg] = {}
    total_rows = 0
    spot20_excluded = 0
    null_epoch_excluded = 0

    for row in rows:
        total_rows += 1

        # Step 1: exclude SPOT_2.0
        if str(row.get("product_type", "")).strip().upper() == "SPOT_2.0":
            spot20_excluded += 1
            continue

        # Step 2: exclude null planned_end_epoch
        planned_end = parse_epoch(row.get("planned_end_epoch", ""))
        if planned_end is None:
            null_epoch_excluded += 1
            continue

        # Step 3: exclude null actual_end_epoch
        actual_end = parse_epoch(row.get("actual_end_epoch", ""))
        if actual_end is None:
            null_epoch_excluded += 1
            continue

        # Eligible row — vendor_id is required; None-safe normalisation, fail fast
        raw_vendor = row.get("vendor_id")
        vendor_id = str(raw_vendor).strip() if raw_vendor is not None else ""
        if not vendor_id:
            raise DataLoadError(
                f"Blank or missing vendor_id at row {total_rows} in period '{period}'"
            )

        if vendor_id not in vendor_stats:
            vendor_stats[vendor_id] = VendorPeriodAgg(vendor_id=vendor_id, period=period)

        agg = vendor_stats[vendor_id]
        agg.total_count += 1

        is_ontime = actual_end <= planned_end + T_seconds
        if is_ontime:
            agg.ontime_count += 1
        else:
            delay_reason = parse_delay_reason(row.get("delay_reason", ""))
            agg.late_delay_reason_counts[delay_reason] += 1

    return vendor_stats, total_rows, spot20_excluded, null_epoch_excluded


def load_file(path: str | Path, period: str, T_seconds: int) -> PeriodLoadResult:
    path = Path(path)
    t0 = time.perf_counter()
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            validate_headers(list(reader.fieldnames or []))
            vendor_stats, total_rows, spot20_excluded, null_epoch_excluded = parse_stream(
                reader, period, T_seconds
            )
    except csv.Error as exc:
        raise DataLoadError(f"CSV parse error in {path}: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot open {path}: {exc}") from exc
    elapsed = time.perf_counter() - t0

    eligible_rows = total_rows - spot20_excluded - null_epoch_excluded
    logger.info(
        "%s: total=%d spot20=%d null_epoch=%d eligible=%d vendors=%d elapsed=%.2fs",
        period,
        total_rows,
        spot20_excluded,
        null_epoch_excluded,
        eligible_rows,
        len(vendor_stats),
        elapsed,
    )
    return PeriodLoadResult(
        period=period,
        t_seconds=T_seconds,
        total_rows=total_rows,
        spot20_excluded=spot20_excluded,
        null_epoch_excluded=null_epoch_excluded,
        eligible_rows=eligible_rows,
        vendor_stats=vendor_stats,
    )


def load_all_files(
    data_dir: Path,
    month_files: dict[str, str],
    T_seconds: int,
) -> list[PeriodLoadResult]:
    results = []
    for period, filename in month_files.items():
        results.append(load_file(data_dir / filename, period, T_seconds))
    return results
