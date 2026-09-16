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
