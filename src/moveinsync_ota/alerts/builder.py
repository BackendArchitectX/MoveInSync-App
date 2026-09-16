from __future__ import annotations

import hashlib
import json

from moveinsync_ota.alerts.models import AlertCandidate
from moveinsync_ota.compute.comparison import PeriodComparison

POLICY_VERSION = "ota-watchdog-v1"


def _compute_alert_id(vendor_id: str, comparison: PeriodComparison) -> str:
    identity = {
        "DETERIORATION_THRESHOLD_PP": comparison.deterioration_threshold_pp,
        "T_SECONDS": comparison.t_seconds,
        "VOL_MIN": comparison.vol_min,
        "current_period": comparison.current_period,
        "policy_version": POLICY_VERSION,
        "prior_period": comparison.prior_period,
        "vendor_id": vendor_id,
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_alert_candidates(comparison: PeriodComparison) -> list[AlertCandidate]:
    """Return one AlertCandidate per deteriorating vendor, sorted worst-first.

    Sort key: (ota_pp_change ASC, vendor_id ASC) — most negative change first,
    ties broken lexicographically by vendor_id.
    """
    t_seconds = comparison.t_seconds
    vol_min = comparison.vol_min
    deterioration_threshold_pp = comparison.deterioration_threshold_pp

    candidates: list[AlertCandidate] = []
    for vendor_id, vc in comparison.vendor_comparisons.items():
        if not vc.is_deterioration:
            continue

        alert_id = _compute_alert_id(vendor_id, comparison)
        dc = vc.delay_context
        candidates.append(
            AlertCandidate(
                alert_id=alert_id,
                policy_version=POLICY_VERSION,
                vendor_id=vendor_id,
                prior_period=comparison.prior_period,
                current_period=comparison.current_period,
                prior_ota_pct=vc.prior_ota_pct,
                current_ota_pct=vc.current_ota_pct,
                ota_pp_change=vc.ota_pp_change,
                prior_total_count=vc.prior_total_count,
                current_total_count=vc.current_total_count,
                total_late_count=dc.total_late_count,
                nodelay_count=dc.nodelay_count,
                nodelay_share=dc.nodelay_share,
                nodelay_dominates=dc.nodelay_dominates,
                top_non_nodelay_reason=dc.top_non_nodelay_reason,
                top_non_nodelay_count=dc.top_non_nodelay_count,
                top_non_nodelay_share=dc.top_non_nodelay_share,
                full_distribution=dict(dc.full_distribution),
                fleet_prior_ota_pct=comparison.fleet_prior_ota_pct,
                fleet_current_ota_pct=comparison.fleet_current_ota_pct,
                fleet_ota_pp_change=comparison.fleet_ota_pp_change,
                eligible_vendor_count=len(comparison.eligible_vendor_ids),
                breach_count=comparison.breach_count,
                breach_pct=comparison.breach_pct,
                T_seconds=t_seconds,
                vol_min=vol_min,
                deterioration_threshold_pp=deterioration_threshold_pp,
            )
        )

    candidates.sort(key=lambda c: (c.ota_pp_change, c.vendor_id))
    return candidates
