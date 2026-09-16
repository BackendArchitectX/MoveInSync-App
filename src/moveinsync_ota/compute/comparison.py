from __future__ import annotations

from dataclasses import dataclass

from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg
from moveinsync_ota.compute.volume import apply_volume_filter
from moveinsync_ota.compute.ota import vendor_ota_pct, fleet_ota_pct
from moveinsync_ota.compute.delay_context import DelayReasonContext, build_delay_context


@dataclass
class VendorComparison:
    vendor_id: str
    prior_period: str
    current_period: str
    prior_ota_pct: float
    current_ota_pct: float
    ota_pp_change: float
    prior_total_count: int
    current_total_count: int
    delay_context: DelayReasonContext
    is_deterioration: bool


@dataclass
class PeriodComparison:
    prior_period: str
    current_period: str
    t_seconds: int
    vol_min: int
    deterioration_threshold_pp: float
    eligible_vendor_ids: frozenset[str]
    fleet_prior_ota_pct: float
    fleet_current_ota_pct: float
    fleet_ota_pp_change: float
    vendor_comparisons: dict[str, VendorComparison]
    deteriorated_vendor_ids: frozenset[str]
    breach_count: int
    breach_pct: float


def compare_periods(
    prior: PeriodLoadResult,
    current: PeriodLoadResult,
    vol_min: int,
    deterioration_threshold_pp: float,
) -> PeriodComparison:
    if prior.t_seconds != current.t_seconds:
        raise ValueError(
            f"t_seconds mismatch: prior '{prior.period}' uses {prior.t_seconds}s "
            f"but current '{current.period}' uses {current.t_seconds}s"
        )
    eligible_ids = apply_volume_filter(prior, current, vol_min)

    vendor_comparisons: dict[str, VendorComparison] = {}
    for vendor_id in eligible_ids:
        prior_agg: VendorPeriodAgg = prior.vendor_stats[vendor_id]
        current_agg: VendorPeriodAgg = current.vendor_stats[vendor_id]

        prior_ota = vendor_ota_pct(prior_agg)
        current_ota = vendor_ota_pct(current_agg)
        pp_change = current_ota - prior_ota
        is_det = pp_change < -deterioration_threshold_pp
        delay_ctx = build_delay_context(current_agg)

        vendor_comparisons[vendor_id] = VendorComparison(
            vendor_id=vendor_id,
            prior_period=prior.period,
            current_period=current.period,
            prior_ota_pct=prior_ota,
            current_ota_pct=current_ota,
            ota_pp_change=pp_change,
            prior_total_count=prior_agg.total_count,
            current_total_count=current_agg.total_count,
            delay_context=delay_ctx,
            is_deterioration=is_det,
        )

    f_prior = fleet_ota_pct(prior.vendor_stats, eligible_ids)
    f_current = fleet_ota_pct(current.vendor_stats, eligible_ids)

    deteriorated = frozenset(
        v for v, vc in vendor_comparisons.items() if vc.is_deterioration
    )
    breach_count = len(deteriorated)
    breach_pct = breach_count / len(eligible_ids) * 100.0 if eligible_ids else 0.0

    return PeriodComparison(
        prior_period=prior.period,
        current_period=current.period,
        t_seconds=prior.t_seconds,
        vol_min=vol_min,
        deterioration_threshold_pp=deterioration_threshold_pp,
        eligible_vendor_ids=eligible_ids,
        fleet_prior_ota_pct=f_prior,
        fleet_current_ota_pct=f_current,
        fleet_ota_pp_change=f_current - f_prior,
        vendor_comparisons=vendor_comparisons,
        deteriorated_vendor_ids=deteriorated,
        breach_count=breach_count,
        breach_pct=breach_pct,
    )
