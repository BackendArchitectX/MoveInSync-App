# Plan: OTA Watchdog — Milestones 2 & 3

**Source PRD**: `.claude/prds/ota-watchdog.prd.md`
**Milestones**: M2 OTA Computation & Context Engine · M3 Detection & Evidence Assembly
**Complexity**: Medium

## Summary

M2 computes per-vendor and fleet OTA percentages for each qualifying vendor pair,
plus delay-reason context for late trips. M3 assembles `AlertCandidate` evidence
bundles for every vendor whose OTA deteriorated beyond the configured threshold.
No alert firing, LLM prose, persistence, or external delivery is implemented.

## Calibration Gates (must pass before M3, then again at final run)

| Profile | Assert |
|---------|--------|
| May→June eligible vendors | 21 |
| Fleet May OTA | ≈ 46.98 % |
| Fleet June OTA | ≈ 41.14 % |
| Fleet Δ May→Jun | ≈ −5.84 pp |
| May→June breach count | 18 |
| June→July breach count | 0 |
| Meera Pavlov Travel: prior OTA | ≈ 76.39 % |
| Meera Pavlov Travel: current OTA | ≈ 68.53 % |
| Meera Pavlov Travel: Δ pp | ≈ −7.86 pp |
| Meera Pavlov Travel: nodelay_dominates | True |
| Meera Pavlov Travel: top non-NODELAY | TRAFFIC |

## Key Semantic Rules

- `eligible(v, prior, current)` ↔ `prior.total_count >= VOL_MIN AND current.total_count >= VOL_MIN`
- `vendor_ota_pct = ontime / total × 100` (full precision, no rounding before comparisons)
- `fleet_ota_pct` = trip-weighted over SAME eligible cohort; never average of vendor %
- `ota_pp_change = current_ota − prior_ota` (negative = deterioration)
- `is_deterioration = ota_pp_change < −DETERIORATION_THRESHOLD_PP` (strict; −5.0 at 5.0 threshold is NOT a breach)
- `nodelay_dominates`: NODELAY > 0 AND NODELAY strictly > every non-NODELAY count (tie = False)
- Top non-NODELAY tie-break: highest count first; lexicographically smallest reason on tie
- `alert_id` = SHA-256 of canonical JSON `{policy_version, vendor_id, prior_period, current_period, T_SECONDS, VOL_MIN, DETERIORATION_THRESHOLD_PP}` with `sort_keys=True, separators=(',',':')`
- `policy_version = "ota-watchdog-v1"`
- Output order: `(ota_pp_change ASC, vendor_id ASC)` — worst deterioration first

## Files

| File | Action | Purpose |
|------|--------|---------|
| `src/moveinsync_ota/config.py` | UPDATE | Add `VOL_MIN=500`, `DETERIORATION_THRESHOLD_PP=5.0` |
| `src/moveinsync_ota/compute/__init__.py` | CREATE | Package marker |
| `src/moveinsync_ota/compute/volume.py` | CREATE | `apply_volume_filter` |
| `src/moveinsync_ota/compute/ota.py` | CREATE | `vendor_ota_pct`, `fleet_ota_pct` |
| `src/moveinsync_ota/compute/delay_context.py` | CREATE | `DelayReasonContext`, `build_delay_context` |
| `src/moveinsync_ota/compute/comparison.py` | CREATE | `VendorComparison`, `PeriodComparison`, `compare_periods` |
| `src/moveinsync_ota/alerts/__init__.py` | CREATE | Package marker |
| `src/moveinsync_ota/alerts/models.py` | CREATE | `AlertCandidate` dataclass |
| `src/moveinsync_ota/alerts/builder.py` | CREATE | `build_alert_candidates`, `POLICY_VERSION` |
| `tests/test_volume.py` | CREATE | Unit tests — volume filter |
| `tests/test_ota.py` | CREATE | Unit tests — OTA computation |
| `tests/test_delay_context.py` | CREATE | Unit tests — delay reason context |
| `tests/test_comparison.py` | CREATE | Unit tests — period comparison |
| `tests/test_alerts.py` | CREATE | Unit tests — alert candidate building |
| `tests/test_integration.py` | UPDATE | Add M2/M3 calibration test classes |

## Validation

```bash
python -m pytest tests/ -v -m "not integration"
python -m pytest tests/ -v -m integration
python -m pytest tests/ -v
```

## Stop condition

STOP after M3. Do not implement alert firing, LLM prose, persistence, scheduler,
or any external notification.

## Configuration Provenance (Batch-A fix)

`PeriodLoadResult` carries `t_seconds` — the exact OTA tolerance used during ingestion.
`PeriodComparison` carries all three policy values (`t_seconds`, `vol_min`, `deterioration_threshold_pp`);
`compare_periods` raises `ValueError` if prior/current have mismatched `t_seconds`.
`build_alert_candidates(comparison)` derives all policy from `comparison.*` — no independent
policy parameters — so every `AlertCandidate` is guaranteed to record the policy under which
its breach was evaluated.
