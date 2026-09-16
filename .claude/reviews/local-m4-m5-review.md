# Local Code Review: M4 + M5 (feat/ota-watchdog-mvp)

**Reviewed**: 2026-09-16
**Branch**: feat/ota-watchdog-mvp (uncommitted M4+M5 changes)
**Decision**: ACCEPT — post-fix verification complete

## Summary

The M4/M5 implementation is clean, correct, and commit-ready. The originally identified XSS blocker (`top_non_nodelay_reason` unescaped in `detailHTML`) and selected reliability issues (AWS region hard-default, missing period guard, silent Bedrock fallback, a11y gaps, package-data) were all fixed. 214 tests pass, HTTP smoke verification confirmed calibration pins (May→June: 21 eligible / 18 breach / 18 candidates; June→July: 21 eligible / 0 breach / 0 candidates), and no commit blockers remain.

---

## Findings

### CRITICAL
None.

---

### HIGH

**H1 — `service.py:64` — Unguarded `KeyError` when period not loaded**

`self._periods[prior_name]` raises `KeyError` with no meaningful message if:
- `replay()` is called before `load()` (possible if test state is injected without calling `load`)
- A period CSV was missing or skipped during `load_all_files`

The error bubbles up through the FastAPI route as a 500 with an opaque `KeyError: 'June'` — no context for the operator.

```python
# service.py:60-65 — current
prior_name, current_name = SUPPORTED_COMPARISONS[comparison_key]
started_at = datetime.now(timezone.utc)
comparison = compare_periods(
    self._periods[prior_name],   # KeyError if period absent
    self._periods[current_name],
```

**Fix:**
```python
if prior_name not in self._periods or current_name not in self._periods:
    missing = [p for p in (prior_name, current_name) if p not in self._periods]
    raise ValueError(
        f"Period(s) not loaded for '{comparison_key}': {missing}. "
        "Call load() before replay()."
    )
```

---

### MEDIUM

**M1 — `narrative.py:121` — Silent Bedrock fallback with no logging**

`except Exception: return self._fallback.generate(candidate)` swallows all Bedrock errors (auth failures, throttling, invalid model ID). An operator enabling `BEDROCK_MODEL_ID` would silently receive deterministic output with no indication that Bedrock is failing.

**Fix:** Log the exception before falling back:
```python
except Exception as exc:
    import logging
    logging.getLogger(__name__).warning(
        "BedrockNarrativeProvider failed, using fallback: %s", exc
    )
    return self._fallback.generate(candidate)
```

---

**M2 — `index.html:53` — `aria-labelledby="modal-title"` points to non-existent element**

The modal declares `aria-labelledby="modal-title"`, but no element with `id="modal-title"` exists in the static HTML or in the JS-injected `detailHTML()`. Screen readers will find no label for the dialog.

**Fix:** Switch to `aria-label="Alert detail"` on the modal, or have `detailHTML()` write the vendor name into an element with `id="modal-title"`.

---

**M3 — `index.html:24-25` — `role="tab"` without `aria-selected`**

Buttons with `role="tab"` require `aria-selected="true|false"` to announce their state to screen readers. State is tracked only via CSS class; screen readers have no way to identify which tab is selected.

**Fix:** Add `aria-selected="true/false"` to both buttons in the HTML, and toggle it alongside the class in `setupTabs()` in `app.js`.

---

**M4 — `app.js:205` — `Object.entries(d.full_distribution)` throws on null/undefined**

If the API response ever returns `full_distribution: null`, `Object.entries(null)` throws a `TypeError` and the modal renders only an error message.

**Fix:**
```js
const distRows = Object.entries(d.full_distribution || {})
```

---

### LOW

**L1 — `pyproject.toml:17` — `httpx>=0.27` is deprecated**

Starlette emits a deprecation warning on every test run. Swap to `httpx2` to eliminate the noise.

---

**L2 — `service.py:45,88,100-106` — `_runs` list grows unboundedly; `get_latest_run` is O(n)**

