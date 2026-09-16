"""Integration tests — require real CSV files at DATA_DIR.

Run with:  pytest -v -m integration
Skip with: pytest -v -m "not integration"

Observed pin counts (T=300s, verified against immutable CSVs):
  May:  total=188992  spot20=648  null_epoch=0  eligible=188344
  June: total=210669  spot20=702  null_epoch=0  eligible=209967
  July: total=215885  spot20=973  null_epoch=0  eligible=214912

Vendor name in data is "Meera Pavlov Travel" (includes "Travel" suffix).
Meera Pavlov Travel / May spot-check (T=300s):
  total_count=5392  ontime_count=4119
"""
import time
import pytest

from moveinsync_ota.config import DATA_DIR, MONTH_FILES, T_SECONDS
from moveinsync_ota.data.loader import load_all_files


@pytest.fixture(scope="module")
def results():
    if not DATA_DIR.exists():
        pytest.skip(f"DATA_DIR not found: {DATA_DIR}")
    t0 = time.perf_counter()
    res = load_all_files(DATA_DIR, MONTH_FILES, T_SECONDS)
    elapsed = time.perf_counter() - t0
    print(f"\nload_all_files elapsed: {elapsed:.2f}s")
    return res


@pytest.mark.integration
class TestProfile1PinCounts:
    def test_may_total_rows(self, results):
        may = next(r for r in results if r.period == "May")
        assert may.total_rows == 188992

    def test_may_spot20_excluded(self, results):
        may = next(r for r in results if r.period == "May")
        assert may.spot20_excluded == 648

    def test_may_null_epoch_excluded(self, results):
        may = next(r for r in results if r.period == "May")
        assert may.null_epoch_excluded == 0

    def test_may_eligible_rows(self, results):
        may = next(r for r in results if r.period == "May")
        assert may.eligible_rows == 188344

    def test_june_total_rows(self, results):
        june = next(r for r in results if r.period == "June")
        assert june.total_rows == 210669

    def test_june_spot20_excluded(self, results):
        june = next(r for r in results if r.period == "June")
        assert june.spot20_excluded == 702

    def test_june_null_epoch_excluded(self, results):
        june = next(r for r in results if r.period == "June")
        assert june.null_epoch_excluded == 0

    def test_june_eligible_rows(self, results):
        june = next(r for r in results if r.period == "June")
        assert june.eligible_rows == 209967

    def test_july_total_rows(self, results):
        july = next(r for r in results if r.period == "July")
        assert july.total_rows == 215885

    def test_july_spot20_excluded(self, results):
        july = next(r for r in results if r.period == "July")
        assert july.spot20_excluded == 973

    def test_july_null_epoch_excluded(self, results):
        july = next(r for r in results if r.period == "July")
        assert july.null_epoch_excluded == 0

    def test_july_eligible_rows(self, results):
        july = next(r for r in results if r.period == "July")
        assert july.eligible_rows == 214912

    def test_total_eligible_rows_all_months(self, results):
        assert sum(r.eligible_rows for r in results) == 613_223


@pytest.mark.integration
class TestMeeraPavlovSpotCheck:
    def test_may_total_count(self, results):
        may = next(r for r in results if r.period == "May")
        agg = may.vendor_stats.get("Meera Pavlov Travel")
        assert agg is not None, "Vendor 'Meera Pavlov Travel' not found in May data"
        assert agg.total_count == 5392

    def test_may_ontime_count(self, results):
        may = next(r for r in results if r.period == "May")
        agg = may.vendor_stats["Meera Pavlov Travel"]
        assert agg.ontime_count == 4119


# ---------------------------------------------------------------------------
# M2 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def may_june_comparison(results):
    from moveinsync_ota.compute.comparison import compare_periods
    from moveinsync_ota.config import VOL_MIN, DETERIORATION_THRESHOLD_PP
    may = next(r for r in results if r.period == "May")
    june = next(r for r in results if r.period == "June")
    return compare_periods(may, june, VOL_MIN, DETERIORATION_THRESHOLD_PP)


@pytest.fixture(scope="module")
def june_july_comparison(results):
    from moveinsync_ota.compute.comparison import compare_periods
    from moveinsync_ota.config import VOL_MIN, DETERIORATION_THRESHOLD_PP
    june = next(r for r in results if r.period == "June")
    july = next(r for r in results if r.period == "July")
    return compare_periods(june, july, VOL_MIN, DETERIORATION_THRESHOLD_PP)


# ---------------------------------------------------------------------------
# M3 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def may_june_candidates(may_june_comparison):
    from moveinsync_ota.alerts.builder import build_alert_candidates
    return build_alert_candidates(may_june_comparison)


