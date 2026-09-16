from __future__ import annotations

from moveinsync_ota.data.schema import VendorPeriodAgg


def vendor_ota_pct(agg: VendorPeriodAgg) -> float:
    """Return ontime percentage for a single vendor aggregation (full precision)."""
    if agg.total_count == 0:
        return 0.0
    return agg.ontime_count / agg.total_count * 100.0


def fleet_ota_pct(
    vendor_stats: dict[str, VendorPeriodAgg],
    eligible_ids: frozenset[str],
) -> float:
    """Return trip-weighted fleet OTA over the eligible vendor cohort.

    Never averages vendor percentages — sums raw counts across eligible vendors only.
    """
    total_ontime = sum(
        vendor_stats[v].ontime_count for v in eligible_ids if v in vendor_stats
    )
    total_trips = sum(
        vendor_stats[v].total_count for v in eligible_ids if v in vendor_stats
    )
    if total_trips == 0:
        return 0.0
    return total_ontime / total_trips * 100.0