Every `replay()` appends to `_runs`. `get_latest_run()` scans the full list. For a demo this is negligible, but a `dict[str, AgentRun]` keyed by comparison_key would make both operations O(1).

---

**L3 — `narrative.py:103` — Vendor ID interpolated directly into LLM prompt**

`_build_prompt` inserts `c.vendor_id` verbatim. A vendor name with injected text could attempt prompt manipulation. Risk is low (source is internal CSV data), but noted.

---

**L4 — `tests/test_app.py:128` — `os.environ` mutation without monkeypatch in module-scoped fixture**

If `svc.load()` raises before `yield`, `OTA_TEST_MODE` leaks into subsequent tests. Use `try/finally` or `monkeypatch.setenv`.

---

## Validation Results

| Check | Result |
|---|---|
| Tests (`pytest`) | **Pass** — 207 passed, 0 failed |

---

## Post-fix verification

Patches applied 2026-09-16 per final pre-commit instruction.

### Fixes applied

| # | Finding | File | Change |
|---|---|---|---|
| H1 | XSS — `top_non_nodelay_reason` unescaped | `app/static/app.js:247` | Wrapped with `esc()` |
| + | `full_distribution` null guard | `app/static/app.js:205` | `Object.entries(d.full_distribution \|\| {})` |
| M1 | `"us-east-1"` hard-default overrides boto3 profile region | `app/narrative.py:67` | Removed default; `_get_client` passes `region_name` conditionally |
| + | Silent Bedrock fallback | `app/narrative.py:121` | Added `logging.getLogger(__name__).warning(...)` before fallback |
| M2 | KeyError if period not loaded | `app/service.py:64` | Added guard with descriptive `ValueError` |
| M3a | `aria-labelledby` orphan | `templates/index.html:53` | Changed to `aria-label="Alert detail"` |
| M3b | `role="tab"` without `aria-selected` | `templates/index.html:24-25` | Added `aria-selected="true/false"` |
| + | `aria-selected` not toggled on tab click | `app/static/app.js:setupTabs` | Toggle alongside CSS class in `setupTabs()` |
| L3 | No `package-data` for templates/static | `pyproject.toml` | Added `[tool.setuptools.package-data]` |
| + | New tests | `tests/test_service.py` | `TestMissingPeriodReplay` (3 tests) |
| + | New tests | `tests/test_narrative.py` | `TestBedrockFallback` (2 tests) |
| + | New tests | `tests/test_app.py` | `TestNarrativeCacheViaAPI` (2 tests) |

### Final verification

- `python -m pytest -q`: **214 passed, 0 failed**, 3 non-blocking deprecation warnings
- `git diff --check`: **clean** (no whitespace errors)
- `git diff --name-only HEAD`: only `pyproject.toml` (modified); all M4/M5 files untracked — no raw CSV changes, no M1/M2/M3 modifications
- HTTP smoke (port 8002):
  - `GET /` → 200 HTML ✓
  - `GET /api/state` → may-june: eligible=21, breach=18, candidates=18 ✓
  - `POST /api/replay/may-june` → eligible=21, breach=18, candidates=18 ✓
  - `POST /api/replay/june-july` → eligible=21, breach=0, candidates=0 ✓
  - `GET /api/alerts/{id}` → 200, deterministic narrative present ✓
- No credentials added. No shell-based source-file writes. No M1/M2/M3 semantic changes.

**Verdict after fixes: ACCEPT — ready for commit.**

---

## Files Reviewed

| File | Change |
|---|---|
| `pyproject.toml` | Modified |
| `src/moveinsync_ota/app/__init__.py` | Added |
| `src/moveinsync_ota/app/service.py` | Added |
| `src/moveinsync_ota/app/narrative.py` | Added |
| `src/moveinsync_ota/app/main.py` | Added |
| `src/moveinsync_ota/app/templates/index.html` | Added |
| `src/moveinsync_ota/app/static/app.css` | Added |
| `src/moveinsync_ota/app/static/app.js` | Added |
| `tests/test_service.py` | Added |
| `tests/test_narrative.py` | Added |
| `tests/test_app.py` | Added |
