"""Unit tests for compute.comparison — compare_periods."""
from collections import Counter

import pytest

from moveinsync_ota.compute.comparison import compare_periods
from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg


def make_period(
    period: str,
    vendor_data: dict[str, tuple[int, int, dict]],
    t_seconds: int = 300,
) -> PeriodLoadResult:
    """Build a PeriodLoadResult from {vendor_id: (total, ontime, late_reasons)}."""
    vendor_stats: dict[str, VendorPeriodAgg] = {}
    for vid, (total, ontime, reasons) in vendor_data.items():
        vendor_stats[vid] = VendorPeriodAgg(
            vendor_id=vid,
            period=period,
            total_count=total,
            ontime_count=ontime,
            late_delay_reason_counts=Counter(reasons),
        )
    total_count = sum(t for t, _, _ in vendor_data.values())
    return PeriodLoadResult(
        period=period,
        t_seconds=t_seconds,
        total_rows=total_count,
        spot20_excluded=0,
        null_epoch_excluded=0,
        eligible_rows=total_count,
        vendor_stats=vendor_stats,
    )


class TestComparePeriods:
    def test_deteriorating_vendor_flagged(self):
        prior = make_period("May", {"V1": (1000, 700, {"NODELAY": 300})})
        current = make_period("June", {"V1": (1000, 600, {"NODELAY": 400})})
        result = compare_periods(prior, current, 500, 5.0)
        vc = result.vendor_comparisons["V1"]
        assert vc.prior_ota_pct == pytest.approx(70.0)
        assert vc.current_ota_pct == pytest.approx(60.0)
        assert vc.ota_pp_change == pytest.approx(-10.0)
        assert vc.is_deterioration is True

    def test_exactly_at_threshold_not_deterioration(self):
        """pp_change = −5.0 at threshold 5.0 is NOT a breach (strictly less than)."""
        prior = make_period("May", {"V1": (1000, 700, {})})
        current = make_period("June", {"V1": (1000, 650, {})})
        result = compare_periods(prior, current, 500, 5.0)
        vc = result.vendor_comparisons["V1"]
        assert vc.ota_pp_change == pytest.approx(-5.0)
        assert vc.is_deterioration is False

    def test_improvement_not_deterioration(self):
        prior = make_period("May", {"V1": (1000, 600, {})})
        current = make_period("June", {"V1": (1000, 700, {})})
        result = compare_periods(prior, current, 500, 5.0)
        assert result.vendor_comparisons["V1"].is_deterioration is False

    def test_vendor_below_vol_min_excluded(self):
        prior = make_period("May", {"V1": (1000, 700, {}), "V2": (400, 300, {})})
        current = make_period("June", {"V1": (1000, 600, {}), "V2": (400, 300, {})})
        result = compare_periods(prior, current, 500, 5.0)
        assert "V1" in result.eligible_vendor_ids
        assert "V2" not in result.eligible_vendor_ids
        assert "V1" in result.vendor_comparisons
        assert "V2" not in result.vendor_comparisons

    def test_fleet_uses_eligible_cohort_only(self):
        """V2 excluded (400 trips); fleet must use V1 only."""
        prior = make_period("May", {"V1": (1000, 700, {}), "V2": (400, 300, {})})
        current = make_period("June", {"V1": (1000, 600, {}), "V2": (400, 300, {})})
        result = compare_periods(prior, current, 500, 5.0)
        assert result.fleet_prior_ota_pct == pytest.approx(70.0)
        assert result.fleet_current_ota_pct == pytest.approx(60.0)

    def test_fleet_is_trip_weighted(self):
        """fleet OTA is trip-weighted sum, not average of vendor percentages."""
        prior = make_period("May", {
            "V1": (100, 1, {}),   # 1%
            "V2": (10, 9, {}),    # 90%
        })
        current = make_period("June", {
            "V1": (100, 1, {}),
            "V2": (10, 9, {}),
        })
        result = compare_periods(prior, current, 10, 5.0)
        expected = (1 + 9) / (100 + 10) * 100
        assert result.fleet_prior_ota_pct == pytest.approx(expected)

    def test_breach_count_and_pct(self):
        prior = make_period("May", {
            "V1": (1000, 700, {}), "V2": (1000, 700, {}), "V3": (1000, 700, {}),
        })
        current = make_period("June", {
            "V1": (1000, 600, {}),  # −10 pp, breach
            "V2": (1000, 650, {}),  # −5.0 pp, NOT a breach
            "V3": (1000, 700, {}),  # 0 pp, no change
        })
        result = compare_periods(prior, current, 500, 5.0)
        assert result.breach_count == 1
        assert result.breach_pct == pytest.approx(100.0 / 3, abs=0.01)

    def test_no_eligible_vendors_all_zeros(self):
        prior = make_period("May", {"V1": (100, 70, {})})
        current = make_period("June", {"V1": (100, 60, {})})
        result = compare_periods(prior, current, 500, 5.0)
        assert len(result.eligible_vendor_ids) == 0
        assert result.fleet_prior_ota_pct == 0.0
        assert result.breach_count == 0
        assert result.breach_pct == 0.0

    def test_period_names_propagated(self):
        prior = make_period("May", {"V1": (1000, 700, {})})
        current = make_period("June", {"V1": (1000, 600, {})})
        result = compare_periods(prior, current, 500, 5.0)
        assert result.prior_period == "May"
        assert result.current_period == "June"
        vc = result.vendor_comparisons["V1"]
        assert vc.prior_period == "May"
        assert vc.current_period == "June"

    def test_deteriorated_vendor_ids_matches_breach_count(self):
        prior = make_period("May", {"V1": (1000, 700, {}), "V2": (1000, 700, {})})
        current = make_period("June", {"V1": (1000, 600, {}), "V2": (1000, 695, {})})
        result = compare_periods(prior, current, 500, 5.0)
        assert len(result.deteriorated_vendor_ids) == result.breach_count
        assert "V1" in result.deteriorated_vendor_ids
        assert "V2" not in result.deteriorated_vendor_ids

    def test_fleet_ota_pp_change_consistent(self):
        prior = make_period("May", {"V1": (1000, 700, {})})
        current = make_period("June", {"V1": (1000, 600, {})})
        result = compare_periods(prior, current, 500, 5.0)
        expected = result.fleet_current_ota_pct - result.fleet_prior_ota_pct
        assert result.fleet_ota_pp_change == pytest.approx(expected)


class TestComparePeriodsProvenance:
    def test_a_t_seconds_mismatch_raises_value_error(self):
        prior = make_period("May", {"V1": (1000, 700, {})}, t_seconds=300)
        current = make_period("June", {"V1": (1000, 600, {})}, t_seconds=600)
        with pytest.raises(ValueError, match="t_seconds"):
            compare_periods(prior, current, 500, 5.0)

    def test_b_comparison_records_provenance(self):
        prior = make_period("May", {"V1": (1000, 700, {})}, t_seconds=300)
        current = make_period("June", {"V1": (1000, 600, {})}, t_seconds=300)
        result = compare_periods(prior, current, 500, 5.0)
        assert result.t_seconds == 300
        assert result.vol_min == 500
        assert result.deterioration_threshold_pp == 5.0
