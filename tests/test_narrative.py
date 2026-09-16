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

    def test_prompt_declares_nodelay_opaque(self):
        prompt = self._get_prompt()
        assert "NODELAY is a literal source-data category" in prompt

    def test_prompt_forbids_magnitude_comparison(self):
        prompt = self._get_prompt()
        assert "Never compare the magnitude" in prompt


# ── D2. Deterministic semantic correctness ────────────────────────────────────

class TestDeterministicSemantics:
    def test_uses_labeled_nodelay_wording(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate())
        assert "were labeled NODELAY" in text

    def test_no_no_recorded_delay_reason(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate()).lower()
        assert "no recorded delay reason" not in text

    def test_no_unattributed(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate()).lower()
        assert "unattributed" not in text

    def test_no_compliance_wording(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate()).lower()
        assert "compliance" not in text

    def test_no_data_quality_wording(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate()).lower()
        assert "data-quality" not in text
        assert "data quality" not in text

    def test_uses_percentage_points_not_pp(self):
        import re as _re
        text = DeterministicNarrativeProvider().generate(_make_candidate())
        assert "percentage points" in text
        assert not _re.search(r"\d\s+pp\b", text)

    def test_no_breach_terminology(self):
        text = DeterministicNarrativeProvider().generate(_make_candidate()).lower()
        assert "breach" not in text


# ── E. Fail-closed narrative validator ───────────────────────────────────────

