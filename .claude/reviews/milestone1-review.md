# Code Review: Milestone 1 — Data Foundation

**Reviewed**: 2026-09-16
**Scope**: All new source files in `src/moveinsync_ota/` and `tests/`
**Decision**: APPROVE with comments

## Summary
Milestone 1 is well-structured, correctly implements the calibration-specified exclusion order,
and passes all 60 tests. No security issues, no CRITICAL or HIGH findings. Five MEDIUM issues
identified: one dead code block, one unused function, one missing type parameter, one silent
bad-data path, and one redundant test fixture registration.

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM

**M1 — `except SchemaValidationError: raise` is dead code**
- File: `src/moveinsync_ota/data/loader.py:90–91`
- `SchemaValidationError` is not an `OSError` subclass and cannot be caught by the following
  `except OSError` block, so the re-raise guard does nothing.
- Fix: remove lines 90–91; the exception propagates naturally.

**M2 — `guard_na` is defined but never called in production code**
- File: `src/moveinsync_ota/data/normalise.py:21–23`
- Tested in `test_normalise.py` but unused in `loader.py` or `config.py`.
  Dead production code. If needed by M2, leave it — otherwise remove.
- Fix: delete or document that M2 will use it.

**M3 — `Counter` field not type-parameterized**
- File: `src/moveinsync_ota/data/schema.py:13`
- `Counter` should be `Counter[str]` for full type safety.
- Fix: `late_delay_reason_counts: Counter[str] = field(default_factory=Counter)`

**M4 — Empty `vendor_id` silently creates a blank key in `vendor_stats`**
- File: `src/moveinsync_ota/data/loader.py:64`
- If a row has a blank `vendor_id`, it produces `vendor_stats[""]`. No error is raised.
  This is invisible in normal data but would corrupt aggregation totals if it occurred.
- Fix: add `if not vendor_id: continue` (and increment a counter for audit).
  Or accept as-is if blank `vendor_id` is impossible per domain contract.

**M5 — `pytest_configure` in `test_integration.py` is redundant**
- File: `tests/test_integration.py:22–24`
- The `integration` marker is already declared in `pyproject.toml:[tool.pytest.ini_options]`.
  The `pytest_configure` hook re-registers it, which is harmless but noisy.
- Fix: remove `pytest_configure` from `test_integration.py`.

### LOW

**L1 — `parse_delay_reason` applies `.upper()` then `.lower()`**
- File: `src/moveinsync_ota/data/normalise.py:17–18`
- `s = str(raw).strip().upper()` then `s.lower() in _NA_CLASS` — double conversion is
  correct but reads oddly. Clearer: strip, check lower, then return upper.
- Fix (optional):
  ```python
  def parse_delay_reason(raw: str) -> str:
      s = str(raw).strip()
      return "UNKNOWN" if s.lower() in _NA_CLASS else s.upper()
  ```

**L2 — `csv.Error` from malformed CSV not caught**
- File: `src/moveinsync_ota/data/loader.py:83–93`
- A CSV with an unterminated quote field raises `csv.Error`, which is neither `OSError` nor
  `SchemaValidationError`. It will propagate as an uncaught exception.
- Fix (optional): add `except csv.Error as exc: raise DataLoadError(...)`.

## Validation Results

| Check | Result |
|---|---|
| Unit tests (46 tests) | Pass |
| Integration tests (14 tests) | Pass |
| Build / import | Pass |

## Files Reviewed

| File | Status |
|---|---|
| `src/moveinsync_ota/__init__.py` | Added |
| `src/moveinsync_ota/config.py` | Added |
| `src/moveinsync_ota/exceptions.py` | Added |
| `src/moveinsync_ota/data/__init__.py` | Added |
| `src/moveinsync_ota/data/schema.py` | Added |
| `src/moveinsync_ota/data/normalise.py` | Added |
| `src/moveinsync_ota/data/loader.py` | Added |
| `tests/__init__.py` | Added |
| `tests/test_normalise.py` | Added |
| `tests/test_loader.py` | Added |
| `tests/test_integration.py` | Added |
| `pyproject.toml` | Added |
| `.gitignore` | Modified |
