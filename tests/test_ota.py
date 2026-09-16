"""Unit tests for compute.ota — vendor_ota_pct and fleet_ota_pct."""
import pytest

from moveinsync_ota.compute.ota import fleet_ota_pct, vendor_ota_pct
from moveinsync_ota.data.schema import VendorPeriodAgg


def make_agg(vendor_id: str, period: str, total: int, ontime: int) -> VendorPeriodAgg:
    return VendorPeriodAgg(
        vendor_id=vendor_id, period=period, total_count=total, ontime_count=ontime
    )


class TestVendorOtaPct:
    def test_all_ontime(self):
        assert vendor_ota_pct(make_agg("V1", "May", 100, 100)) == 100.0

    def test_none_ontime(self):
        assert vendor_ota_pct(make_agg("V1", "May", 100, 0)) == 0.0

    def test_half_ontime(self):
        assert vendor_ota_pct(make_agg("V1", "May", 4, 2)) == 50.0

    def test_zero_total_returns_zero(self):
        assert vendor_ota_pct(make_agg("V1", "May", 0, 0)) == 0.0

    def test_known_meera_pavlov_may(self):
        # Calibration: May total=5392, ontime=4119 → 76.39 %
        assert vendor_ota_pct(make_agg("Meera Pavlov Travel", "May", 5392, 4119)) == pytest.approx(76.39, abs=0.01)

    def test_known_meera_pavlov_june(self):
        # Calibration: June total=5294, ontime=3628 → 68.53 %
        assert vendor_ota_pct(make_agg("Meera Pavlov Travel", "June", 5294, 3628)) == pytest.approx(68.53, abs=0.01)

    def test_full_precision_no_premature_rounding(self):
        # 1/3 should be stored as float, not rounded
        result = vendor_ota_pct(make_agg("V1", "May", 3, 1))
        assert result == pytest.approx(33.333333, abs=0.001)


class TestFleetOtaPct:
    def test_two_equal_vendors(self):
        stats = {
            "V1": make_agg("V1", "May", 10, 4),
            "V2": make_agg("V2", "May", 10, 6),
        }
        assert fleet_ota_pct(stats, frozenset(["V1", "V2"])) == 50.0

    def test_eligible_subset_only(self):
        stats = {
            "V1": make_agg("V1", "May", 10, 4),
            "V2": make_agg("V2", "May", 10, 10),
        }
        # V2 excluded from eligible cohort
        assert fleet_ota_pct(stats, frozenset(["V1"])) == 40.0

    def test_empty_eligible_returns_zero(self):
        stats = {"V1": make_agg("V1", "May", 10, 4)}
        assert fleet_ota_pct(stats, frozenset()) == 0.0

    def test_trip_weighted_not_average_of_pcts(self):
        # V1: 1/100 = 1%, V2: 9/10 = 90%
        # Average-of-pcts = 45.5%; trip-weighted = 10/110 × 100 ≈ 9.09%
        stats = {
            "V1": make_agg("V1", "May", 100, 1),
            "V2": make_agg("V2", "May", 10, 9),
        }
        expected = (1 + 9) / (100 + 10) * 100
        assert fleet_ota_pct(stats, frozenset(["V1", "V2"])) == pytest.approx(expected)

    def test_single_vendor(self):
        stats = {"V1": make_agg("V1", "May", 200, 150)}
        assert fleet_ota_pct(stats, frozenset(["V1"])) == 75.0
