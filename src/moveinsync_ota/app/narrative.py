from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod

from moveinsync_ota.alerts.models import AlertCandidate

_log = logging.getLogger(__name__)

# ── Unsafe-pattern registry ───────────────────────────────────────────────────
# Each entry is an independently auditable rule. If any fires on a generated
# narrative, the text is rejected and the deterministic fallback is returned.

_UNSAFE_PATTERNS: list[re.Pattern[str]] = [
    # Causal attribution — all forms
    re.compile(r"caused\s+by",                      re.I),
    re.compile(r"caused\s+the",                     re.I),
    re.compile(r"\broot\s+cause\b",                 re.I),
    re.compile(r"\bdue\s+to\b",                     re.I),
    re.compile(r"\bbecause\s+of\b",                 re.I),
    re.compile(r"\bdriven\s+by\b",                  re.I),
    re.compile(r"\bresults?\s+from\b",              re.I),
    re.compile(r"\bled\s+to\b",                     re.I),
    re.compile(r"\bresponsible\s+for\b",            re.I),
    re.compile(r"\bcontribut(?:ed|ing)\s+to\b",     re.I),
    # NODELAY semantic misinterpretation
    re.compile(r"\bunattributed\b",                 re.I),
    re.compile(r"no\s+recorded\s+delay\s+reason",   re.I),
    re.compile(r"no\s+recorded\s+context",          re.I),
    re.compile(r"data.?quality\s+signal",           re.I),
    re.compile(r"\bcompliance\b",                   re.I),
    re.compile(r"\bmissing\s+reason\b",             re.I),
    re.compile(r"\bunknown\s+reason\b",             re.I),
    re.compile(r"reason.{0,20}not.{0,30}captured",  re.I | re.DOTALL),
    re.compile(r"\buncoded\b",                      re.I),
    re.compile(r"incomplete\s+recording",           re.I),
    re.compile(r"poor\s+reason\s+capture",          re.I),
    # Qualitative scale / severity language
    re.compile(r"\bwidespread\b",                   re.I),
    re.compile(r"\bpervasive\b",                    re.I),
    re.compile(r"\bsevere\b",                       re.I),
    re.compile(r"broad.?based",                     re.I),
    re.compile(r"\bbroadly\s+deteriorating\b",      re.I),
    re.compile(r"\bsystemic\b",                     re.I),
    re.compile(r"\bbroad\s+deterioration\b",        re.I),
    # Ranking language
    re.compile(r"\boutperform\b",                   re.I),
    re.compile(r"\bunderperform\b",                 re.I),
    re.compile(r"\bbenchmark\b",                    re.I),
    re.compile(r"\bbest\b",                         re.I),
    re.compile(r"\bworst\b",                        re.I),
    re.compile(r"\bleader\b",                       re.I),
    re.compile(r"\blaggard\b",                      re.I),
    # Breach terminology in narrative
    re.compile(r"\bbreach(?:es|ed)?\b",             re.I),
    # Vendor-change vs fleet-change magnitude comparisons
    re.compile(r"exceed.{0,60}fleet.{0,100}change", re.I | re.DOTALL),
    re.compile(r"larger.{0,25}than.{0,60}fleet.{0,100}change", re.I | re.DOTALL),
    re.compile(r"greater.{0,25}than.{0,60}fleet.{0,100}change", re.I | re.DOTALL),
    re.compile(r"declin\w*.{0,25}more.{0,25}than.{0,60}fleet", re.I | re.DOTALL),
    # Residual "pp" abbreviation (after numeric normalization)
    re.compile(r"\bpp\b",                           re.I),
]

# Normalizes "7.86 pp" → "7.86 percentage points" before validation.
_PP_NORMALIZE = re.compile(r"(\d[\d.,]*)\s+pp\b", re.I)

# Extracts numeric tokens (integer or decimal, with optional comma separators).
_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?")


def _normalize_pp(text: str) -> str:
    return _PP_NORMALIZE.sub(r"\1 percentage points", text)


def _is_safe_narrative(text: str) -> bool:
    """Return True only if no unsafe patterns fire."""
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(text):
            return False
    return True


def _build_permitted_numbers(c: AlertCandidate) -> frozenset[float]:
    """Build the set of numeric values explicitly supplied in the Bedrock prompt."""
    return frozenset([
        c.prior_ota_pct,
        c.current_ota_pct,
        abs(c.ota_pp_change),
        float(c.prior_total_count),
        float(c.current_total_count),
        c.fleet_prior_ota_pct,
        c.fleet_current_ota_pct,
        abs(c.fleet_ota_pp_change),
        float(c.eligible_vendor_count),
        float(c.breach_count),
        float(c.total_late_count),
        float(c.nodelay_count),
        round(c.nodelay_share * 100, 1),
        float(c.top_non_nodelay_count),
    ])


def _extract_numbers(text: str) -> list[float]:
    nums = []
    for m in _NUMBER_RE.finditer(text):
        try:
            nums.append(float(m.group().replace(",", "")))
        except ValueError:
            pass
    return nums


def _numeric_provenance_ok(text: str, candidate: AlertCandidate) -> bool:
    """Return True only if every numeric token in text is in the permitted set."""
    permitted = _build_permitted_numbers(candidate)
    for n in _extract_numbers(text):
        if not any(abs(n - p) < 1e-6 for p in permitted):
            return False
    return True


class NarrativeProvider(ABC):
    @abstractmethod
    def generate(self, candidate: AlertCandidate) -> str: ...


