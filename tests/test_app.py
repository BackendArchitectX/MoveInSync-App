"""API smoke tests for app.main — uses FastAPI TestClient."""
import os

import pytest
from fastapi.testclient import TestClient

from moveinsync_ota.app.narrative import NarrativeProvider
from moveinsync_ota.app.service import OTAService
from moveinsync_ota.data.schema import PeriodLoadResult, VendorPeriodAgg


# ── Synthetic fixture helpers ─────────────────────────────────────────────

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
    may = _make_period("May",  {"V1": (1000, 700), "V2": (1000, 700)})
    june = _make_period("June", {"V1": (1000, 600), "V2": (1000, 695)})
    july = _make_period("July", {"V1": (1000, 650), "V2": (1000, 700)})
    svc = OTAService()
    svc.load(_periods=[may, june, july])
    svc.replay("may-june")
    svc.replay("june-july")
    return svc


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("OTA_TEST_MODE", "1")
    from moveinsync_ota.app.main import app, _inject_test_state
    _inject_test_state(_fake_svc())
    with TestClient(app) as c:
        yield c


# ── D. Unit smoke tests ───────────────────────────────────────────────────

class TestRootRoute:
    def test_get_root_returns_200(self, client):
        assert client.get("/").status_code == 200

    def test_root_is_html(self, client):
        assert "text/html" in client.get("/").headers["content-type"]

    def test_root_contains_branding(self, client):
        assert "OTA Watchdog" in client.get("/").text


class TestStateEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/state").status_code == 200

    def test_contains_both_comparison_keys(self, client):
        data = client.get("/api/state").json()
        assert "may-june" in data and "june-july" in data

    def test_may_june_has_run(self, client):
        data = client.get("/api/state").json()
        assert data["may-june"]["run"] is not None

    def test_may_june_has_candidates(self, client):
        data = client.get("/api/state").json()
        assert len(data["may-june"]["candidates"]) >= 1

    def test_june_july_has_zero_candidates(self, client):
        data = client.get("/api/state").json()
        assert data["june-july"]["candidates"] == []


class TestAlertEndpoint:
    def test_unknown_alert_returns_404(self, client):
        assert client.get("/api/alerts/nonexistent").status_code == 404

    def test_known_alert_returns_200(self, client):
        aid = client.get("/api/state").json()["may-june"]["candidates"][0]["alert_id"]
        assert client.get(f"/api/alerts/{aid}").status_code == 200

    def test_alert_response_has_narrative(self, client):
        aid = client.get("/api/state").json()["may-june"]["candidates"][0]["alert_id"]
        data = client.get(f"/api/alerts/{aid}").json()
        assert "narrative" in data and data["narrative"]

    def test_alert_response_has_policy_fields(self, client):
        aid = client.get("/api/state").json()["may-june"]["candidates"][0]["alert_id"]
        data = client.get(f"/api/alerts/{aid}").json()
        assert all(k in data for k in ("T_seconds", "vol_min", "deterioration_threshold_pp"))


class TestReplayEndpoint:
    def test_unsupported_comparison_returns_422(self, client):
        assert client.post("/api/replay/jan-feb").status_code == 422

    def test_may_june_replay_returns_200(self, client):
        assert client.post("/api/replay/may-june").status_code == 200

    def test_june_july_replay_returns_200(self, client):
        assert client.post("/api/replay/june-july").status_code == 200

    def test_may_june_replay_has_candidates(self, client):
        assert len(client.post("/api/replay/may-june").json()["candidates"]) >= 1

    def test_june_july_replay_zero_candidates(self, client):
        assert client.post("/api/replay/june-july").json()["candidates"] == []

    def test_replay_response_has_run_and_comparison(self, client):
        data = client.post("/api/replay/may-june").json()
        assert "run" in data and "comparison" in data


# ── B. Real application narrative cache ──────────────────────────────────

class _CountingProvider(NarrativeProvider):
    def __init__(self):
        self.call_count = 0

    def generate(self, candidate):
        self.call_count += 1
        return f"narrative:{candidate.alert_id}:{self.call_count}"


class TestNarrativeCacheViaAPI:
    def test_same_alert_fetched_twice_calls_provider_once(self, monkeypatch):
        monkeypatch.setenv("OTA_TEST_MODE", "1")
        from moveinsync_ota.app.main import app, _inject_test_state

        provider = _CountingProvider()
        _inject_test_state(_fake_svc(), narrative=provider)
        with TestClient(app) as c:
            state = c.get("/api/state").json()
            aid = state["may-june"]["candidates"][0]["alert_id"]
            r1 = c.get(f"/api/alerts/{aid}").json()
            r2 = c.get(f"/api/alerts/{aid}").json()

        assert provider.call_count == 1
        assert r1["narrative"] == r2["narrative"]

    def test_two_different_alerts_each_call_provider_once(self, monkeypatch):
        monkeypatch.setenv("OTA_TEST_MODE", "1")
        from moveinsync_ota.app.main import app, _inject_test_state

        provider = _CountingProvider()
        _inject_test_state(_fake_svc(), narrative=provider)
        with TestClient(app) as c:
            candidates = c.get("/api/state").json()["may-june"]["candidates"]
            aid1 = candidates[0]["alert_id"]
            aid2 = candidates[1]["alert_id"] if len(candidates) > 1 else aid1
            c.get(f"/api/alerts/{aid1}")
            c.get(f"/api/alerts/{aid2}")
            c.get(f"/api/alerts/{aid1}")

        expected = 1 if aid1 == aid2 else 2
        assert provider.call_count == expected


# ── Integration smoke tests (real data) ──────────────────────────────────

@pytest.fixture(scope="module")
def int_client():
    from moveinsync_ota.config import DATA_DIR
    if not DATA_DIR.exists():
        pytest.skip(f"DATA_DIR not found: {DATA_DIR}")

    os.environ["OTA_TEST_MODE"] = "1"
    svc = OTAService()
    svc.load()
    svc.replay("may-june")
    svc.replay("june-july")

    from moveinsync_ota.app.main import app, _inject_test_state
    _inject_test_state(svc)
    with TestClient(app) as c:
        yield c

    os.environ.pop("OTA_TEST_MODE", None)


@pytest.mark.integration
class TestAppIntegration:
    def test_state_may_june_18_candidates(self, int_client):
        data = int_client.get("/api/state").json()
        assert len(data["may-june"]["candidates"]) == 18

    def test_state_may_june_eligible_21(self, int_client):
        data = int_client.get("/api/state").json()
        assert data["may-june"]["run"]["eligible_vendor_count"] == 21

    def test_state_may_june_breach_18(self, int_client):
        data = int_client.get("/api/state").json()
        assert data["may-june"]["run"]["breach_count"] == 18

    def test_state_june_july_zero_candidates(self, int_client):
        data = int_client.get("/api/state").json()
        assert data["june-july"]["candidates"] == []

    def test_replay_may_june_18_candidates(self, int_client):
        data = int_client.post("/api/replay/may-june").json()
        assert len(data["candidates"]) == 18

    def test_replay_june_july_zero_candidates(self, int_client):
        data = int_client.post("/api/replay/june-july").json()
        assert data["candidates"] == []
