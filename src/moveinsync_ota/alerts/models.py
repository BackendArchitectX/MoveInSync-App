from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlertCandidate:
    # Identity
    alert_id: str
    policy_version: str
    vendor_id: str
    prior_period: str
    current_period: str

    # Vendor evidence
    prior_ota_pct: float
    current_ota_pct: float
    ota_pp_change: float
    prior_total_count: int
    current_total_count: int

    # Delay context (from current period)
    total_late_count: int
    nodelay_count: int
    nodelay_share: float
    nodelay_dominates: bool
    top_non_nodelay_reason: str | None
    top_non_nodelay_count: int
    top_non_nodelay_share: float
    full_distribution: dict[str, int]

    # Fleet context
    fleet_prior_ota_pct: float
    fleet_current_ota_pct: float
    fleet_ota_pp_change: float
    eligible_vendor_count: int
    breach_count: int
    breach_pct: float

    # Configuration snapshot
    T_seconds: int
    vol_min: int
    deterioration_threshold_pp: float
