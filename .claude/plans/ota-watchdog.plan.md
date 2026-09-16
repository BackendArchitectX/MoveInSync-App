# Plan: OTA Watchdog — Data Foundation

**Source PRD**: `.claude/prds/ota-watchdog.prd.md`
**Selected Milestone**: Milestone 1 — Data Foundation
**Complexity**: Medium

---

## Architecture Decision

### Options compared

| Dimension | A. Python-first | B. Java/Spring Boot | C. Hybrid (Python analytics + Java API) |
|---|---|---|---|
| Implementation time | **Fastest** — calibration pipeline already proven in Python; no context switch | Slower — more boilerplate, compile cycle, bean wiring | **Slowest** — two languages, two build systems, IPC layer needed |
| Processing 615k CSV rows | Expected to be comfortably adequate for the supplied ~615k-row dataset; elapsed time will be measured during Milestone 1 validation | Excellent — JVM CSV processing is fast; strong typing reduces row-parsing bugs | Split concern; no benefit over pure Python for this volume |
| Deterministic reproducibility | High — pure functions, easy to test with StringIO | High — strong types reduce silent coercion bugs | Harder — must ensure both layers agree on edge-case handling |
| Testability | **Excellent** — pytest, StringIO fixtures, no build step | Good — JUnit 5, but Spring context overhead in tests | Complex — two separate test suites, integration surface between layers |
| Local setup complexity | **Low** — Python 3 + `pip install -e ".[dev]"` | Medium — JDK, Maven/Gradle, IDE configuration | **High** — both environments must be configured and kept in sync |
| In-app alert feed integration | Any REST API works for the Angular frontend; FastAPI produces OpenAPI docs automatically | Spring Boot REST is mature; OpenAPI via springdoc | No benefit from hybrid over pure Python |
| LLM integration (Milestone 4) | **Best** — Anthropic Python SDK is the primary SDK; streaming, tool-use, and structured output are all native | Good — Anthropic Java SDK exists; Spring AI available | Python side holds the LLM logic; Java side is redundant for this concern |
| Scheduled / replay execution (Milestone 5) | Clean — APScheduler or simple cron; agent loop is a Python `while True` | Good — Spring `@Scheduled`, Spring Batch | Complicated orchestration — two processes, shared state |
| Deployment / demo reliability | **Simple** — single Python process, `python -m uvicorn app:main`; no build step for demo | Good — fat JAR is portable; needs JRE on demo machine | Two processes to start and keep in sync; higher demo failure risk |
| Unnecessary cross-language complexity | None | None | **High** — IPC, serialisation, error propagation across boundary |

**Tech preference in source material:** `INPUT_AUDIT.md §NFR-5` records the problem statement as: *"Preferred tech stack: Java, Angular, AWS — but not restrictive."* No implementation language is mandated. The Architecture evaluation criterion (20 pts) rewards deployability into an enterprise platform and sound design — not language choice.

### Selected architecture: Option A — Python-first

**Rationale:**
1. The complete data pipeline is already validated end-to-end in Python through 10 calibration profiles. Porting to Java is rework with no new learning.
2. The agentic design criterion (20 pts) requires a working sense → reason → act loop. The Anthropic Python SDK is the primary SDK for this; Python is the natural language for the agent control loop.
3. FastAPI delivers a production-quality REST API with OpenAPI documentation in minimal code. The Angular frontend is language-agnostic.
4. Streaming aggregation in Python handles the supplied dataset with stdlib only and negligible memory (bounded aggregates, not materialised rows).
5. Option A gives more implementation hours for Milestones 4 and 5 (LLM + agentic scheduling), which carry 45 of the 100 evaluation points.
6. The preferred-but-not-restrictive Java preference does not override these tradeoffs.

**Angular frontend:** remains the plan for the presentation layer — it works with any REST API.

---

## Summary

