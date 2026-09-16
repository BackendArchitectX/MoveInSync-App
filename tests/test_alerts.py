"""Unit tests for alerts.builder — build_alert_candidates and alert_id."""
import hashlib
import json
from collections import Counter

import pytest

from moveinsync_ota.alerts.builder import POLICY_VERSION, build_alert_candidates
from moveinsync_ota.compute.comparison import compare_periods
from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg


def make_period(
    period: str,
    vendor_data: dict[str, tuple[int, int, dict]],
    t_seconds: int = 300,
) -> PeriodLoadResult:
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


def two_vendor_comparison(
    v1_prior_ontime: int = 700,
    v1_current_ontime: int = 600,
    v2_prior_ontime: int = 700,
    v2_current_ontime: int = 695,
):
    prior = make_period("May", {
        "V1": (1000, v1_prior_ontime, {"NODELAY": 300}),
        "V2": (1000, v2_prior_ontime, {}),
    })
    current = make_period("June", {
        "V1": (1000, v1_current_ontime, {"NODELAY": 400}),
        "V2": (1000, v2_current_ontime, {}),
    })
    return compare_periods(prior, current, 500, 5.0)


class TestBuildAlertCandidates:
    def test_only_deteriorating_vendors_become_candidates(self):
        comparison = two_vendor_comparison()
        candidates = build_alert_candidates(comparison)
        vendor_ids = [c.vendor_id for c in candidates]
        assert "V1" in vendor_ids
        assert "V2" not in vendor_ids

    def test_sorted_worst_first(self):
        prior = make_period("May", {"V1": (1000, 700, {}), "V2": (1000, 700, {})})
        current = make_period("June", {
            "V1": (1000, 500, {}),  # −20 pp
            "V2": (1000, 600, {}),  # −10 pp
        })
        comparison = compare_periods(prior, current, 500, 5.0)
        candidates = build_alert_candidates(comparison)
        assert candidates[0].vendor_id == "V1"   # −20 pp first
        assert candidates[1].vendor_id == "V2"   # −10 pp second

    def test_tie_broken_by_vendor_id_lexicographic(self):
        prior = make_period("May", {"Zorro": (1000, 700, {}), "Alpha": (1000, 700, {})})
        current = make_period("June", {
            "Zorro": (1000, 600, {}),  # −10 pp
            "Alpha": (1000, 600, {}),  # −10 pp (same)
        })
        comparison = compare_periods(prior, current, 500, 5.0)
        candidates = build_alert_candidates(comparison)
        assert candidates[0].vendor_id == "Alpha"  # "Alpha" < "Zorro"

    def test_zero_candidates_when_no_deterioration(self):
        prior = make_period("May", {"V1": (1000, 600, {})})
        current = make_period("June", {"V1": (1000, 650, {})})
        comparison = compare_periods(prior, current, 500, 5.0)
        assert build_alert_candidates(comparison) == []

    def test_alert_id_is_64_hex_chars(self):
        comparison = two_vendor_comparison()
        c = build_alert_candidates(comparison)[0]
        assert len(c.alert_id) == 64
        assert all(ch in "0123456789abcdef" for ch in c.alert_id)

    def test_alert_id_deterministic(self):
        comparison = two_vendor_comparison()
        c1 = build_alert_candidates(comparison)[0]
        c2 = build_alert_candidates(comparison)[0]
        assert c1.alert_id == c2.alert_id

    def test_alert_id_changes_with_t_seconds(self):
        prior_300 = make_period("May", {"V1": (1000, 700, {})}, t_seconds=300)
        current_300 = make_period("June", {"V1": (1000, 600, {})}, t_seconds=300)
        prior_600 = make_period("May", {"V1": (1000, 700, {})}, t_seconds=600)
        current_600 = make_period("June", {"V1": (1000, 600, {})}, t_seconds=600)
        id_300 = build_alert_candidates(compare_periods(prior_300, current_300, 500, 5.0))[0].alert_id
        id_600 = build_alert_candidates(compare_periods(prior_600, current_600, 500, 5.0))[0].alert_id
        assert id_300 != id_600

    def test_alert_id_changes_with_vol_min(self):
        prior = make_period("May", {"V1": (2000, 1400, {})})
        current = make_period("June", {"V1": (2000, 1200, {})})
        id_500 = build_alert_candidates(compare_periods(prior, current, 500, 5.0))[0].alert_id
        id_1000 = build_alert_candidates(compare_periods(prior, current, 1000, 5.0))[0].alert_id
        assert id_500 != id_1000

    def test_alert_id_sha256_matches_manual_computation(self):
        comparison = two_vendor_comparison()
        candidate = build_alert_candidates(comparison)[0]
        identity = {
            "DETERIORATION_THRESHOLD_PP": 5.0,
            "T_SECONDS": 300,
            "VOL_MIN": 500,
            "current_period": "June",
            "policy_version": POLICY_VERSION,
            "prior_period": "May",
            "vendor_id": "V1",
        }
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(canonical.encode()).hexdigest()
        assert candidate.alert_id == expected

    def test_candidate_policy_version(self):
        comparison = two_vendor_comparison()
        c = build_alert_candidates(comparison)[0]
        assert c.policy_version == POLICY_VERSION

    def test_candidate_vendor_evidence(self):
        comparison = two_vendor_comparison()
        c = build_alert_candidates(comparison)[0]
        assert c.prior_total_count == 1000
        assert c.current_total_count == 1000
        assert c.prior_ota_pct == pytest.approx(70.0)
        assert c.current_ota_pct == pytest.approx(60.0)
        assert c.ota_pp_change == pytest.approx(-10.0)

    def test_candidate_config_snapshot(self):
        comparison = two_vendor_comparison()
        c = build_alert_candidates(comparison)[0]
        assert c.T_seconds == 300
        assert c.vol_min == 500
        assert c.deterioration_threshold_pp == 5.0

    def test_candidate_fleet_evidence(self):
        comparison = two_vendor_comparison()
        c = build_alert_candidates(comparison)[0]
        assert c.eligible_vendor_count == len(comparison.eligible_vendor_ids)
        assert c.breach_count == comparison.breach_count
        assert c.fleet_prior_ota_pct == pytest.approx(comparison.fleet_prior_ota_pct)


