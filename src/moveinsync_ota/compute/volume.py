from __future__ import annotations

from moveinsync_ota.data.schema import PeriodLoadResult


def apply_volume_filter(
    prior: PeriodLoadResult,
    current: PeriodLoadResult,
    vol_min: int,
) -> frozenset[str]:
    """Return vendor IDs where BOTH prior and current periods have >= vol_min trips.

    Absent vendor in either period is treated as total_count=0 → ineligible.
    May→June eligibility is computed from May+June counts only; July is never read.
    """
    all_vendors = set(prior.vendor_stats.keys()) | set(current.vendor_stats.keys())
    eligible: set[str] = set()
    for vendor_id in all_vendors:
        prior_count = (
            prior.vendor_stats[vendor_id].total_count
            if vendor_id in prior.vendor_stats
            else 0
        )
        current_count = (
            current.vendor_stats[vendor_id].total_count
            if vendor_id in current.vendor_stats
            else 0
        )
        if prior_count >= vol_min and current_count >= vol_min:
            eligible.add(vendor_id)
    return frozenset(eligible)