Implement the ingestion and normalisation pipeline that reads `ride_data_trip` across three months using **streaming aggregation** — accumulate vendor/period OTA statistics directly from each CSV row, never materialising individual trip objects. Apply SPOT_2.0 exclusion, then null-epoch exclusion, in that exact order to preserve calibration-reproducible counts. Validate required headers at file open time. Expose typed `VendorPeriodAgg` and `PeriodLoadResult` aggregates as the verified data contract for Milestone 2.

**What Milestone 1 does NOT do:** no prior/current comparison, no volume eligibility decisions, no fleet cohort construction, no deterioration detection, no alert generation. These belong to Milestones 2 and 3.

**Allowed aggregation in Milestone 1:** accumulating `total_count`, `ontime_count` (at configured `T_SECONDS`), and `late_delay_reason_counts` is explicitly permitted — these are primitive deterministic aggregates needed to validate the data contract against calibration values.

---

## Patterns to Mirror

**Greenfield — no existing application code.** Every convention established here becomes the project baseline.

| Category | Source | Convention established |
|---|---|---|
| Naming | — (new) | `snake_case` modules; `PascalCase` dataclasses; `UPPER_SNAKE` constants |
| Error handling | — (new) | `DataLoadError` for I/O failures; `SchemaValidationError(DataLoadError)` for missing headers; individual row errors logged at WARNING, never raised |
| Logging | — (new) | `logging.getLogger(__name__)` per module; INFO for per-file load summary; WARNING for skipped rows with reason and row index |
| Data access | — (new) | `parse_stream(rows, period, T_seconds)` is pure stream consumer; `load_file(path, period, T_seconds)` owns file I/O and calls `parse_stream`; unit tests use the former only |
| Tests | — (new) | `pytest`; `io.StringIO` for unit test fixtures; `@pytest.mark.integration` for real-file tests; one test file per source module |

---

## Data Flow

```
CSV files (read-only, never modified)
    │
    └─► load_file(path, period, T_seconds)
            │
            ├─► validate_headers(reader.fieldnames)   # SchemaValidationError if missing
            │
            └─► parse_stream(rows, period, T_seconds)
                    │
                    For each row — exclusion order is deterministic:
                    │
                    ├─ 1. product_type == "SPOT_2.0"?  ──YES──► spot20_excluded++, skip
                    │
                    ├─ 2. parse_epoch(planned_end_epoch) is None?  ──YES──► null_epoch_excluded++, skip
                    │
                    ├─ 3. parse_epoch(actual_end_epoch) is None?   ──YES──► null_epoch_excluded++, skip
                    │
                    └─ 4. Eligible row → accumulate into VendorPeriodAgg
                               delta = actual_end_epoch - planned_end_epoch
                               total_count++
                               ontime_count++  if delta <= T_seconds
                               late_delay_reason_counts[delay_reason]++  if delta > T_seconds
                    │
                    Returns (vendor_stats, total_rows, spot20_excluded, null_epoch_excluded)
```

**Each row belongs to exactly one category:** SPOT_2.0 excluded, null-epoch excluded, or eligible. A SPOT_2.0 row with a malformed epoch is classified as SPOT_2.0 excluded only.

---

## Memory / Streaming Decision

**Selected: streaming aggregation (bounded intermediate aggregates).**

- 22 vendors × 3 months × 4 delay reasons = ~264 accumulator cells — negligible.
- No `Trip` objects are materialised. No pandas. No external dependencies.
- Trade-off: OTA is computed at a single T during the stream. Recomputing at a different T requires re-reading the files. Acceptable for a hackathon where T is fixed at demo time via config.
- The downstream product needs vendor-period aggregates and delay-reason counts — not arbitrary access to individual rows. Streaming provides exactly what is needed.

---

## Files to Create / Change