class TestProvenanceIntegrity:
    def test_c_candidate_copies_provenance_from_comparison(self):
        comparison = two_vendor_comparison()
        c = build_alert_candidates(comparison)[0]
        assert c.T_seconds == comparison.t_seconds
        assert c.vol_min == comparison.vol_min
        assert c.deterioration_threshold_pp == comparison.deterioration_threshold_pp

    def test_d_threshold_change_produces_different_alert_id(self):
        prior = make_period("May", {"V1": (1000, 700, {})})
        current = make_period("June", {"V1": (1000, 600, {})})
        id_5 = build_alert_candidates(compare_periods(prior, current, 500, 5.0))[0].alert_id
        id_7 = build_alert_candidates(compare_periods(prior, current, 500, 7.0))[0].alert_id
        assert id_5 != id_7

    def test_e_vol_min_change_produces_different_alert_id(self):
        prior = make_period("May", {"V1": (2000, 1400, {})})
        current = make_period("June", {"V1": (2000, 1200, {})})
        id_500 = build_alert_candidates(compare_periods(prior, current, 500, 5.0))[0].alert_id
        id_1000 = build_alert_candidates(compare_periods(prior, current, 1000, 5.0))[0].alert_id
        assert id_500 != id_1000

    def test_f_t_seconds_change_produces_different_alert_id(self):
        prior_300 = make_period("May", {"V1": (1000, 700, {})}, t_seconds=300)
        current_300 = make_period("June", {"V1": (1000, 600, {})}, t_seconds=300)
        prior_600 = make_period("May", {"V1": (1000, 700, {})}, t_seconds=600)
        current_600 = make_period("June", {"V1": (1000, 600, {})}, t_seconds=600)
        id_300 = build_alert_candidates(compare_periods(prior_300, current_300, 500, 5.0))[0].alert_id
        id_600 = build_alert_candidates(compare_periods(prior_600, current_600, 500, 5.0))[0].alert_id
        assert id_300 != id_600
