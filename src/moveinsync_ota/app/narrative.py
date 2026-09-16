from __future__ import annotations

import os
from abc import ABC, abstractmethod

from moveinsync_ota.alerts.models import AlertCandidate


class NarrativeProvider(ABC):
    @abstractmethod
    def generate(self, candidate: AlertCandidate) -> str: ...


class DeterministicNarrativeProvider(NarrativeProvider):
    def generate(self, candidate: AlertCandidate) -> str:
        c = candidate
        pp = abs(c.ota_pp_change)

        obs = (
            f"Observation: {c.vendor_id} recorded a {pp:.1f} pp OTA decline "
            f"({c.prior_ota_pct:.1f}% to {c.current_ota_pct:.1f}%) "
            f"from {c.prior_period} to {c.current_period}, "
            f"based on {c.current_total_count:,} trips."
        )

        fleet = (
            f"Fleet context: Across {c.eligible_vendor_count} eligible vendors, "
            f"fleet OTA moved {c.fleet_prior_ota_pct:.1f}% to {c.fleet_current_ota_pct:.1f}% "
            f"({c.fleet_ota_pp_change:+.1f} pp). "
            f"{c.breach_count} of {c.eligible_vendor_count} vendors crossed the deterioration threshold."
        )

        delay = (
            f"Recorded delay context: Of {c.total_late_count:,} late trips, "
            f"{c.nodelay_count:,} ({c.nodelay_share:.0%}) had no recorded delay reason (NODELAY)."
        )
        if c.top_non_nodelay_reason:
            delay += (
                f" The most-recorded non-NODELAY reason was {c.top_non_nodelay_reason} "
                f"({c.top_non_nodelay_count:,} trips, {c.top_non_nodelay_share:.0%} of late trips). "
                f"Recorded delay context shows operational data only; "
                f"causality cannot be inferred from delay reason codes."
            )
        else:
            delay += " No non-NODELAY reasons were recorded."

        action = (
            "Suggested action: Review vendor operations and validate contributing conditions. "
            "Confirm data completeness for trips marked NODELAY before drawing operational conclusions."
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
            "- Keep under 200 words.\n\n"
            f"ALERT DATA:\n"
            f"Vendor: {c.vendor_id}\n"
            f"Period: {c.prior_period} to {c.current_period}\n"
            f"Prior OTA: {c.prior_ota_pct:.2f}%\n"
            f"Current OTA: {c.current_ota_pct:.2f}%\n"
            f"OTA Change: {c.ota_pp_change:.2f} pp\n"
            f"Prior trips: {c.prior_total_count:,}\n"
            f"Current trips: {c.current_total_count:,}\n"
            f"Fleet prior OTA: {c.fleet_prior_ota_pct:.2f}%\n"
            f"Fleet current OTA: {c.fleet_current_ota_pct:.2f}%\n"
            f"Fleet change: {c.fleet_ota_pp_change:.2f} pp\n"
            f"Eligible vendors: {c.eligible_vendor_count}\n"
            f"Breach count: {c.breach_count}\n"
            f"Late trips: {c.total_late_count:,}\n"
            f"NODELAY trips: {c.nodelay_count:,} ({c.nodelay_share:.1%})\n"
            f"NODELAY dominates: {c.nodelay_dominates}\n"
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
            return response["output"]["message"]["content"][0]["text"]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Bedrock narrative generation failed; using deterministic fallback: %s", exc
            )
            return self._fallback.generate(candidate)