| File | Action | Why |
|---|---|---|
| `pyproject.toml` | CREATE | Package metadata, src layout discovery, Python version, pytest config (integration marker, testpaths), dev dependencies (`pytest`). Single dependency management path — no `requirements.txt`. |
| `src/moveinsync_ota/__init__.py` | CREATE | Package root |
| `src/moveinsync_ota/config.py` | CREATE | `T_SECONDS`, `DATA_DIR` (repo-relative default via `pathlib`; `MIS_DATA_DIR` env-var override), `MONTH_FILES`. No `VOL_MIN` or `DETERIORATION_THRESHOLD_PP` — both are comparison/detection policy belonging to Milestone 2. |
| `src/moveinsync_ota/exceptions.py` | CREATE | `DataLoadError`, `SchemaValidationError(DataLoadError)` — the complete exception hierarchy |
| `src/moveinsync_ota/data/__init__.py` | CREATE | Data sub-package |
| `src/moveinsync_ota/data/schema.py` | CREATE | `VendorPeriodAgg`, `PeriodLoadResult` dataclasses |
| `src/moveinsync_ota/data/normalise.py` | CREATE | Pure parsing functions — no I/O, no config import |
| `src/moveinsync_ota/data/loader.py` | CREATE | `validate_headers`, `parse_stream`, `load_file`, `load_all_files` |
| `tests/__init__.py` | CREATE | Test package |
| `tests/test_normalise.py` | CREATE | Unit tests for all normalise functions |
| `tests/test_loader.py` | CREATE | Unit tests using `io.StringIO` — no real file I/O |
| `tests/test_integration.py` | CREATE | Smoke test against real CSVs; `@pytest.mark.integration` |
| `.gitignore` | UPDATE | Add `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `*.egg-info/` |

**Not created in Milestone 1:** `src/moveinsync_ota/compute/` package, `volume.py`, `test_volume.py`. Volume filter is a comparison policy — it belongs to Milestone 2.

**Columns used at stream time:** `product_type` (exclusion), `planned_end_epoch` (parse), `actual_end_epoch` (parse), `vendor_id` (aggregation key), `delay_reason` (accumulate for late trips). No other columns. `is_driver_nc`, `is_cab_nc`, `planned_km`, `trip_id`, and all remaining columns are not read, parsed, or reconciled in this milestone.

---

## Tasks

### Task 1 — `pyproject.toml`
- **Action**: Create `pyproject.toml` at the repository root. Include:
  - `[build-system]` using `hatchling` or `setuptools` (whichever is available in the target environment).
  - `[project]` with `name = "moveinsync-ota"`, `requires-python = ">=3.11"`, no runtime dependencies.
  - `[project.optional-dependencies]` with `dev = ["pytest>=8"]`.
  - `[tool.setuptools.packages.find]` with `where = ["src"]` to enable src layout discovery.
  - `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `markers = ["integration: requires real CSV files at DATA_DIR (deselect with -m 'not integration')"]`.
- **Why**: Ensures `import moveinsync_ota` works reliably after `pip install -e ".[dev]"` without manually setting `PYTHONPATH`. Single source of truth for dev tooling.
- **Validate**: `pip install -e ".[dev]" && python -c "import moveinsync_ota"`

### Task 2 — Config module
- **Action**: Create `src/moveinsync_ota/config.py`. Define:
  - `T_SECONDS: int = 300` — OTA tolerance, seconds.
  - `DATA_DIR: Path` — resolved as: if `MIS_DATA_DIR` environment variable is set, use `Path(os.environ["MIS_DATA_DIR"])`; otherwise resolve relative to this file using `Path(__file__).resolve().parent.parent.parent / "input" / "dataset" / "raw" / "MoveInSynch Anonymized Trip Log Dataset"`. This makes the default portable: it works after cloning to any machine without editing source code.
  - `MONTH_FILES: dict[str, str]` — maps `"May"`, `"June"`, `"July"` to their exact filenames.
  - Do **not** define `VOL_MIN` — that is a comparison policy belonging to Milestone 2.
  - Do **not** define `DETERIORATION_THRESHOLD_PP` — that belongs to Milestone 2.
- **Validate**: `python -c "from moveinsync_ota.config import T_SECONDS, DATA_DIR; assert T_SECONDS == 300; print(DATA_DIR)"`

