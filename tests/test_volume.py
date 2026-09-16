"""Unit tests for compute.volume.apply_volume_filter."""
import pytest

from moveinsync_ota.compute.volume import apply_volume_filter
from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg


def make_period(period: str, vendor_counts: dict[str, int]) -> PeriodLoadResult:
    vendor_stats: dict[str, VendorPeriodAgg] = {}
    for vid, count in vendor_counts.items():
        agg = VendorPeriodAgg(vendor_id=vid, period=period, total_count=count)
        vendor_stats[vid] = agg
    return PeriodLoadResult(
        period=period,
        t_seconds=300,
        total_rows=sum(vendor_counts.values()),
        spot20_excluded=0,
        null_epoch_excluded=0,
        eligible_rows=sum(vendor_counts.values()),
        vendor_stats=vendor_stats,
    )


class TestApplyVolumeFilter:
    # ---- Plan scenario A: May=600, Jun=700, Jul=400 ----

    def test_scenario_a_may_june_eligible(self):
        """V1 qualifies for May→Jun because both ≥ 500."""
        may = make_period("May", {"V1": 600})
        jun = make_period("June", {"V1": 700})
        assert "V1" in apply_volume_filter(may, jun, 500)

    def test_scenario_a_jun_jul_not_eligible(self):
        """V1 excluded for Jun→Jul because Jul=400 < 500."""
        jun = make_period("June", {"V1": 700})
        jul = make_period("July", {"V1": 400})
        assert "V1" not in apply_volume_filter(jun, jul, 500)

    # ---- Plan scenario B: May=300, Jun=600, Jul=700 ----

    def test_scenario_b_may_june_not_eligible(self):
        """V1 excluded for May→Jun because May=300 < 500."""
        may = make_period("May", {"V1": 300})
        jun = make_period("June", {"V1": 600})
        assert "V1" not in apply_volume_filter(may, jun, 500)

    def test_scenario_b_jun_jul_eligible(self):
        """V1 qualifies for Jun→Jul because both ≥ 500."""
        jun = make_period("June", {"V1": 600})
        jul = make_period("July", {"V1": 700})
        assert "V1" in apply_volume_filter(jun, jul, 500)

    # ---- Boundary conditions ----

    def test_exactly_at_vol_min_is_eligible(self):
        prior = make_period("May", {"V1": 500})
        current = make_period("June", {"V1": 500})
        assert "V1" in apply_volume_filter(prior, current, 500)

    def test_one_below_vol_min_not_eligible(self):
        prior = make_period("May", {"V1": 499})
        current = make_period("June", {"V1": 500})
        assert "V1" not in apply_volume_filter(prior, current, 500)

    def test_vendor_in_prior_only_not_eligible(self):
        prior = make_period("May", {"V1": 600})
        current = make_period("June", {})
        assert "V1" not in apply_volume_filter(prior, current, 500)

    def test_vendor_in_current_only_not_eligible(self):
        prior = make_period("May", {})
        current = make_period("June", {"V1": 600})
        assert "V1" not in apply_volume_filter(prior, current, 500)

    # ---- Multi-vendor partial eligibility ----

    def test_multiple_vendors_partial_eligibility(self):
        prior = make_period("May", {"V1": 600, "V2": 400, "V3": 600})
        current = make_period("June", {"V1": 600, "V2": 600, "V3": 400})
        result = apply_volume_filter(prior, current, 500)
        assert "V1" in result
        assert "V2" not in result   # prior=400
        assert "V3" not in result   # current=400

    def test_returns_frozenset(self):
        prior = make_period("May", {"V1": 600})
        current = make_period("June", {"V1": 600})
        assert isinstance(apply_volume_filter(prior, current, 500), frozenset)

    def test_empty_vendors_returns_empty(self):
        prior = make_period("May", {})
        current = make_period("June", {})
        assert apply_volume_filter(prior, current, 500) == frozenset()

    def test_eligibility_uses_only_the_two_given_periods(self):
        """apply_volume_filter takes exactly two PeriodLoadResult arguments;
        calling it with May+June cannot incorporate July counts by construction."""
        may = make_period("May", {"V1": 600})
        jun = make_period("June", {"V1": 700})
        result = apply_volume_filter(may, jun, 500)
        assert "V1" in result