class DeterministicNarrativeProvider(NarrativeProvider):
    def generate(self, candidate: AlertCandidate) -> str:
        c = candidate
        pp = abs(c.ota_pp_change)

        obs = (
            f"Observation: {c.vendor_id} OTA declined by {pp:.2f} percentage points, "
            f"from {c.prior_ota_pct:.2f}% to {c.current_ota_pct:.2f}%, "
            f"based on {c.current_total_count:,} current-period trips."
        )

        fleet = (
            f"Fleet context: Fleet OTA moved from {c.fleet_prior_ota_pct:.2f}% to "
            f"{c.fleet_current_ota_pct:.2f}%, a change of "
            f"{abs(c.fleet_ota_pp_change):.2f} percentage points. "
            f"{c.breach_count} of {c.eligible_vendor_count} eligible vendors crossed the "
            f"configured deterioration threshold."
        )

        delay = (
            f"Recorded delay context: Of {c.total_late_count:,} late trips, "
            f"{c.nodelay_count:,} ({c.nodelay_share:.1%}) were labeled NODELAY."
        )
        if c.top_non_nodelay_reason:
            delay += (
                f" Among non-NODELAY labels, {c.top_non_nodelay_reason} was most frequent "
                f"at {c.top_non_nodelay_count:,} trips. "
                f"Recorded delay labels are contextual and do not establish causality."
            )
        else:
            delay += " No non-NODELAY labels were recorded."

        action = (
            "Suggested action: Review the OTA deterioration with the vendor and validate "
            "operational conditions. Validate the operational meaning of NODELAY before "
            "using the recorded label distribution diagnostically."
        )

        return "\n\n".join([obs, fleet, delay, action])


class BedrockNarrativeProvider(NarrativeProvider):
    def __init__(
        self,
        model_id: str,
        region: str | None = None,
        fallback: NarrativeProvider | None = None,
    ) -> None:
        self._model_id = model_id
        self._region = (
            region
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
        )
        self._fallback = fallback or DeterministicNarrativeProvider()
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            if self._region:
                self._client = boto3.client("bedrock-runtime", region_name=self._region)
            else:
                self._client = boto3.client("bedrock-runtime")
        return self._client

    def _build_prompt(self, c: AlertCandidate) -> str:
        return (
            "You are an operations analyst assistant. Summarize the following OTA "
            "deterioration alert for a Transport Manager in 4 short paragraphs: "
            "Observation, Fleet Context, Recorded Delay Context, Suggested Action.\n\n"
            "RULES:\n"
            "- Do not calculate or re-derive any metrics. Use only the numbers supplied.\n"
            "- Do not introduce new calculations or numbers not present in the alert data.\n"
            "- Do not claim causality. Use 'Recorded delay context shows' not 'X caused Y'.\n"
            "- Recorded delay reasons are context only; they do not prove root cause.\n"
            "- When comparing the vendor to fleet, use only 'above/below the fleet-level OTA'.\n"
            "- Do not use ranking language: 'outperform', 'underperform', 'best', 'worst', "
            "'benchmark', or similar, unless that exact ranking is present in the alert data.\n"
            "- Do not infer root cause from delay reason codes.\n"
            "- NODELAY is a literal source-data category. Its business meaning is not "
            "provided. Do not interpret or expand the meaning of NODELAY.\n"
            "- Never compare the magnitude of vendor OTA change to the magnitude of "
            "fleet OTA change.\n"
            "- If comparing vendor and fleet, compare current OTA levels only.\n"
            "- State threshold-crossing counts numerically. Do not characterize them as "
            "widespread, severe, broad, pervasive, or similar qualitative labels.\n"
            "- Use the words 'percentage points', never 'pp'.\n"
            "- Use 'threshold crossing', never 'breach'.\n"
            "- Keep under 200 words.\n\n"
            f"ALERT DATA:\n"
            f"Vendor: {c.vendor_id}\n"
            f"Period: {c.prior_period} to {c.current_period}\n"
            f"Prior OTA: {c.prior_ota_pct:.2f}%\n"
            f"Current OTA: {c.current_ota_pct:.2f}%\n"
            f"OTA Change: {c.ota_pp_change:.2f} percentage points\n"
            f"Prior trips: {c.prior_total_count:,}\n"
            f"Current trips: {c.current_total_count:,}\n"
            f"Fleet prior OTA: {c.fleet_prior_ota_pct:.2f}%\n"
            f"Fleet current OTA: {c.fleet_current_ota_pct:.2f}%\n"
            f"Fleet change: {c.fleet_ota_pp_change:.2f} percentage points\n"
            f"Eligible vendors: {c.eligible_vendor_count}\n"
            f"Threshold crossings: {c.breach_count}\n"
            f"Late trips: {c.total_late_count:,}\n"
            f"NODELAY trips: {c.nodelay_count:,} ({c.nodelay_share:.1%})\n"
            f"NODELAY most frequent label: {c.nodelay_dominates}\n"
            f"Top non-NODELAY reason: {c.top_non_nodelay_reason or 'None'} "
            f"({c.top_non_nodelay_count:,} trips)\n"
        )

    def generate(self, candidate: AlertCandidate) -> str:
        try:
            client = self._get_client()
            response = client.converse(
                modelId=self._model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": self._build_prompt(candidate)}],
                    }
                ],
                inferenceConfig={"maxTokens": 400, "temperature": 0.3},
            )
            raw = response["output"]["message"]["content"][0]["text"]
            normalized = _normalize_pp(raw)
            if not _is_safe_narrative(normalized):
                _log.warning(
                    "Bedrock narrative failed safety validation; using deterministic fallback"
                )
                return self._fallback.generate(candidate)
            if not _numeric_provenance_ok(normalized, candidate):
                _log.warning(
                    "Bedrock narrative failed numeric provenance check; using deterministic fallback"
                )
                return self._fallback.generate(candidate)
            return normalized
        except Exception as exc:
            _log.warning(
                "Bedrock narrative generation failed; using deterministic fallback: %s", exc
            )
            return self._fallback.generate(candidate)