### Task 3 — Exception hierarchy
- **Action**: Create `src/moveinsync_ota/exceptions.py`. Define exactly two exceptions:
  - `class DataLoadError(Exception): pass` — raised when a file cannot be opened or read.
  - `class SchemaValidationError(DataLoadError): pass` — raised when required column headers are missing from the CSV.
  - No other exceptions in this file.
- **Validate**: `python -c "from moveinsync_ota.exceptions import DataLoadError, SchemaValidationError"`

### Task 4 — Schema dataclasses
- **Action**: Create `src/moveinsync_ota/data/schema.py`. Define:
  - `VendorPeriodAgg`: dataclass with `vendor_id: str`, `period: str`, `total_count: int = 0`, `ontime_count: int = 0`, `late_delay_reason_counts: Counter = field(default_factory=Counter)`. Accumulates OTA statistics for one vendor in one period. `late_delay_reason_counts` records delay_reason values only for OTA-late trips (delta > T).
  - `PeriodLoadResult`: dataclass with `period: str`, `total_rows: int`, `spot20_excluded: int`, `null_epoch_excluded: int`, `eligible_rows: int`, `vendor_stats: dict[str, VendorPeriodAgg]`.
  - Do **not** define a `Trip` dataclass — streaming aggregation requires no per-row objects.
- **Validate**: `python -c "from moveinsync_ota.data.schema import VendorPeriodAgg, PeriodLoadResult; print('ok')"`

### Task 5 — Normalisation functions
- **Action**: Create `src/moveinsync_ota/data/normalise.py`. Implement as pure functions with no imports from other project modules:
  - `parse_epoch(raw: str) -> int | None` — strip commas; case-fold and check against `{"", "na", "null", "none"}`; return `int(float(s))`; return `None` on any `ValueError`.
  - `parse_delay_reason(raw: str) -> str` — strip and upper; return `"UNKNOWN"` if the result is empty or in the NA-class set.
  - `guard_na(raw: str) -> str | None` — returns `None` for empty or NA-class strings (case-insensitive), else the stripped value.
  - No reconciliation functions for unused columns (`is_driver_nc`, `is_cab_nc`, `planned_km`).
- **Validate**: `python -m pytest tests/test_normalise.py -v`

### Task 6 — Header validation and `parse_stream`
- **Action**: Create `src/moveinsync_ota/data/loader.py`. Implement:
  - `REQUIRED_HEADERS: frozenset` — `{"product_type", "planned_end_epoch", "actual_end_epoch", "vendor_id", "delay_reason"}`.
  - `validate_headers(fieldnames: list[str]) -> None` — raises `SchemaValidationError` listing missing headers if any required header is absent. Extra columns and unknown-benign drift columns are silently ignored.
  - `parse_stream(rows: Iterable[dict], period: str, T_seconds: int) -> tuple[dict[str, VendorPeriodAgg], int, int, int]` returning `(vendor_stats, total_rows, spot20_excluded, null_epoch_excluded)`. Applies the exclusion order defined in the Data Flow diagram. Has no file I/O; receives already-opened row dicts. This is the sole unit under test for row-level logic.
- **Validate**: `python -m pytest tests/test_loader.py -v`

### Task 7 — `load_file` and `load_all_files`
- **Action**: In `loader.py`, implement:
  - `load_file(path: str | Path, period: str, T_seconds: int) -> PeriodLoadResult` — opens file with `encoding="utf-8"`, `newline=""`, raises `DataLoadError` on `OSError`. Creates `csv.DictReader`, calls `validate_headers`, passes `reader` to `parse_stream`. Builds and returns `PeriodLoadResult`. Logs INFO summary (period, total rows, excluded counts, eligible rows, elapsed time in seconds).
  - `load_all_files(data_dir: Path, month_files: dict[str, str], T_seconds: int) -> list[PeriodLoadResult]` — calls `load_file` for each entry in `month_files` order, returns list of results.
- **Validate**: Integration test (Task 8) covers real-file execution. Unit tests for the `DataLoadError` path use `pytest`'s `tmp_path` fixture to write a deliberately missing path.

### Task 8 — Unit tests

