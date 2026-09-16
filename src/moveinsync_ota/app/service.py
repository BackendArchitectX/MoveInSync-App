from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from moveinsync_ota.alerts.builder import build_alert_candidates
from moveinsync_ota.alerts.models import AlertCandidate
from moveinsync_ota.compute.comparison import PeriodComparison, compare_periods
from moveinsync_ota.config import (
    DATA_DIR,
    DETERIORATION_THRESHOLD_PP,
    MONTH_FILES,
    T_SECONDS,
    VOL_MIN,
)
from moveinsync_ota.data.loader import load_all_files
from moveinsync_ota.data.schema import PeriodLoadResult

SUPPORTED_COMPARISONS: dict[str, tuple[str, str]] = {
    "may-june": ("May", "June"),
    "june-july": ("June", "July"),
}


@dataclass
class AgentRun:
    run_id: str
    prior_period: str
    current_period: str
    status: str
    eligible_vendor_count: int = 0
    breach_count: int = 0
    candidate_count: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class OTAService:
    def __init__(self) -> None:
        self._periods: dict[str, PeriodLoadResult] = {}
        self._comparisons: dict[str, PeriodComparison] = {}
        self._candidates: dict[str, list[AlertCandidate]] = {}
        self._feed: dict[str, AlertCandidate] = {}
        self._runs: list[AgentRun] = []

    def load(self, _periods: list[PeriodLoadResult] | None = None) -> None:
        if _periods is not None:
            results = _periods
        else:
            results = load_all_files(DATA_DIR, MONTH_FILES, T_SECONDS)
        self._periods = {r.period: r for r in results}

    def replay(self, comparison_key: str) -> AgentRun:
        if comparison_key not in SUPPORTED_COMPARISONS:
            raise ValueError(
                f"Unsupported comparison '{comparison_key}'. "
                f"Supported: {sorted(SUPPORTED_COMPARISONS)}"
            )
        prior_name, current_name = SUPPORTED_COMPARISONS[comparison_key]
        started_at = datetime.now(timezone.utc)

        missing = [p for p in (prior_name, current_name) if p not in self._periods]
        if missing:
            raise ValueError(
                f"Period(s) not loaded for '{comparison_key}': {missing}. "
                "Call load() before replay()."
            )

        comparison = compare_periods(
            self._periods[prior_name],
            self._periods[current_name],
            VOL_MIN,
            DETERIORATION_THRESHOLD_PP,
        )
        candidates = build_alert_candidates(comparison)

        self._comparisons[comparison_key] = comparison
        self._candidates[comparison_key] = candidates
        for c in candidates:
            self._feed[c.alert_id] = c

        run_id = hashlib.sha256(comparison_key.encode()).hexdigest()[:16]
        run = AgentRun(
            run_id=run_id,
            prior_period=prior_name,
            current_period=current_name,
            status="complete",
            eligible_vendor_count=len(comparison.eligible_vendor_ids),
            breach_count=comparison.breach_count,
            candidate_count=len(candidates),
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
        self._runs.append(run)
        return run

    def get_alert(self, alert_id: str) -> AlertCandidate | None:
        return self._feed.get(alert_id)

    def get_candidates(self, comparison_key: str) -> list[AlertCandidate]:
        return self._candidates.get(comparison_key, [])

    def get_comparison(self, comparison_key: str) -> PeriodComparison | None:
        return self._comparisons.get(comparison_key)

    def get_latest_run(self, comparison_key: str) -> AgentRun | None:
        key = comparison_key.lower()
        matches = [
            r for r in self._runs
            if f"{r.prior_period.lower()}-{r.current_period.lower()}" == key
        ]
        return matches[-1] if matches else None
