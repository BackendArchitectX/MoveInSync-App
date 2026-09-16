from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from moveinsync_ota.alerts.models import AlertCandidate
from moveinsync_ota.app.narrative import (
    BedrockNarrativeProvider,
    DeterministicNarrativeProvider,
    NarrativeProvider,
)
from moveinsync_ota.app.service import AgentRun, OTAService, SUPPORTED_COMPARISONS
from moveinsync_ota.compute.comparison import PeriodComparison

_svc: OTAService | None = None
_narrative: NarrativeProvider | None = None
_narrative_cache: dict[str, str] = {}


def _inject_test_state(
    svc: OTAService,
    narrative: NarrativeProvider | None = None,
) -> None:
    global _svc, _narrative, _narrative_cache
    _svc = svc
    _narrative = narrative or DeterministicNarrativeProvider()
    _narrative_cache = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _svc, _narrative
    if os.environ.get("OTA_TEST_MODE") == "1":
        if _svc is None:
            _svc = OTAService()
        if _narrative is None:
            _narrative = DeterministicNarrativeProvider()
        yield
        return

    _svc = OTAService()
    _svc.load()

    det = DeterministicNarrativeProvider()
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    _narrative = (
        BedrockNarrativeProvider(model_id=model_id, fallback=det) if model_id else det
    )

    demo_prior = os.environ.get("OTA_DEMO_PRIOR_PERIOD", "May")
    demo_current = os.environ.get("OTA_DEMO_CURRENT_PERIOD", "June")
    demo_key = f"{demo_prior.lower()}-{demo_current.lower()}"
    if demo_key in SUPPORTED_COMPARISONS:
        _svc.replay(demo_key)

    yield


_HERE = Path(__file__).parent
app = FastAPI(title="OTA Watchdog", lifespan=lifespan)
templates = Jinja2Templates(directory=str(_HERE / "templates"))
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")


# ── Serialisation helpers ────────────────────────────────────────────────────

def _run_dict(run: AgentRun) -> dict:
    return {
        "run_id": run.run_id,
        "prior_period": run.prior_period,
        "current_period": run.current_period,
        "status": run.status,
        "eligible_vendor_count": run.eligible_vendor_count,
        "breach_count": run.breach_count,
        "candidate_count": run.candidate_count,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _comparison_dict(comp: PeriodComparison) -> dict:
    return {
        "prior_period": comp.prior_period,
        "current_period": comp.current_period,
        "eligible_vendor_count": len(comp.eligible_vendor_ids),
        "fleet_prior_ota_pct": round(comp.fleet_prior_ota_pct, 2),
        "fleet_current_ota_pct": round(comp.fleet_current_ota_pct, 2),
        "fleet_ota_pp_change": round(comp.fleet_ota_pp_change, 2),
        "breach_count": comp.breach_count,
        "breach_pct": round(comp.breach_pct, 2),
        "t_seconds": comp.t_seconds,
        "vol_min": comp.vol_min,
        "deterioration_threshold_pp": comp.deterioration_threshold_pp,
    }


def _card_dict(c: AlertCandidate) -> dict:
    return {
        "alert_id": c.alert_id,
        "vendor_id": c.vendor_id,
        "prior_period": c.prior_period,
        "current_period": c.current_period,
        "prior_ota_pct": round(c.prior_ota_pct, 2),
        "current_ota_pct": round(c.current_ota_pct, 2),
        "ota_pp_change": round(c.ota_pp_change, 2),
        "current_total_count": c.current_total_count,
        "fleet_ota_pp_change": round(c.fleet_ota_pp_change, 2),
        "top_non_nodelay_reason": c.top_non_nodelay_reason,
        "nodelay_dominates": c.nodelay_dominates,
        "nodelay_share": round(c.nodelay_share, 3),
    }


def _detail_dict(c: AlertCandidate) -> dict:
    return {
        "alert_id": c.alert_id,
        "policy_version": c.policy_version,
        "vendor_id": c.vendor_id,
        "prior_period": c.prior_period,
        "current_period": c.current_period,
        "prior_ota_pct": round(c.prior_ota_pct, 2),
        "current_ota_pct": round(c.current_ota_pct, 2),
        "ota_pp_change": round(c.ota_pp_change, 2),
        "prior_total_count": c.prior_total_count,
        "current_total_count": c.current_total_count,
        "fleet_prior_ota_pct": round(c.fleet_prior_ota_pct, 2),
        "fleet_current_ota_pct": round(c.fleet_current_ota_pct, 2),
        "fleet_ota_pp_change": round(c.fleet_ota_pp_change, 2),
        "eligible_vendor_count": c.eligible_vendor_count,
        "breach_count": c.breach_count,
        "breach_pct": round(c.breach_pct, 2),
        "total_late_count": c.total_late_count,
        "nodelay_count": c.nodelay_count,
        "nodelay_share": round(c.nodelay_share, 3),
        "nodelay_dominates": c.nodelay_dominates,
        "top_non_nodelay_reason": c.top_non_nodelay_reason,
        "top_non_nodelay_count": c.top_non_nodelay_count,
        "top_non_nodelay_share": round(c.top_non_nodelay_share, 3),
        "full_distribution": c.full_distribution,
        "T_seconds": c.T_seconds,
        "vol_min": c.vol_min,
        "deterioration_threshold_pp": c.deterioration_threshold_pp,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/state")
async def get_state():
    result = {}
    for key in SUPPORTED_COMPARISONS:
        run = _svc.get_latest_run(key)
        comp = _svc.get_comparison(key)
        candidates = _svc.get_candidates(key)
        result[key] = {
            "run": _run_dict(run) if run else None,
            "comparison": _comparison_dict(comp) if comp else None,
            "candidates": [_card_dict(c) for c in candidates],
        }
    return result


@app.get("/api/alerts/{alert_id}")
async def get_alert(alert_id: str):
    c = _svc.get_alert(alert_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert_id not in _narrative_cache:
        _narrative_cache[alert_id] = _narrative.generate(c)
    return {**_detail_dict(c), "narrative": _narrative_cache[alert_id]}


@app.post("/api/replay/{comparison}")
async def replay(comparison: str):
    key = comparison.lower()
    if key not in SUPPORTED_COMPARISONS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported comparison '{comparison}'. "
                f"Supported: {sorted(SUPPORTED_COMPARISONS)}"
            ),
        )
    run = _svc.replay(key)
    comp = _svc.get_comparison(key)
    candidates = _svc.get_candidates(key)
    return {
        "run": _run_dict(run),
        "comparison": _comparison_dict(comp),
        "candidates": [_card_dict(c) for c in candidates],
    }