**`tests/test_normalise.py`** — cover:
- `parse_epoch`: comma-formatted string (`"1,777,598,280"` → `1777598280`), `"NA"` → `None`, `"na"` → `None`, `"NULL"` → `None`, `""` → `None`, float-string (`"1777598280.0"` → `1777598280`), plain int-string, `"None"` → `None`.
- `parse_delay_reason`: `"TRAFFIC"` → `"TRAFFIC"`, `""` → `"UNKNOWN"`, `"NA"` → `"UNKNOWN"`, `" nodelay "` → `"NODELAY"`.
- `guard_na`: non-empty string returns stripped value; `""` returns `None`; `"null"` returns `None`.

**`tests/test_loader.py`** — cover (all using `io.StringIO` fed into `csv.DictReader`, passed to `parse_stream` directly — no file I/O):
- SPOT_2.0 row is classified as `spot20_excluded`, not `null_epoch_excluded`, even when both epoch fields are empty.
- Row with null `planned_end_epoch` and valid `actual_end_epoch` → `null_epoch_excluded`.
- Row with valid `planned_end_epoch` and null `actual_end_epoch` → `null_epoch_excluded`.
- Clean row at `delta == T_seconds` → on-time (boundary inclusive).
- Clean row at `delta == T_seconds + 1` → late; its `delay_reason` appears in `late_delay_reason_counts`.
- `validate_headers` raises `SchemaValidationError` listing missing headers when a required column is absent.
- `validate_headers` passes when all required columns are present alongside extra unknown columns.

### Task 9 — Integration smoke test
- **Action**: Write `tests/test_integration.py`. Decorated `@pytest.mark.integration`. Auto-skip if `DATA_DIR` does not exist on disk (`pytest.skip` inside a session-scoped fixture or at module level). Call `load_all_files(DATA_DIR, MONTH_FILES, T_SECONDS)`. Report elapsed wall-clock time for the full load in the test output (INFO log or `print` — no pass/fail performance SLA). Assert:

  **Profile 1 — row counts (exact)**
  - May: `total_rows == 188_992`, `spot20_excluded == 648`, `null_epoch_excluded == 0`, `eligible_rows == 188_344`
  - June: `total_rows == 210_669`, `spot20_excluded == 702`, `null_epoch_excluded == 0`, `eligible_rows == 209_967`
  - July: `total_rows == 215_885`, `spot20_excluded == 973`, `null_epoch_excluded == 0`, `eligible_rows == 214_912`
  - Sum of `eligible_rows` across all three months: `613_223`

  **Per-vendor spot check — Meera Pavlov Travel, May** (calibration-derived, T=300s)
  - `may_result.vendor_stats["Meera Pavlov Travel"].total_count == 5_392`
  - `may_result.vendor_stats["Meera Pavlov Travel"].ontime_count == 4_119`

  **Do NOT assert:** volume eligibility, fleet OTA, or cohort comparisons — those belong to Milestone 2.

---

## Milestone Boundary

| Concern | Milestone |
|---|---|
| CSV ingestion, normalisation, exclusion | **1 — this plan** |
| Streaming aggregation into `VendorPeriodAgg` (`total_count`, `ontime_count`, `late_delay_reason_counts`) | **1 — this plan** |
| `T_SECONDS` config | **1 — this plan** |
| `DATA_DIR`, `MONTH_FILES` config | **1 — this plan** |
| `VOL_MIN` config | 2 |
| Volume filter / comparison-specific eligibility | 2 |
| `DETERIORATION_THRESHOLD_PP` config | 2 |
| Month-over-month comparison (prior vs current) | 2 |
| Fleet context computation | 2 |
| Deterioration detection and alert firing | 3 |
| LLM brief generation | 4 |
| Scheduled / replay execution | 5 |

---

## Mandatory Milestone 2 Requirements (carried forward from this plan)

The following must be implemented in Milestone 2 and must not be pre-empted here.

