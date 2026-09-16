"""Unit and integration tests for app.service.OTAService."""
import pytest

from moveinsync_ota.app.service import OTAService, SUPPORTED_COMPARISONS
from moveinsync_ota.config import DETERIORATION_THRESHOLD_PP, VOL_MIN
from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg


# ── Synthetic data helpers ────────────────────────────────────────────────

def _make_period(period: str, vendors: dict[str, tuple[int, int]], t_seconds: int = 300) -> PeriodLoadResult:
    stats = {
        vid: VendorPeriodAgg(vendor_id=vid, period=period, total_count=t, ontime_count=o)
        for vid, (t, o) in vendors.items()
    }
    total = sum(t for t, _ in vendors.values())
    return PeriodLoadResult(
        period=period, t_seconds=t_seconds,
        total_rows=total, spot20_excluded=0, null_epoch_excluded=0,
        eligible_rows=total, vendor_stats=stats,
    )


def _fake_svc() -> OTAService:
    # V1: May 70%, June 60% = -10pp breach; June->July 65% = recovery
    may = _make_period("May",  {"V1": (1000, 700), "V2": (1000, 700)})
    june = _make_period("June", {"V1": (1000, 600), "V2": (1000, 695)})
    july = _make_period("July", {"V1": (1000, 650), "V2": (1000, 700)})
    svc = OTAService()
    svc.load(_periods=[may, june, july])
    return svc


# ── Unit tests ────────────────────────────────────────────────────────────

class TestOTAServiceUnit:
    def test_supported_comparisons_defined(self):
        assert "may-june" in SUPPORTED_COMPARISONS
        assert "june-july" in SUPPORTED_COMPARISONS

    def test_unsupported_period_raises_value_error(self):
        svc = _fake_svc()
        with pytest.raises(ValueError, match="Unsupported"):
            svc.replay("jan-feb")

    def test_may_june_produces_candidates(self):
        svc = _fake_svc()
        run = svc.replay("may-june")
        assert run.candidate_count >= 1
        assert run.status == "complete"

    def test_june_july_produces_zero_candidates(self):
        svc = _fake_svc()
        run = svc.replay("june-july")
        assert run.candidate_count == 0
        assert run.breach_count == 0

    def test_replay_dedup_does_not_grow_feed(self):
        svc = _fake_svc()
        svc.replay("may-june")
        feed_after_first = len(svc._feed)
        svc.replay("may-june")
        feed_after_second = len(svc._feed)
        assert feed_after_first == feed_after_second

    def test_replay_candidates_count_stable(self):
        svc = _fake_svc()
        svc.replay("may-june")
        count1 = len(svc.get_candidates("may-june"))
        svc.replay("may-june")
        count2 = len(svc.get_candidates("may-june"))
        assert count1 == count2

    def test_policy_provenance_in_candidate(self):
        svc = _fake_svc()
        svc.replay("may-june")
        for c in svc.get_candidates("may-june"):
            assert c.T_seconds == 300
            assert c.vol_min == VOL_MIN
            assert c.deterioration_threshold_pp == DETERIORATION_THRESHOLD_PP

    def test_get_alert_returns_none_for_unknown(self):
        svc = _fake_svc()
        assert svc.get_alert("nonexistent") is None

    def test_get_alert_returns_candidate_after_replay(self):
        svc = _fake_svc()
        svc.replay("may-june")
        candidates = svc.get_candidates("may-june")
        assert candidates
        first = candidates[0]
        assert svc.get_alert(first.alert_id) is first

    def test_get_latest_run_none_before_replay(self):
        svc = _fake_svc()
        assert svc.get_latest_run("may-june") is None

    def test_get_latest_run_populated_after_replay(self):
        svc = _fake_svc()
        svc.replay("may-june")
        run = svc.get_latest_run("may-june")
        assert run is not None
        assert run.prior_period == "May"
        assert run.current_period == "June"

    def test_agent_run_fields_populated(self):
        svc = _fake_svc()
        run = svc.replay("may-june")
        assert run.run_id and len(run.run_id) == 16
        assert run.started_at is not None
        assert run.completed_at is not None


# ── A. Missing-period replay ──────────────────────────────────────────────

class TestMissingPeriodReplay:
    def test_replay_raises_valueerror_if_period_not_loaded(self):
        svc = OTAService()
        may = _make_period("May", {"V1": (1000, 700)})
        svc.load(_periods=[may])
        with pytest.raises(ValueError, match="not loaded"):
            svc.replay("may-june")

    def test_replay_raises_lists_missing_period_name(self):
        svc = OTAService()
        may = _make_period("May", {"V1": (1000, 700)})
        svc.load(_periods=[may])
        with pytest.raises(ValueError, match="June"):
            svc.replay("may-june")

    def test_replay_succeeds_when_both_periods_loaded(self):
        svc = _fake_svc()
        run = svc.replay("may-june")
        assert run.status == "complete"


# ── Integration tests (real CSV data) ────────────────────────────────────

@pytest.mark.integration
class TestOTAServiceIntegration:
    @pytest.fixture(scope="class")
    def real_svc(self):
        from moveinsync_ota.config import DATA_DIR
        if not DATA_DIR.exists():
            pytest.skip(f"DATA_DIR not found: {DATA_DIR}")
        svc = OTAService()
        svc.load()
        return svc

    def test_may_june_produces_18_candidates(self, real_svc):
        run = real_svc.replay("may-june")
        assert run.candidate_count == 18

    def test_june_july_produces_0_candidates(self, real_svc):
        run = real_svc.replay("june-july")
        assert run.candidate_count == 0

    def test_may_june_eligible_count(self, real_svc):
        run = real_svc.get_latest_run("may-june")
        assert run.eligible_vendor_count == 21

    def test_policy_provenance_intact_real_data(self, real_svc):
        for c in real_svc.get_candidates("may-june"):
            assert c.T_seconds == 300
            assert c.vol_min == VOL_MIN
            assert c.deterioration_threshold_pp == DETERIORATION_THRESHOLD_PP
