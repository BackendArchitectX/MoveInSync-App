# Plan: OTA Watchdog — Milestones 4 & 5

**Source PRD**: `.claude/prds/ota-watchdog.prd.md`
**Milestones**: M4 Operational Brief + Demo UI · M5 Agentic Replay Flow
**Complexity**: Medium

## Summary

M4 adds a FastAPI + Jinja2 web layer with a NarrativeProvider abstraction
(deterministic fallback + optional Amazon Bedrock). M5 wires a SENSE→REASON→ACT
replay cycle with autonomous startup, de-duplicated in-memory feed, and replay
controls. One Python process, no external services required.

## New Files

| File | Purpose |
|------|---------|
| `src/moveinsync_ota/app/__init__.py` | Package marker |
| `src/moveinsync_ota/app/service.py` | `OTAService` — loads data once, runs comparisons, owns feed + runs |
| `src/moveinsync_ota/app/narrative.py` | `NarrativeProvider`, `DeterministicNarrativeProvider`, `BedrockNarrativeProvider` |
| `src/moveinsync_ota/app/main.py` | FastAPI app, lifespan, routes, JSON serialisation helpers |
| `src/moveinsync_ota/app/templates/index.html` | Single-page Jinja2 shell |
| `src/moveinsync_ota/app/static/app.css` | Responsive styles |
| `src/moveinsync_ota/app/static/app.js` | Vanilla JS: fetch state, render feed, modal detail, replay |
| `tests/test_service.py` | OTAService unit + integration tests |
| `tests/test_narrative.py` | Deterministic narrative + cache tests |
| `tests/test_app.py` | FastAPI TestClient smoke tests |

## Modified Files

| File | Change |
|------|--------|
| `pyproject.toml` | Add `fastapi`, `uvicorn[standard]`, `jinja2`, `boto3`; add `httpx` to dev |

## Key Design Decisions

- `OTAService.load(_periods=None)` accepts override list for unit tests
- `main.py` respects `OTA_TEST_MODE=1` env var to skip lifespan data load
- `_inject_test_state(svc, narrative)` in `main.py` for TestClient fixtures
- Narrative cache: `dict[alert_id, str]` in process memory; reset by `_inject_test_state`
- `BedrockNarrativeProvider` wraps any exception and delegates to `fallback`
- `run_id` = SHA-256 of comparison key (deterministic; timestamps never affect `alert_id`)
- Feed de-duplication: `_feed: dict[alert_id, AlertCandidate]` — same ID overwrites

## Agentic Lifecycle (M5)

```
SENSE  -> load period aggregates from PeriodLoadResult
REASON -> compare_periods() -> PeriodComparison (volume, OTA, fleet, threshold)
ACT    -> build_alert_candidates() -> AlertCandidate objects into in-memory feed
```

Narrative summarization is presentation assistance; it is NOT the breach decision.

## Run Command

```bash
python -m uvicorn moveinsync_ota.app.main:app --reload --port 8001
```

## Bedrock Configuration

```
BEDROCK_MODEL_ID=<model-id>    # e.g. amazon.titan-text-express-v1
AWS_REGION=us-east-1
AWS_PROFILE=<profile>          # optional; uses standard boto3 credential chain
```

If BEDROCK_MODEL_ID is absent or Bedrock fails for any reason, the deterministic
narrative is used transparently. The demo never fails because Bedrock is unavailable.

## Stop Condition

STOP after M5. No commit. No README/deck hardening.