class TestNarrativeValidator:
    def _provider_returning(self, text: str) -> BedrockNarrativeProvider:
        provider = BedrockNarrativeProvider(
            model_id="fake-model",
            region="us-east-1",
            fallback=DeterministicNarrativeProvider(),
        )
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": text}]}}
        }
        provider._client = mock_client
        return provider

    def test_safe_output_returned_normally(self):
        # Use only numbers present in the default _make_candidate() evidence set:
        # abs(ota_pp_change)=10.0, fleet_prior=65.0, fleet_current=58.0,
        # breach_count=8, eligible_vendor_count=10
        safe_text = (
            "Test Vendor OTA declined by 10.00 percentage points from May to June. "
            "Fleet OTA moved from 65.00% to 58.00%. "
            "8 of 10 eligible vendors crossed the configured deterioration threshold."
        )
        result = self._provider_returning(safe_text).generate(_make_candidate())
        assert result == safe_text

    def test_unsafe_causal_output_falls_back(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()
        unsafe = "The OTA decline was caused by TRAFFIC congestion in the current period."
        provider = self._provider_returning(unsafe)
        provider._fallback = det
        result = provider.generate(c)
        assert result == det.generate(c)

    def test_unsafe_nodelay_interpretation_falls_back(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()
        unsafe = "91.1% had no recorded delay reason, suggesting data-quality issues."
        provider = self._provider_returning(unsafe)
        provider._fallback = det
        result = provider.generate(c)
        assert result == det.generate(c)

    def test_unsafe_fleet_magnitude_comparison_falls_back(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()
        unsafe = "The vendor's decline exceeds the fleet OTA change significantly."
        provider = self._provider_returning(unsafe)
        provider._fallback = det
        result = provider.generate(c)
        assert result == det.generate(c)

    def test_unsafe_breach_terminology_falls_back(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()
        unsafe = "18 vendors breached the threshold in this period."
        provider = self._provider_returning(unsafe)
        provider._fallback = det
        result = provider.generate(c)
        assert result == det.generate(c)

    def test_numeric_pp_normalized_to_percentage_points(self):
        # Use candidate whose numbers match the text exactly for provenance pass.
        c = _make_candidate(ota_pp_change=-7.86, fleet_ota_pp_change=-5.84)
        raw = (
            "OTA declined by 7.86 pp from May to June. "
            "Fleet moved 5.84 pp. "
            "8 of 10 vendors crossed the configured threshold."
        )
        result = self._provider_returning(raw).generate(c)
        assert "7.86 percentage points" in result
        assert "5.84 percentage points" in result


# ── F. Expanded validator coverage ───────────────────────────────────────────

class TestValidatorExpansions:
    """Regression tests for patterns added in the second hardening pass."""

    def _provider_returning(self, text: str, candidate=None) -> BedrockNarrativeProvider:
        c = candidate or _make_candidate()
        provider = BedrockNarrativeProvider(
            model_id="fake-model",
            region="us-east-1",
            fallback=DeterministicNarrativeProvider(),
        )
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": text}]}}
        }
        provider._client = mock_client
        return provider

    # ── Qualitative severity ──────────────────────────────────────────────────

    def test_widespread_exact_observed_form_falls_back(self):
        # Exact form observed in a live Bedrock invocation.
        c = _make_candidate(breach_count=18, eligible_vendor_count=21)
        unsafe = (
            "18 of 21 vendors crossed the threshold, "
            "indicating deterioration is widespread across the fleet."
        )
        det = DeterministicNarrativeProvider()
        p = self._provider_returning(unsafe, candidate=c)
        p._fallback = det
        assert p.generate(c) == det.generate(c)

    def test_pervasive_falls_back(self):
        c = _make_candidate(breach_count=8, eligible_vendor_count=10)
        p = self._provider_returning(
            "OTA deterioration is pervasive across vendors.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_severe_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning("The vendor experienced severe OTA decline.", candidate=c)
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_systemic_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "This represents a systemic deterioration pattern.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    # ── Ranking language ──────────────────────────────────────────────────────

    def test_best_vendor_ranking_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning("Meera is one of the best vendors.", candidate=c)
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_worst_vendor_ranking_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "Meera is the worst-performing vendor.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    # ── Expanded causal forms ─────────────────────────────────────────────────

    def test_driven_by_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "OTA deterioration was driven by TRAFFIC.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_because_of_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "OTA declined because of DRIVER issues.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_contributed_to_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "NODELAY contributed to the deterioration.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    # ── Residual pp ───────────────────────────────────────────────────────────

    def test_residual_pp_without_number_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning("OTA experienced a pp decline.", candidate=c)
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    # ── NODELAY phrase coverage ───────────────────────────────────────────────

    def test_nodelay_missing_reason_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "NODELAY indicates a missing reason.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_nodelay_reason_not_captured_falls_back(self):
        c = _make_candidate()
        p = self._provider_returning(
            "NODELAY means the reason was not captured.", candidate=c
        )
        p._fallback = DeterministicNarrativeProvider()
        assert p.generate(c) == DeterministicNarrativeProvider().generate(c)

    def test_safe_nodelay_recorded_label_accepted(self):
        c = _make_candidate()
        safe = (
            "NODELAY is a recorded source-data label "
            "whose operational meaning is not established."
        )
        p = self._provider_returning(safe, candidate=c)
        assert p.generate(c) == safe


# ── G. Numeric provenance ─────────────────────────────────────────────────────

class TestNumericProvenance:
    """Verify that numeric values not supplied to the model cause fallback."""

    def _provider_returning(self, text: str, candidate=None) -> BedrockNarrativeProvider:
        c = candidate or _make_candidate()
        provider = BedrockNarrativeProvider(
            model_id="fake-model",
            region="us-east-1",
            fallback=DeterministicNarrativeProvider(),
        )
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": text}]}}
        }
        provider._client = mock_client
        return provider

    def test_provenance_rejects_invented_trip_count(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()  # current_total_count=1000
        p = self._provider_returning("Based on 3,000 trips.", candidate=c)
        p._fallback = det
        assert p.generate(c) == det.generate(c)

    def test_provenance_rejects_invented_percentage(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()
        p = self._provider_returning("90% of trips were affected.", candidate=c)
        p._fallback = det
        assert p.generate(c) == det.generate(c)

    def test_provenance_rejects_invented_vendor_count(self):
        det = DeterministicNarrativeProvider()
        c = _make_candidate()  # eligible_vendor_count=10
        p = self._provider_returning("12 vendors crossed the threshold.", candidate=c)
        p._fallback = det
        assert p.generate(c) == det.generate(c)

    def test_provenance_accepts_formatted_supplied_count(self):
        c = _make_candidate()  # current_total_count=1000
        safe = "Based on 1,000 current-period trips."
        p = self._provider_returning(safe, candidate=c)
        assert p.generate(c) == safe

    def test_provenance_accepts_safe_supplied_numbers(self):
        # All numbers are from default _make_candidate() evidence.
        c = _make_candidate()
        safe = (
            "Test Vendor OTA declined by 10.00 percentage points, "
            "from 70.00% to 60.00%, based on 1,000 current-period trips. "
            "Fleet OTA moved from 65.00% to 58.00%. "
            "8 of 10 eligible vendors crossed the configured deterioration threshold."
        )
        p = self._provider_returning(safe, candidate=c)
        assert p.generate(c) == safe
