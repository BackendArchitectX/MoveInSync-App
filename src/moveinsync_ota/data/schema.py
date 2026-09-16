from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class VendorPeriodAgg:
    vendor_id: str
    period: str
    total_count: int = 0
    ontime_count: int = 0
    late_delay_reason_counts: Counter[str] = field(default_factory=Counter)


@dataclass
class PeriodLoadResult:
    period: str
    total_rows: int
    spot20_excluded: int
    null_epoch_excluded: int
    eligible_rows: int
    vendor_stats: dict[str, VendorPeriodAgg]