@pytest.fixture(scope="module")
def june_july_candidates(june_july_comparison):
    from moveinsync_ota.alerts.builder import build_alert_candidates
    return build_alert_candidates(june_july_comparison)


# ---------------------------------------------------------------------------
# M2 calibration gate
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestM2Calibration:
    def test_may_june_eligible_vendor_count(self, may_june_comparison):
        assert len(may_june_comparison.eligible_vendor_ids) == 21

    def test_may_june_fleet_prior_ota(self, may_june_comparison):
        assert may_june_comparison.fleet_prior_ota_pct == pytest.approx(46.98, abs=0.01)

    def test_may_june_fleet_current_ota(self, may_june_comparison):
        assert may_june_comparison.fleet_current_ota_pct == pytest.approx(41.14, abs=0.01)

    def test_may_june_fleet_change(self, may_june_comparison):
        assert may_june_comparison.fleet_ota_pp_change == pytest.approx(-5.84, abs=0.01)

    def test_may_june_breach_count(self, may_june_comparison):
        assert may_june_comparison.breach_count == 18

    def test_may_june_breach_pct(self, may_june_comparison):
        assert may_june_comparison.breach_pct == pytest.approx(85.71, abs=0.01)

    def test_meera_pavlov_prior_count(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.prior_total_count == 5392

    def test_meera_pavlov_current_count(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.current_total_count == 5294

    def test_meera_pavlov_prior_ota(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.prior_ota_pct == pytest.approx(76.39, abs=0.01)

    def test_meera_pavlov_current_ota(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.current_ota_pct == pytest.approx(68.53, abs=0.01)

    def test_meera_pavlov_pp_change(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.ota_pp_change == pytest.approx(-7.86, abs=0.01)

    def test_meera_pavlov_is_deterioration(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.is_deterioration is True

    def test_meera_pavlov_top_non_nodelay_traffic(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.delay_context.top_non_nodelay_reason == "TRAFFIC"

    def test_meera_pavlov_nodelay_dominates(self, may_june_comparison):
        vc = may_june_comparison.vendor_comparisons["Meera Pavlov Travel"]
        assert vc.delay_context.nodelay_dominates is True

    def test_june_july_eligible_vendor_count(self, june_july_comparison):
        assert len(june_july_comparison.eligible_vendor_ids) == 21

    def test_june_july_breach_count(self, june_july_comparison):
        assert june_july_comparison.breach_count == 0


# ---------------------------------------------------------------------------
# M3 calibration gate
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestM3Calibration:
    def test_may_june_candidate_count(self, may_june_candidates):
        assert len(may_june_candidates) == 18

    def test_june_july_candidate_count(self, june_july_candidates):
        assert len(june_july_candidates) == 0

    def test_meera_pavlov_candidate_present(self, may_june_candidates):
        meera = next(
            (c for c in may_june_candidates if c.vendor_id == "Meera Pavlov Travel"),
            None,
        )
        assert meera is not None

    def test_meera_pavlov_alert_id_sha256(self, may_june_candidates):
        meera = next(c for c in may_june_candidates if c.vendor_id == "Meera Pavlov Travel")
        assert len(meera.alert_id) == 64
        assert all(ch in "0123456789abcdef" for ch in meera.alert_id)

    def test_meera_pavlov_vendor_evidence(self, may_june_candidates):
        meera = next(c for c in may_june_candidates if c.vendor_id == "Meera Pavlov Travel")
        assert meera.prior_total_count == 5392
        assert meera.current_total_count == 5294
        assert meera.prior_ota_pct == pytest.approx(76.39, abs=0.01)
        assert meera.current_ota_pct == pytest.approx(68.53, abs=0.01)
        assert meera.ota_pp_change == pytest.approx(-7.86, abs=0.01)

    def test_meera_pavlov_fleet_evidence(self, may_june_candidates):
        meera = next(c for c in may_june_candidates if c.vendor_id == "Meera Pavlov Travel")
        assert meera.fleet_prior_ota_pct == pytest.approx(46.98, abs=0.01)
        assert meera.fleet_current_ota_pct == pytest.approx(41.14, abs=0.01)
        assert meera.eligible_vendor_count == 21
        assert meera.breach_count == 18

    def test_meera_pavlov_delay_evidence(self, may_june_candidates):
        meera = next(c for c in may_june_candidates if c.vendor_id == "Meera Pavlov Travel")
        assert meera.top_non_nodelay_reason == "TRAFFIC"
        assert meera.nodelay_dominates is True

    def test_candidates_sorted_worst_first(self, may_june_candidates):
        changes = [c.ota_pp_change for c in may_june_candidates]
        assert changes == sorted(changes)
