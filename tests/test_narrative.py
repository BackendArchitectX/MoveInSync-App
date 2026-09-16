"""Tests for app.narrative — deterministic provider and cache behaviour."""
from unittest.mock import MagicMock

import pytest

from moveinsync_ota.alerts.models import AlertCandidate
from moveinsync_ota.app.narrative import (
    BedrockNarrativeProvider,
    DeterministicNarrativeProvider,
    NarrativeProvider,
)


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_candidate(**overrides) -> AlertCandidate:
    defaults = dict(
        alert_id="abc123",
        policy_version="ota-watchdog-v1",
        vendor_id="Test Vendor",
        prior_period="May",
        current_period="June",
        prior_ota_pct=70.0,
        current_ota_pct=60.0,
        ota_pp_change=-10.0,
        prior_total_count=1000,
        current_total_count=1000,
        total_late_count=400,
        nodelay_count=300,
        nodelay_share=0.75,
        nodelay_dominates=True,
        top_non_nodelay_reason="TRAFFIC",
        top_non_nodelay_count=70,
        top_non_nodelay_share=0.175,
        full_distribution={"NODELAY": 300, "TRAFFIC": 70, "DRIVER": 30},
        fleet_prior_ota_pct=65.0,
        fleet_current_ota_pct=58.0,
        fleet_ota_pp_change=-7.0,
        eligible_vendor_count=10,
        breach_count=8,
        breach_pct=80.0,
        T_seconds=300,
        vol_min=500,
        deterioration_threshold_pp=5.0,
    )
    defaults.update(overrides)
    return AlertCandidate(**defaults)


class _FakeProvider(NarrativeProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def generate(self, candidate: AlertCandidate) -> str:
        self.call_count += 1
        return f"narrative:{candidate.alert_id}:{self.call_count}"


# ── B. Deterministic narrative ────────────────────────────────────────────

class TestDeterministicNarrative:
    def test_generates_non_empty_string(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate())
        assert isinstance(text, str) and len(text) > 50

    def test_includes_vendor_name(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate())
        assert "Test Vendor" in text

    def test_includes_key_metrics(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate(ota_pp_change=-10.0))
        assert "10.0" in text

    def test_does_not_claim_causality(self):
        text = DeterministicNarrativeProvider().generate(
            _make_candidate(top_non_nodelay_reason="TRAFFIC")
        )
        lower = text.lower()
        assert "traffic caused" not in lower
        assert "caused by" not in lower
        assert "caused the" not in lower

    def test_labels_delay_context_as_recorded(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate())
        assert "ecorded delay context" in text

    def test_does_not_mutate_candidate(self):
        c = _make_candidate()
        original_ota = c.ota_pp_change
        DeterministicNarrativeProvider().generate(c)
        assert c.ota_pp_change == original_ota

    def test_handles_no_top_non_nodelay_reason(self):
        text = DeterministicNarrativeProvider().generate(
            _make_candidate(top_non_nodelay_reason=None, top_non_nodelay_count=0)
        )
        assert isinstance(text, str) and len(text) > 0

    def test_suggested_action_present(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate())
        assert "Suggested action" in text


# ── C. Narrative cache ────────────────────────────────────────────────────

class TestNarrativeCache:
    def test_c_provider_called_once_per_alert(self):
        fake = _FakeProvider()
        cache: dict[str, str] = {}
        c = _make_candidate(alert_id="x1")
        for _ in range(3):
            if c.alert_id not in cache:
                cache[c.alert_id] = fake.generate(c)
        assert fake.call_count == 1

    def test_c_different_alerts_each_invoke_provider_once(self):
        fake = _FakeProvider()
        cache: dict[str, str] = {}
        c1 = _make_candidate(alert_id="x1")
        c2 = _make_candidate(alert_id="x2", vendor_id="Other")
        for c in [c1, c2, c1, c2, c1]:
            if c.alert_id not in cache:
                cache[c.alert_id] = fake.generate(c)
        assert fake.call_count == 2

    def test_c_cached_value_stable_across_accesses(self):
        fake = _FakeProvider()
        cache: dict[str, str] = {}
        c = _make_candidate(alert_id="x1")
        for _ in range(3):
            if c.alert_id not in cache:
                cache[c.alert_id] = fake.generate(c)
        assert len(set([cache[c.alert_id] for _ in range(3)])) == 1
        assert fake.call_count == 1


# ── C2. Bedrock fallback ──────────────────────────────────────────────────

class TestBedrockFallback:
    def test_generate_returns_deterministic_fallback_on_client_error(self):
        det = DeterministicNarrativeProvider()
        provider = BedrockNarrativeProvider(model_id="fake-model", region="us-east-1", fallback=det)
        mock_client = MagicMock()
        mock_client.converse.side_effect = RuntimeError("connection refused")
        provider._client = mock_client

        c = _make_candidate()
        result = provider.generate(c)

        assert result == det.generate(c)
        assert "Test Vendor" in result
        mock_client.converse.assert_called_once()

    def test_generate_does_not_raise_on_client_error(self):
        provider = BedrockNarrativeProvider(model_id="fake-model", region="us-east-1")
        mock_client = MagicMock()
        mock_client.converse.side_effect = Exception("any error")
        provider._client = mock_client

        try:
            result = provider.generate(_make_candidate())
            assert isinstance(result, str) and len(result) > 0
        except Exception:
            pytest.fail("generate() must not raise when Bedrock fails")


# ── D. Bedrock prompt constraints ─────────────────────────────────────────

class TestBedrockPromptConstraints:
    def _get_prompt(self) -> str:
        provider = BedrockNarrativeProvider(model_id="fake-model")
        return provider._build_prompt(_make_candidate())

    def test_prompt_forbids_causality(self):
        prompt = self._get_prompt()
        assert "Do not claim causality" in prompt

    def test_prompt_labels_delay_context_as_non_causal(self):
        prompt = self._get_prompt()
        assert "delay reasons are context only" in prompt

    def test_prompt_forbids_recalculation(self):
        prompt = self._get_prompt()
        assert "Do not calculate or re-derive" in prompt

    def test_prompt_forbids_new_numbers(self):
        prompt = self._get_prompt()
        assert "Do not introduce new calculations or numbers" in prompt

    def test_prompt_restricts_fleet_comparison_wording(self):
        prompt = self._get_prompt()
        assert "above/below the fleet-level OTA" in prompt

    def test_prompt_forbids_ranking_language(self):
        prompt = self._get_prompt()
        assert "outperform" in prompt
        assert "underperform" in prompt
        assert "benchmark" in prompt

    def test_prompt_forbids_root_cause_inference(self):
        prompt = self._get_prompt()
        assert "Do not infer root cause" in prompt