**Comparison-specific volume eligibility invariant:**
```
eligible(vendor, prior_period, current_period) =
    prior_period.total_count  >= VOL_MIN
    AND
    current_period.total_count >= VOL_MIN
```
- May → June eligibility depends only on May and June counts.
- June → July eligibility depends only on June and July counts.
- A vendor is eligible for May → June regardless of its July count.
- A vendor is eligible for June → July regardless of its May count.
- `apply_volume_filter` must be called once per comparison pair with only the two relevant `PeriodLoadResult` objects.

**Milestone 2 unit test scenarios (move to `test_volume.py` in Milestone 2):**
- **Scenario A:** vendor with May=600, June=700, July=400 — eligible for May→June (both ≥500), NOT eligible for June→July (400 < 500).
- **Scenario B:** vendor with May=300, June=600, July=700 — NOT eligible for May→June (300 < 500), eligible for June→July (both ≥500).

---

## Validation

```bash
# From a clean checkout — no PYTHONPATH manipulation needed
pip install -e ".[dev]"

# Unit tests only — no CSV files required
python -m pytest -v -m "not integration"

# Integration smoke — requires CSV files at DATA_DIR
# (auto-skips if DATA_DIR does not exist)
python -m pytest -v -m integration

# Expected integration output:
#   May  : total 188,992  SPOT_2.0: 648   null_epoch: 0   eligible: 188,344
#   June : total 210,669  SPOT_2.0: 702   null_epoch: 0   eligible: 209,967
#   July : total 215,885  SPOT_2.0: 973   null_epoch: 0   eligible: 214,912
#   Total eligible: 613,223
#   Meera Pavlov Travel / May: total_count 5,392 | ontime_count 4,119
#   Elapsed ingestion time: <reported, no pass/fail SLA>
```

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Exclusion order diverges from calibration, shifting counts | Medium | `parse_stream` applies SPOT_2.0 check before epoch checks — exactly matching calibration order; integration test pins exact counts |
| Required header missing in a future month's CSV | Low | `validate_headers` raises `SchemaValidationError` with a descriptive message at file open; not a silent wrong count |
| `delay_reason` NA-class strings mis-classified in late counts | Medium | `parse_delay_reason` normalises NA-class to `"UNKNOWN"`; unit test covers empty and `"NA"` inputs |
| `DATA_DIR` path resolution wrong on a fresh clone | Low | Repo-relative `pathlib` default; `MIS_DATA_DIR` env-var override; integration test auto-skips if path absent |
| Integration baseline numbers stale if calibration was wrong | Low | Calibration used identical exclusion logic; any count divergence > 0 surfaces a bug immediately |

---

## Acceptance

- [ ] `pip install -e ".[dev]" && python -m pytest -v -m "not integration"` — all unit tests pass
- [ ] `python -m pytest -v -m integration` — integration smoke passes with real CSV files
- [ ] Exact row counts and exclusion counts match Profile 1 calibration values
- [ ] Meera Pavlov Travel / May spot-check: `total_count == 5_392`, `ontime_count == 4_119`
- [ ] SPOT_2.0 row with empty epoch fields is counted as `spot20_excluded`, not `null_epoch_excluded`
- [ ] `validate_headers` raises `SchemaValidationError` for missing required headers
- [ ] No `Trip` dataclass; no per-row object materialisation; streaming only
- [ ] `parse_stream` has no file I/O; all unit tests use in-memory row iterables
- [ ] `DATA_DIR` default resolves via `pathlib` relative to `config.py`; no hardcoded absolute paths
- [ ] `pyproject.toml` is the single dependency management file; no `requirements.txt`
- [ ] `VOL_MIN` does not appear anywhere in Milestone 1 code
- [ ] `DETERIORATION_THRESHOLD_PP` does not appear anywhere in Milestone 1 code
- [ ] No `compute/` package; no `volume.py`; no `test_volume.py`
- [ ] `is_driver_nc`, `is_cab_nc`, `planned_km`, `trip_id` are not read, parsed, or reconciled in this milestone

---

*Next milestone after approval: Milestone 2 — OTA Computation & Context Engine.*
*Mandatory requirements carried forward: comparison-specific volume eligibility invariant (see above) and its two unit test scenarios.*
