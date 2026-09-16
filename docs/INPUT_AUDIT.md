# INPUT AUDIT — MoveInSync Agentic Intelligence & Reporting Layer

**Audit date:** 2026-09-16  
**Last updated:** 2026-09-16 (Pre-PRD validation pass)  
**Auditor:** pre-implementation review  
**Status:** COMPLETE — READY FOR PRD (see §20)

---

## 1. Input Inventory

### Problem Statement
| File | Size | Notes |
|---|---|---|
| `input/problem-statement/Moveinsync Problem statement with additional details.pdf` | 1.4 MB | 8 pages; text + slide images |

### References
| Directory | Contents |
|---|---|
| `input/references/` | **Empty — no reference files present** |

### Dictionaries
| File | Describes |
|---|---|
| `input/dataset/dictionary/Dictionary/README.md` | Dataset guide + entity-relationship overview |
| `input/dataset/dictionary/Dictionary/ride_data_trip.md` | Trip spine columns |
| `input/dataset/dictionary/Dictionary/emp_data.md` | Rider/employee columns |
| `input/dataset/dictionary/Dictionary/alerts_data.md` | Safety/compliance alert columns |
| `input/dataset/dictionary/Dictionary/bill_data.md` | Billing line item columns |
| `input/dataset/dictionary/Dictionary/trip_feedback.md` | Employee feedback rating columns |

### Datasets (Raw — immutable)
| File | Size | Rows (excl. header) | Grain |
|---|---|---|---|
| `Ride_data _trip-may_2026.csv` | 43.8 MB | 188,992 | one trip |
| `Ride_data _trip-June_2026.csv` | 49.1 MB | 210,669 | one trip |
| `Ride_data _trip-July_2026.csv` | 50.4 MB | 215,885 | one trip |
| `emp_Data.csv` | 272.8 MB | 1,637,906 | one employee leg |
| `bill_data.csv` | 82.5 MB | 620,942 (wc -l) / 620,782 (parsed) | one billed trip line |
| `trip_feedback.csv` | 48.7 MB | 512,873 | one employee rating |
| `alerts_data.csv` | 7.6 MB | 51,699 | one alert/event |
| **Total** | **~555 MB** | **~3,438,966 data rows** | |

> **Note on bill_data row count:** `wc -l` yields 620,942 rows; Python CSV parsing yields 620,782. The 160-row difference is likely due to embedded newlines in quoted fields. The parsed count is used for cardinality analysis.

---

## 2. Problem Definition

**Business problem (§3–4 of PS):** Large enterprises operate cab/shuttle fleets for hundreds to thousands of employees. Transport managers spend most of their time *assembling* data rather than *acting on it*. Metrics lack benchmarking context — a number is presented without historical trend, SLA target, or peer comparison. Signal is present; insight is absent; actions are manual.

**Users / actors (§3):**
1. **Transport manager (operational)** — day-to-day: vendor coordination, escalations, shift planning, delay management. Needs fast actionable signals.
2. **Transport & facilities head (strategic)** — budget, SLA accountability, vendor strategy, leadership reporting. Needs a coherent cost/safety/experience story automatically assembled.
3. **Team / line manager (shift-based ops)** — shift-level visibility into who arrived, who was late, how delays ripple into floor readiness.

**Observable pain (§4):** Metrics without context. Example given: "OTA is 78%" is meaningless without "it was 85% last month, SLA is 90%, and two vendors are responsible for the gap."

**Expected outcome (§4):** An agentic layer that senses what is happening, reasons about what it means (vs trend/SLA/benchmark/peer), and acts — surfacing what matters and communicating it to the right person at the right time.

---

## 3. Explicit Functional Requirements

All facts drawn from §8 (Requirements) of the problem statement.

| # | Requirement | Tier | Source |
|---|---|---|---|
| FR-1 | Working, demo-able prototype that runs on the provided dataset | **Mandatory** | §8 Mandatory |
| FR-2 | Agentic behaviour — senses, reasons, and acts; not a passive dashboard or query-only tool | **Mandatory** | §8 Mandatory |
| FR-3 | Serves at least one of the three named personas (transport manager / T&F head / team-line manager) | **Mandatory** | §8 Mandatory |
| FR-4 | Contextualises every metric against **at least one** reference point: historical trend, SLA/goal, industry benchmark, **or** peer comparison | **Mandatory** | §8 Mandatory |
| FR-5 | Combines two or more solution forms from §7 (conversational agent, proactive alerting, automated reporting, insight/anomaly detection, decision-support dashboard, automated communications) | Good-to-have | §8 Good-to-have |
| FR-6 | Handles messy or missing data gracefully (GPS gaps, unmatched records, incomplete rosters) | Good-to-have | §8 Good-to-have |
| FR-7 | Proactive triggers rather than purely on-demand responses | Good-to-have | §8 Good-to-have |
| FR-8 | Output a transport & facilities head could forward to leadership without rework | Bonus | §8 Bonus |
| FR-9 | Credible deployability story: multi-tenancy, latency, cost at enterprise volumes | Bonus | §8 Bonus |

> **SOURCE FACT — FR-4:** The mandatory requirement uses "or" — any single reference point satisfies it. Month-over-month historical trend from the supplied 3-month dataset is a valid and fully sufficient contextualisation. SLA thresholds and industry benchmarks are enhancements, not requirements.

---

## 4. Explicit Non-Functional Requirements

Only items supported by supplied material.

| # | Requirement | Source |
|---|---|---|
| NFR-1 | Must run on the anonymised sample dataset only — no live system access | §8 Constraints |
| NFR-2 | No production-grade authentication or security required | §8 Not expected |
| NFR-3 | No full historical data pipeline required | §8 Not expected |
| NFR-4 | No real vendor system integration required | §8 Not expected |
| NFR-5 | Preferred tech stack: Java, Angular, AWS — but not restrictive | §5 Tech Stack |
| NFR-6 | Inference cost per interaction and latency must be plausible at enterprise volumes (grading criterion) | §9 Criterion #2 |
| NFR-7 | Architecture must be deployable into an existing enterprise mobility platform (grading criterion) | §9 Criterion #3 |

---

## 5. Required Deliverables

From §10 of the problem statement:

1. Source code repository (GitHub/GitLab)
2. Architecture diagram
3. README + setup instructions
4. Sample inputs/outputs
5. Demo video (if requested)
6. Presentation deck
7. Live demo

---

## 6. Evaluation / Judging Criteria

| # | Criterion | Weight | What is Mandatory |
|---|---|---|---|
| 1 | Business impact & experience — reduces manager effort, surfaces missed decisions, persona-appropriate output, shareable without rework | **35** | Mandatory: clarity for intended persona |
| 2 | Agentic design & cost at scale — AI solving genuine problems, not decoration; plausible inference cost per interaction; latency feasibility | **20** | Mandatory: real agentic behaviour, not a wrapper |
| 3 | Architecture & code quality — sound structure, deployable into existing platform, choices a team can build on | **20** | Inferred best practice (no specific code standard stated) |
| 4 | Functionality — it runs; a working, demo-able prototype end-to-end on the provided dataset | **25** | Mandatory |

**Key grading signal (§8 page 8):** judges assess: (1) whether it works, (2) whether it actually lands for the persona, (3) whether it can actually run at enterprise scale.

---

## 7. Dataset Understanding

### 7.1 `ride_data_trip` (3 monthly CSVs)

| Attribute | Detail |
|---|---|
| **Purpose** | Trip spine — timing, distances, vendor, compliance flags, headcount per trip |
| **Grain** | One row = one cab/bus/shuttle trip |
| **Total rows** | 615,546 (May: 188,992 / June: 210,669 / July: 215,885) |
| **Candidate identifiers** | `trip_id` (unique per file; comma-formatted string) |
| **Timestamps** | `trip_date` (free-text "Month D, YYYY"); `planned_start_epoch`, `planned_end_epoch`, `actual_start_epoch`, `actual_end_epoch` (comma-formatted Unix epoch strings) |
| **Date coverage** | May 1 – July 31, 2026 (3 months) |
| **Key measures** | `planned_km`, `traveled_km`, `delay_minutes` (comma-string), `plannedemployee_cnt`, `actualemployee_cnt`, `noshow_cnt` |
| **Key dimensions** | `business_unit` (5 values), `office` (17 values), `product_type` (CAB/BUS/SPOT_2.0), `trip_direction` (LOGIN/LOGOUT), `vendor_id` (23 vendors), `actual_cab_fuel_type` (Diesel/Electric/Petrol), `delay_reason` (NODELAY/TRAFFIC/DRIVER/EMPLOYEE) |
| **Relationship candidates** | Hub for all other tables via `trip_id` |
| **Dictionary evidence** | Confirmed by README.md and ride_data_trip.md |

**Product-type distribution (May full scan):** CAB 83.5% (157,859), BUS 16.1% (30,485), SPOT_2.0 0.3% (648).

### 7.2 `emp_data`

| Attribute | Detail |
|---|---|
| **Purpose** | Rider-level view — per-employee-per-trip pickup/drop times, distances, no-show status |
| **Grain** | One row = one employee's leg of one trip (many rows per `trip_id`) |
| **Total rows** | 1,637,906 |
| **Candidate identifiers** | `trip_id` (int64, clean), `stwid` (int64; 0 = placeholder, not a real employee) |
| **Timestamps** | `planned_pickup_epoch`, `planned_drop_epoch`, `actual_pickup_epoch`, `actual_drop_epoch` (float64); `trip_date` ISO `YYYY-MM-DD` |
| **Date coverage** | May – July 2026 (92 distinct dates) |
| **Key measures** | `planned_km`, `traveled_km` (negatives possible), boarding rate via `boarding_status` / `is_no_show` |
| **Key dimensions** | `business_unit`, `office` (19 values), `product_type`, `shift_type`, `signintype` (Planned/Adhoc/Guest), `gender`, `emp_role` (16 values) |
| **Relationship candidates** | Joins to ride_data_trip on `trip_id`; joins to alerts_data and trip_feedback on `stwid` |
| **Dictionary evidence** | emp_data.md — clean int64 join keys; other files have comma-formatted strings |
| **Uncertainties** | `stwid=0` is a placeholder and must be excluded from per-rider analysis. Negative km values present. |

### 7.3 `alerts_data`

| Attribute | Detail |
|---|---|
| **Purpose** | Safety and compliance events per trip |
| **Grain** | One row = one alert/event raised during a trip |
| **Total rows** | 51,699 |
| **Candidate identifiers** | `event_id` (UUID, unique); `trip_id` (comma-string, 33,474 unique values); `stwid` (comma-string, "0" for trip-level) |
| **Timestamps** | `start_time`, `acknowledge_time` (free-text "Month D, YYYY, H:MM AM/PM") |
| **Date coverage** | May – July 2026 (aligned with ride data) |
| **Key measures** | Alert volume by type, severity, acknowledgement latency |
| **Key dimensions** | `event_type` (11 values), `severity` (Sev-1/2/3 + bad values), `state_text` (CLOSED/OPEN/NEW), `source` |
| **Relationship candidates** | Joins to ride_data_trip on `trip_id`; joins to emp_data on `stwid` (after filtering stwid=0) |
| **Dictionary evidence** | alerts_data.md |
| **Uncertainties** | Does not have an `office` column — can only get office context by joining to ride_data_trip |

### 7.4 `bill_data`

| Attribute | Detail |
|---|---|
| **Purpose** | Billing line items — cost, billed distance, vendor, contract, slab tier |
| **Grain** | One row = one billed trip line item |
| **Total rows** | 620,782 (parsed); 620,942 (wc -l) |
| **Candidate identifiers** | `trip_id` (plain numeric string, no commas — different from all other files) |
| **Timestamps** | `cycle_start`, `cycle_end` (free-text datetime strings, 6 semi-monthly cycles: May 1–15, May 16–31, June 1–15, June 16–30, July 1–15, July 16–31) |
| **Date coverage** | May 1 – July 31, 2026 (6 billing cycles) |
| **Key measures** | `trip_cost` (comma-formatted string), `total_trip_km` (float; 40.0% of rows = 0.0) |
| **Key dimensions** | `business_unit`, `office`, `vendor` (24 names), `contract` (47 values, 11 nulls), `slab_name` (28 values + string nulls) |
| **Relationship candidates** | Joins to ride_data_trip on `trip_id` (requires normalisation — no commas in bill_data vs comma-string elsewhere) |
| **Dictionary evidence** | bill_data.md |

### 7.5 `trip_feedback`

| Attribute | Detail |
|---|---|
| **Purpose** | Employee satisfaction ratings per trip leg |
| **Grain** | One row = one employee's feedback for one trip leg |
| **Total rows** | 512,873 |
| **Candidate identifiers** | `trip_id` (comma-string), `stwid` (comma-string) |
| **Timestamps** | `trip_date` (free-text with time "Month D, YYYY, H:MM AM/PM"), `creation_time` (same format) |
| **Date coverage** | June–July 2026 (feedback data appears to start in June based on sample) |
| **Key measures** | `route_rating`, `driver_rating`, `cab_rating`, `safety_rating`, `marshal_rating` (each 0–5) |
| **Key dimensions** | `business_unit`, `trip_type` (LOGIN/LOGOUT) |
| **Relationship candidates** | Joins to ride_data_trip on `trip_id`; joins to emp_data on `stwid` |
| **Dictionary evidence** | trip_feedback.md |
| **Uncertainties** | See §8.9 for data-validated rating zero-rate profile. Does NOT have `office` or `vendor_id` column — only accessible via join. |

---

## 8. Dataset Quality Observations

### 8.1 "NA" and "null" String Literals Used as Null Placeholders (Cross-file)

**Finding:** Multiple columns across multiple files use the string `"NA"` or `"null"` as placeholders rather than empty/null values. The dictionaries describe these as "nulls" — the actual storage format is different.

| File | Column | Dictionary says | Actual value |
|---|---|---|---|
| `ride_data_trip` | `trip_nodal` | `NODAL`, `HOME`, `SHUTTLE`; nulls for non-nodal | `"NA"` string (not empty) for non-nodal |
| `alerts_data` | `source` | 39,350 nulls | `"NA"` string (39,350 rows) |
| `alerts_data` | `severity` | Sev-1/2/3 + nulls + one `"False"` | `"NA"` string present in addition to `"False"` |
| `bill_data` | `slab_name` | ~124,912 nulls | `"null"` string (121,111) + `"NA"` string (3,801) |

**Impact:** Any null-check that tests for empty/None will miss these values. All pipelines must normalise `"NA"` and `"null"` strings to proper null before analysis.

### 8.2 `trip_id` Format Inconsistency (Cross-file, documented but critical)

| File | trip_id format | Example |
|---|---|---|
| `ride_data_trip` | Comma-string (`object`) | `"1,097,076"` |
| `alerts_data` | Comma-string (`object`) | `"1,097,076"` |
| `trip_feedback` | Comma-string (`object`) | `"1,258,207"` |
| `emp_data` | Clean `int64` | `1530200` |
| `bill_data` | Plain numeric string (no commas) | `"1123974"` |

Every join across these tables requires normalisation: strip commas, cast to int64.

### 8.3 Epoch Column Format Inconsistency (documented)

| File | Epoch format |
|---|---|
| `ride_data_trip` | Comma-formatted strings (`"1,777,595,400"`) |
| `emp_data` | Float64 (`1783633500.0`) |

### 8.4 Date Format Inconsistency (documented)

| File | trip_date format |
|---|---|
| `emp_data` | ISO `"2026-07-09"` |
| `ride_data_trip` | Free-text `"May 1, 2026"` |
| `trip_feedback` | Free-text with time `"June 3, 2026, 11:00 AM"` |
| `alerts_data` | Free-text with time `"May 1, 2026, 12:03 AM"` |
| `bill_data` | Free-text with time (cycle columns) |

### 8.5 `ride_data_trip` Schema Drift Across Months

| Column | May | June / July |
|---|---|---|
| `is_driver_nc` | `object` with nulls | `bool` |
| `is_cab_nc` | `object` with nulls | `bool` |
| `planned_km` | `float64` | `object` in July (comma-formatted value sneaks in) |

### 8.6 Negative Distances in `emp_data`

`planned_km` ranges to -2.0 and `traveled_km` to -6.63. Physically impossible. Confirmed in sampled 100k rows (2 negative `traveled_km`). Must be dropped or flagged before any distance analysis.

### 8.7 `alerts_data` Severity Bad Values

Confirmed `"False"` (visible in row 2 of raw file) and `"NA"` both present. Dictionary only warned about `"False"`. Pipeline must treat `"False"`, `"NA"`, and empty as invalid severity.

### 8.8 `bill_data` 40% Zero-km Rows

248,191 of 620,782 parsed rows (40.0%) have `total_trip_km = 0.0`. Dictionary says "0.0 appears for a meaningful share of rows" without quantifying. 40% is a very significant share — consistent with flat-rate billing slabs (km-independent). This makes per-km cost analysis inapplicable for these rows; they should be treated as a separate billing category, not as missing data.

### 8.9 `trip_feedback` Rating Zero-Rate Profile (DATA-VALIDATED, full file)

Full scan of all 512,873 feedback rows:

| Dimension | Zero count | Total | Zero rate |
|---|---|---|---|
| `route_rating` | 2 | 512,873 | 0.0% |
| `driver_rating` | 2 | 512,873 | 0.0% |
| `cab_rating` | 2 | 512,873 | 0.0% |
| `safety_rating` | 2 | 512,873 | 0.0% |
| `marshal_rating` | **473,692** | 512,873 | **92.4%** |

**DATA-VALIDATED FACT:** `marshal_rating` zero behaviour is structurally different from all other rating dimensions. Route, driver, cab, and safety ratings have de-minimis zero rates (2 rows each); marshal_rating has a 92.4% zero rate.

**ASSUMPTION / DEFERRED QUESTION:** The most plausible business interpretation is that `marshal_rating=0` means "not applicable — no marshal was present on this trip." However, the supplied dataset and dictionary do not prove this semantic meaning. Zero-exclusion for `marshal_rating` is a provisional downstream product rule pending semantic confirmation. Since `trip_feedback` is not required for the OTA Watchdog MVP, this does not block PRD.

### 8.10 `bill_data` Trip Cardinality (DATA-VALIDATED)

Full cardinality analysis of `bill_data.trip_id` vs `ride_data_trip.trip_id`:

| Metric | Value |
|---|---|
| bill_data total rows (parsed) | 620,782 |
| bill_data distinct trip_id | 613,783 |
| trip_ids with exactly 1 billing row | 606,784 (98.9%) |
| trip_ids with exactly 2 billing rows | 6,999 (1.1%) |
| Maximum billing rows per trip_id | **2** |
| ride_data_trip distinct trip_ids | 608,793 |
| bill trip_ids matching ride_data_trip | 608,047 / 613,783 = **99.1%** |
| ride trip_ids with bill records | 608,047 / 608,793 = **99.9%** |

**DATA-VALIDATED FACT:** 1.1% of bill trip_ids (6,999 trips) have exactly 2 billing rows; 98.9% have exactly 1. Maximum rows per trip_id is 2. The 5,736 bill trip_ids not matching any ride trip_id (0.9%) and the 746 ride trips without billing records are a minor data coverage gap.

**DEFERRED QUESTION:** What do the two billing rows for the same trip represent? Possible interpretations include: two billing slabs applied to the same trip, a correction/restatement row, or two legs billed separately. The correct business aggregation rule (sum, take the latest, or take a specific row type) cannot be determined from the data alone. Since `bill_data` is not required for the OTA Watchdog MVP, this does not block PRD.

### 8.11 Extreme `delay_minutes` Values (DATA-VALIDATED — cause unproven)

Full scan of all 615,546 trip rows:

| Threshold | Count | % of total |
|---|---|---|
| > 60 min | 1,044 | 0.17% |
| > 120 min | 559 | 0.09% |
| > 240 min | 444 | 0.07% |
| > 480 min | 279 | 0.05% |
| > 1,440 min (1 day) | 20 | 0.003% |

**Key finding: All top-20 extreme values (>1,898 min) are `SPOT_2.0` product type.** Top vendors: Pooja Mikhailov Travel (148 rows >480), Pooja Sokolov Travel (97 rows), Vikram Mikhailov Travel (27 rows). Spread across all three months (May: 87, June: 90, July: 102 rows >480). Delay reasons for >480 min rows: TRAFFIC (185), DRIVER (85), EMPLOYEE (9) — all legitimate reason codes.

**Interpretation:** Extreme values are strongly correlated with `SPOT_2.0` product type. The cause is unproven — possibilities include: SPOT_2.0 operates on fundamentally different time scales than regular CAB trips (e.g., all-day bookings), or there is a systematic calculation issue specific to that product type. **Do not label as epoch errors.** Treat as a product-type-specific data-quality observation; handle by excluding SPOT_2.0 from OTA calculations until semantics are clarified, or by computing OTA separately per product_type.

### 8.12 `stwid=0` Placeholder Rows

Across `emp_data`, `alerts_data`, and `trip_feedback`, `stwid=0` represents trip-level or system records not tied to a real rider. Must be excluded from all per-employee analytics.

### 8.13 `trip_feedback` — No `office` or `vendor_id` Column

`trip_feedback` lacks both `office` and `vendor_id`. These attributes are only reachable by joining through `ride_data_trip`. Any vendor or office-level experience analysis requires that join.

### 8.14 `alerts_data` — No `office` Column

Same issue as 8.13. Office-level safety analysis requires joining `alerts_data` to `ride_data_trip`.

---

## 9. Dataset Relationships

### Confirmed

| Relationship | Evidence |
|---|---|
| `ride_data_trip.trip_id` → `emp_data.trip_id` | Dictionary README explicitly documents this. `trip_id` unique in ride_data_trip; many-per-trip in emp_data. |
| `ride_data_trip.trip_id` → `alerts_data.trip_id` | Dictionary README. 33,474 unique trip_ids in alerts_data; subset of ride_data_trip. |
| `ride_data_trip.trip_id` → `trip_feedback.trip_id` | Dictionary README. 298,321 unique trip_ids in feedback; subset of ride_data_trip. |
| `ride_data_trip.trip_id` → `bill_data.trip_id` | Dictionary README. Cross-match validated: 99.1% of bill trip_ids match ride trip_ids; 99.9% of ride trip_ids have bill records. Requires normalisation (no commas in bill_data). |
| `bill_data.vendor` → `ride_data_trip.vendor_id` | DATA-VALIDATED: 23/23 ride_data_trip vendor_id values appear verbatim in bill_data.vendor. One additional bill-only vendor (`'Neha Mikhailov Travel'`) has no trips in the ride data window. Column names differ but values are the same entity. |

### Strongly Supported

| Relationship | Evidence |
|---|---|
| `emp_data.stwid` → `alerts_data.stwid` | Dictionary README states `stwid` links riders across legs, alerts, ratings. Shared value space confirmed by inspection. |
| `emp_data.stwid` → `trip_feedback.stwid` | Same dictionary evidence. trip_feedback.stwid contains 13,258 unique values. |

### Possible but Unverified

| Relationship | Notes |
|---|---|
| `alerts_data.stwid` → `trip_feedback.stwid` | Transitive through emp_data. No dictionary evidence of direct usage. |

---

## 10. Problem-Statement Ambiguities

| # | Ambiguity |
|---|---|
| AMB-1 | **SLA values not provided — but not required for FR-4.** The PS example uses SLA for illustration, but the mandatory requirement (FR-4) accepts *any* reference point including historical trend. Month-over-month trend from the 3-month dataset satisfies FR-4 without SLA values. Configurable SLA thresholds are an optional enhancement. |
| AMB-2 | **"Industry benchmark" and "peer comparison" undefined.** FR-4 accepts these as reference points but they are not required. Not a blocker. |
| AMB-3 | **"Proactive triggers" mechanism unspecified.** Good-to-have FR-7 says proactive rather than on-demand, but no target latency, trigger condition, or notification channel is defined. |
| AMB-4 | **"Agentic behaviour" definition boundary.** FR-2 says "not a passive dashboard or query-only tool." Whether a scheduled automated report counts, or whether the agent must initiate actions without prompting, is not defined. |
| AMB-5 | **Partially resolved by data.** Only `marshal_rating` has a structurally anomalous zero rate (92.4%); route, driver, cab, and safety ratings have de-minimis zeros (0.0%). The business meaning of `marshal_rating=0` is not proven by the data alone. Deferred; not a PRD blocker since trip_feedback is not needed for OTA Watchdog MVP. |
| AMB-6 | **Partially resolved by data.** 98.9% of trips have 1 billing row; 1.1% have exactly 2; maximum is 2. What the two rows represent and the correct aggregation rule (sum, latest, or other) is unproven. Deferred; not a PRD blocker since bill_data is not needed for OTA Watchdog MVP. |
| AMB-7 | **trip_nodal "NA" semantic.** Dictionary says null = non-nodal trip. Actual data uses string "NA." Whether "NA" is identical to null or carries a distinct meaning is unconfirmed, but the practical treatment (normalise "NA" → null for non-nodal analysis) is clear. |
| AMB-8 | **SPOT_2.0 product type semantics.** Not explained in dictionary or PS. Responsible for all extreme delay_minutes values. OTA calculation for this product type cannot proceed until semantics are known. |
| AMB-9 | **Which persona is primary?** FR-3 says "at least one of the three named personas." The primary persona for MVP scope is not mandated. |
| AMB-10 | **Demo format.** "Demo video if requested" — unclear whether a live interactive demo or recorded walkthrough is preferred for full credit. |

---

## 11. Architecture-Impacting Assumptions

Listed as **assumptions**, not decisions.

| # | Assumption | Basis | Status |
|---|---|---|---|
| A-1 | `trip_id` can be normalised to int64 as the universal join key across all five tables | Confirmed by dictionary and data inspection | Validated |
| A-2 | "NA" and "null" string values are semantically equivalent to null and must be normalised at ingestion | Observed in data; dictionary inconsistency confirmed | Validated |
| A-3 | 1.1% of bill trip_ids have exactly 2 billing rows (max=2); what the two rows represent and the correct aggregation rule is a deferred question | DATA-VALIDATED cardinality; aggregation rule is unproven | Open |
| A-4 | `stwid=0` rows must be excluded from all per-employee/per-rider analytics | Documented in dictionary | Validated |
| A-5 | `marshal_rating=0` exhibits structurally different zero behaviour (92.4%) from all other rating dimensions (0.0%). The business meaning of zero is unproven. Provisional treatment: exclude zeros from marshal_rating averages pending semantic confirmation. | DATA-VALIDATED structural difference; semantic meaning is an assumption | Open |
| A-6 | Extreme `delay_minutes` values (>480 min, 279 rows) are anomalous; their cause is unproven but strongly correlated with `SPOT_2.0` product type; should be excluded from OTA calculations or treated separately per product_type | DATA-VALIDATED distribution; cause is a deferred question | Open |
| A-7 | Month-over-month historical trend (May vs June vs July) is the primary contextualisation mechanism and is sufficient to satisfy mandatory FR-4 | SOURCE FACT: FR-4 uses "or"; historical trend is one of the accepted reference points | Validated |
| A-8 | The data layer must be treated as a read-only snapshot; "proactive" triggers are simulated by scheduled batch runs over static data | Confirmed by §8 Constraints: sample dataset only, no live access | Validated |
| A-9 | `bill_data.total_trip_km = 0.0` rows (40%) represent flat-rate billing slabs, not missing data | Inferred from slab-based billing model; unverified | Open |
| A-10 | `business_unit` is a natural data partitioning dimension for multi-tenant scenarios | `business_unit` present in all five tables with same 5 values | Potential strategy, not a requirement |

---

## 12. Questions and Decisions

Questions are classified as: **Closed** (data-validated or source-resolved), **Product decision during PRD** (not a prerequisite to starting PRD), or **Deferred safely** (can be handled with a documented scoping decision).

None of the remaining open questions block entering PRD.

### Closed

| # | Question | How closed |
|---|---|---|
| Q-1 | What SLA thresholds should be used? | Historical trend satisfies mandatory FR-4 without SLA values. SLA is an optional enhancement. |
| Q-2 | Is `bill_data` 1:1 with trips? | DATA-VALIDATED: 98.9% one row, 1.1% two rows, max=2. Aggregation rule is a deferred product decision; cardinality is known. |
| Q-7 | Are zero-ratings in non-marshal dimensions valid low scores? | DATA-VALIDATED: 0.0% zero rate for route/driver/cab/safety. Question is closed. |
| Q-9 | Are hardcoded SLA/benchmark values acceptable? | Historical trend is the primary reference. Closed as non-issue. |
| Q-10 | Is `bill_data.vendor` the same entity as `ride_data_trip.vendor_id`? | DATA-VALIDATED: 23/23 exact string match. Same entity. |

### Product Decisions — Resolve During /plan-prd

| # | Decision | Leading candidate |
|---|---|---|
| Q-3 | What "agentic" form is the primary implementation? (scheduled alert generator / reactive trigger / conversational NL agent) | Scheduled OTA alert generator |
| Q-5 | Which persona is primary for MVP scope? | Transport Manager |
| Q-OTA | What is the OTA formula? What columns define "on-time" and what tolerance applies? | See §12a below — **no authoritative definition exists in supplied materials** |
| Q-THRESH | What deterioration threshold triggers an alert? (e.g., OTA drops > 5 percentage points) | Configurable; reasonable default needed |

### Deferred Safely

| # | Question | Deferral rationale |
|---|---|---|
| Q-4 | Are `delay_minutes` > 480 for SPOT_2.0 genuine delays or a product-type artefact? | Exclude SPOT_2.0 from MVP OTA with documentation. |
| Q-6 | Is string "NA" in `trip_nodal` identical to null (non-nodal), or distinct? | Practical treatment is the same for OTA/CAB analysis. |
| Q-8 | What is SPOT_2.0? All-day booking, on-demand, or other? | Scope it out of MVP OTA; revisit if SPOT_2.0 coverage is added later. |
| Q-MARSHAL | What does `marshal_rating=0` mean? | Not needed for OTA Watchdog MVP. |
| Q-BILL-AGG | What do two billing rows for the same trip represent, and what is the correct aggregation rule? | Not needed for OTA Watchdog MVP. |

---

## 12a. OTA Definition — No Authoritative Formula in Supplied Materials

**Search result:** The problem statement and all six dictionary files were searched for an explicit OTA definition, on-time criteria, tolerance, or formula. None was found.

**What the supplied materials do establish (SOURCE FACTS):**

- `delay_minutes` (ride_data_trip): "Delay duration in minutes." Values range from `"0"` to `"10,644"`. The dictionary does not state how this is calculated or which epoch columns it derives from.
- `planned_start_epoch` / `actual_start_epoch` (ride_data_trip): Planned and actual trip start times in Unix epoch seconds. Both present.
- `planned_end_epoch` / `actual_end_epoch` (ride_data_trip): Planned and actual trip end times in Unix epoch seconds. Both present.
- The ride_data_trip dictionary lists "on-time arrival (OTA) vs an SLA target" as an **idea to explore** — not a defined metric.
- The problem statement uses "OTA is 78%" as an illustrative example with no formula.

**PRODUCT DEFINITION REQUIRED IN PRD**

The OTA formula must be defined during /plan-prd. It is a core product definition because the MVP OTA Watchdog depends on it. Defensible candidates:

| Candidate | Formula | Columns used | Notes |
|---|---|---|---|
| **A** | `delay_minutes == 0` → on-time | `delay_minutes` | Simplest; uses the pre-computed field; definition of what "0" means is still assumed |
| **B** | `delay_minutes <= T` for configurable tolerance T | `delay_minutes` | Allows a tolerance window (e.g., ≤5 min); most flexible |
| **C** | `actual_start_epoch <= planned_start_epoch + T` | `actual_start_epoch`, `planned_start_epoch` | Measures start-time punctuality; independent of the pre-computed field |
| **D** | `actual_end_epoch <= planned_end_epoch + T` | `actual_end_epoch`, `planned_end_epoch` | Measures arrival punctuality; most directly maps to "on-time arrival" |

Candidates A and B are simpler and depend on the pre-computed `delay_minutes` field. Candidates C and D use raw epoch columns and are independent of whatever calculation produced `delay_minutes`. The choice affects how SPOT_2.0 extreme values propagate into OTA.

**The OTA formula choice does not block entering PRD — but it must be the first product decision made within the PRD.**

---

## 13. MVP Boundary

### Revised MVP — OTA Watchdog (Transport Manager)

Mandatory requirements do not require using all five datasets. The smallest dataset subset for a complete, high-value agentic experience is evaluated here.

**Primary dataset: `ride_data_trip` (3 monthly CSVs) only.**

This single table contains everything needed for the core agentic loop:

| Loop stage | Signal available in `ride_data_trip` alone |
|---|---|
| **Sense** | OTA per vendor: compute from `delay_minutes`, `planned_start_epoch`, `actual_start_epoch`, per `vendor_id`, per month |
| **Reason** | Compare current period (July) to prior period (May/June); identify material OTA deterioration; attribute to `delay_reason` (TRAFFIC / DRIVER / EMPLOYEE) breakdown per vendor |
| **Act** | Autonomously generate a Transport Manager alert brief when OTA for any vendor drops >X% month-over-month, naming the vendor, the magnitude, the dominant delay reason, and the trend |

The alert output must include **evidence** (vendor name, OTA %, prior period comparison, dominant delay reason and its share) — not just an LLM-written conclusion.

**Minimum dataset subset for MVP OTA Watchdog:**
- `ride_data_trip` (May + June + July) — **required**
- All other tables (`emp_data`, `bill_data`, `trip_feedback`, `alerts_data`) — **optional enhancements** that deepen the watchdog (e.g., add employee no-show context, cost correlation, experience signal)

**Excludes SPOT_2.0 from OTA calculation** until semantics are confirmed (0.3% of trips; negligible impact on overall OTA).

**Contextualisation (FR-4):** Month-over-month comparison of vendor OTA across the 3-month window. Satisfies mandatory FR-4 without any SLA configuration.

**Agentic behaviour (FR-2):** Agent runs automatically, detects deterioration against a threshold, and produces a structured brief. It acts without being asked.

**Persona (FR-3):** Transport Manager — receives an operational brief they can act on immediately.

**Working prototype (FR-1):** Runs on the provided dataset end-to-end.

---

## 14. Explicit Non-Goals

From §8 "Not expected":
- Production-grade authentication or security
- A full historical data pipeline (beyond the 3-month snapshot)
- Integration with real vendor systems

Additional non-goals from problem statement constraints:
- Real-time data ingestion from live systems
- Actual multi-tenant isolation (demo simulation only)
- Full coverage of all three personas before demo
- GPS route visualisation (no GPS trace data in the supplied dataset — only trip distances)
- Industry benchmark data (not supplied; month-over-month trend is the baseline)

---

## 15. Technical Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| T-1 | 5-table join on `trip_id` with format normalisation is non-trivial; incorrect normalisation will silently produce wrong join counts | High | Validate join cardinality counts before any analysis step |
| T-2 | `emp_data` (272 MB, 1.6M rows) is the largest file; in-memory joins on full dataset may be slow or exceed RAM | Medium | Profile join before choosing runtime; aggregate before joining where possible. MVP OTA Watchdog does not require emp_data. |
| T-3 | LLM-based natural language interface will have high inference cost per query at enterprise scale — grading criterion #2 explicitly checks this | High | Design LLM prompts to operate on pre-aggregated summaries, not raw data; add caching |
| T-4 | "Agentic" behaviour definition is ambiguous; overbuilding an autonomous agent loop risks breaking the prototype within the hackathon timeline | Medium | Build the simplest thing that demonstrably senses–reasons–acts; validate with demo script |
| T-5 | Schema drift across months in `ride_data_trip` (is_driver_nc bool/object, planned_km float/object) will cause concat failures | Medium | Explicit dtype reconciliation before concat |

---

## 16. Data Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| D-1 | 40% of bill_data rows have total_trip_km=0; cost-per-km analysis distorted or impossible for these rows | High | Separate zero-km (flat-rate) from distance-based billing; label explicitly. Not needed for MVP OTA Watchdog. |
| D-2 | "NA"/"null" string literals are undocumented null placeholders; missing them corrupts categorical analyses | High | Normalise at ingestion; add assertion tests on known-bad values |
| D-3 | Extreme delay_minutes values for SPOT_2.0 product type (>1,898 min in all top-20 cases) will skew OTA calculations if included | Medium | Exclude SPOT_2.0 from OTA calculations or compute separately per product_type; document the exclusion |
| D-4 | marshal_rating=0 (92.4% of feedback rows) will corrupt experience scores if treated as a valid rating | High | DATA-VALIDATED structural anomaly; provisional rule is to exclude zeros from marshal_rating. Business meaning is unproven. Not needed for OTA Watchdog MVP. |
| D-5 | bill_data trip_id has no commas while all other files do; silent join failure (zero rows) if not caught | Medium | Unit-test the normalisation step with known trip_ids |
| D-6 | stwid=0 placeholder rows will corrupt per-employee analyses if not excluded | Medium | Filter as the first step in any per-rider aggregation |
| D-7 | ~~No industry benchmark or peer comparison data~~ | Closed | Historical trend satisfies FR-4; this is no longer a risk to mandatory requirements |

---

## 17. Product / Demo Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| P-1 | Judges expect "agentic" — a chat UI or report without autonomous behaviour will not score well on criterion #2 | High | Demo must show agent initiating an action (alert, report draft) without user prompting |
| P-2 | "It actually lands" — output must be persona-relevant and readable by a non-technical transport manager | High | Test output language against a non-technical reader; strip internal jargon |
| P-3 | "Enterprise scale" story — must explain how the solution handles 10× data volume, not just claim it | Medium | Include explicit cost/latency estimates in the architecture section of the deck |
| P-4 | trip_feedback data covers only 512k rows vs 1.6M emp_data rows — CSAT stats will be based on a partial sample | Low | State explicitly in demo; not a correctness risk if handled properly |

---

## 18. Architecture-Driving Requirements

These requirements have the most direct impact on system design choices (technology-neutral):

1. **Agentic pattern required (FR-2):** The system must execute a sense → reason → act loop, not passively serve queries. This demands a control-flow mechanism beyond a pure REST API: a scheduler, event trigger, or agent loop.

2. **Contextualised metrics (FR-4):** Every metric output must carry a reference value. The supplied 3-month window enables month-over-month trend as the primary reference point. SLA thresholds are optional configuration. This demands a metric layer that persists or can recompute prior-period values.

3. **Multi-persona output (FR-3 + grading criterion #1):** Different personas need different output formats and detail levels. The system needs a presentation layer aware of the target persona.

4. **Messy data handling (FR-6):** The dataset is intentionally messy. The system must handle string nulls, format heterogeneity, and extreme values at ingestion — this is explicitly rewarded in grading.

5. **Demo-ability on static data (FR-1 + constraint):** All "live" and "proactive" behaviour must be simulated from the static 3-month snapshot. The architecture must support replaying the data as-if-live for the demo.

6. **Inference cost awareness (NFR-6):** Any LLM usage must target pre-aggregated, structured inputs — not raw row-level data — to keep inference cost per interaction plausible at enterprise scale.

7. **`business_unit` as a potential partitioning dimension (Bonus FR-9):** All five tables share the same 5 `business_unit` values. Scoping queries/outputs by `business_unit` is a natural multi-tenancy strategy if enterprise deployment is demonstrated. This is a potential architecture choice, not a mandatory requirement.

---

## 19. Candidate Vertical Slices (Conceptual Only)

No implementation design; these are product-level problem decompositions only.

| Slice | Persona | Core signal | Value | Datasets needed |
|---|---|---|---|---|
| **OTA Watchdog** *(leading MVP candidate)* | Transport Manager | delay_minutes, delay_reason, vendor_id | Automated alert when a vendor's OTA deteriorates materially month-over-month, with root-cause breakdown | `ride_data_trip` only |
| **Daily Shift Readiness Brief** | Team / Line Manager | is_no_show, boarding_status, actual_pickup_epoch, shift_type | Automated morning summary: who made it, who was late, which cabs were delayed — per shift, per office | `emp_data` + `ride_data_trip` |
| **Vendor Scorecard** | Transport & Facilities Head | vendor_id, delay_minutes, trip_cost, driver_rating, cab_rating, alerts by vendor | Periodic ranked vendor performance report combining cost, OTA, safety events, and experience ratings | All 5 tables |
| **Cost Anomaly Detector** | Transport & Facilities Head | trip_cost, total_trip_km, slab_name, business_unit | Flags billing anomalies: zero-km trips with non-zero cost, cost spikes vs prior cycle | `bill_data` + `ride_data_trip` |
| **Safety Pulse** | Transport Manager | event_type, severity, acknowledge_time, state_text | Simulated real-time Sev-1 alert escalation when panic/SOS events go unacknowledged beyond a time window | `alerts_data` + `ride_data_trip` |
| **Employee Experience Trend** | Transport & Facilities Head | route_rating, driver_rating, cab_rating, safety_rating | Month-over-month CSAT trend by office and vendor, presentable to leadership | `trip_feedback` + `ride_data_trip` |

---

## 20. Readiness Assessment

### Verdict: **READY TO ENTER PRD**

**Why ready:**
- The problem statement is complete and unambiguous on mandatory requirements.
- All mandatory requirements can be satisfied with `ride_data_trip` alone (OTA Watchdog leading candidate).
- FR-4 is satisfiable via month-over-month historical trend — no SLA data required (SOURCE FACT).
- All previously blocking data uncertainties are either data-validated or scoped out of the MVP.
- No remaining question prevents starting /plan-prd. All unresolved items are product decisions to be made within the PRD process.

**Decisions to resolve during /plan-prd (not prerequisites):**

| Decision | Options | Leading candidate |
|---|---|---|
| **D-1:** OTA formula | delay_minutes==0 / delay_minutes≤T / epoch-based start / epoch-based end | PRODUCT DEFINITION REQUIRED — see §12a |
| **D-2:** Primary persona | Transport Manager / T&F Head / Team-Line Manager | Transport Manager |
| **D-3:** Primary agentic form | Scheduled alert generator / reactive trigger / conversational NL agent | Scheduled OTA alert generator |
| **D-4:** Deterioration trigger threshold | e.g., OTA drops >5 pp month-over-month | Configurable with a reasonable default |
| **D-5:** SPOT_2.0 handling | Include in OTA / exclude / compute separately | Exclude from MVP OTA with documentation |
| **D-6:** Dataset scope | ride_data_trip only / add emp_data / all 5 tables | ride_data_trip only for core MVP |
| **D-7:** SLA threshold inclusion | None (trend only) / configurable inputs | Configurable optional enhancement |

---

## Appendix A: Confirmed Discrepancies Between Dictionary and Actual Data

| # | File | Column | Dictionary states | Actual observation | Impact |
|---|---|---|---|---|---|
| DISC-1 | `ride_data_trip` | `trip_nodal` | Nulls for non-nodal trips | String `"NA"` used, not empty/null | Must normalise "NA" → null |
| DISC-2 | `alerts_data` | `source` | 39,350 nulls | String `"NA"` (39,350 rows) | Must normalise "NA" → null |
| DISC-3 | `alerts_data` | `severity` | Stray `"False"` plus nulls | Also has `"NA"` string (undocumented) | Must handle both bad values |
| DISC-4 | `bill_data` | `slab_name` | ~124,912 nulls | String `"null"` (121,111) + `"NA"` (3,801) = 124,912 total | Must normalise both string-null variants |
| DISC-5 | `bill_data` | `total_trip_km` | "0.0 appears for a meaningful share" | 40.0% of rows — substantially larger than "meaningful share" implies | Material impact on cost-per-km analysis |
| DISC-6 | `trip_feedback` | `marshal_rating` | "Check whether 0 means unrated" (advisory only) | 92.4% zero rate (full file), structurally isolated to marshal_rating only; other rating dims 0.0% | Business meaning of 0 unproven; zero-exclusion is a provisional product rule pending semantic confirmation |

---

## Appendix B: Pre-PRD Decisions and Evidence

This section records the outcomes of the targeted validation pass. Each item is classified by type.

---

### B.1 FR-4 Contextualisation — SLA Not Required

**Type:** SOURCE FACT + PRODUCT DECISION

**Source fact:** §8 Mandatory of the problem statement states FR-4 as: "Contextualises metrics against **at least one** reference point (historical trend, SLA/goal, industry benchmark, **or** peer comparison)." The use of "or" means any single reference point satisfies the mandatory requirement.

**Data-validated fact:** The supplied dataset covers May, June, and July 2026 — three consecutive months — enabling month-over-month OTA, delay, cost, and experience comparisons. This is a legitimate historical trend reference point.

**Product decision:** Historical month-over-month trend is the primary contextualisation mechanism for the MVP. Configurable SLA thresholds are an optional enhancement. Industry benchmarks and peer comparison are not addressable with the supplied data.

**Impact on audit:** Q-1 (SLA thresholds) is no longer a PRD blocker. Condition C-1 from the prior audit is closed.

---

### B.2 Rating Zero-Rate — `marshal_rating` Structural Anomaly

**Type:** DATA-VALIDATED FACT + ASSUMPTION

**Evidence (full file, 512,873 rows):**
- route_rating: 0.0% zeros
- driver_rating: 0.0% zeros
- cab_rating: 0.0% zeros
- safety_rating: 0.0% zeros
- marshal_rating: 92.4% zeros

**DATA-VALIDATED FACT:** `marshal_rating` zero behaviour is structurally different from all other rating dimensions. The 92.4% zero rate is anomalous and isolated to this one column.

**ASSUMPTION:** The most plausible business interpretation is "not applicable — no marshal was present on this trip." This is not proven by the supplied data or dictionary. Zero-exclusion for `marshal_rating` is a provisional downstream product rule, not a confirmed data-cleaning step.

**Q-7 status:** The question "are zeros in non-marshal dimensions valid?" is closed — zero rates for all other dimensions are 0.0%.

**Impact on PRD:** `trip_feedback` is not required for the OTA Watchdog MVP. Marshal_rating semantics can be deferred.

---

### B.3 `delay_minutes` Extreme Values — SPOT_2.0 Correlation

**Type:** DATA-VALIDATED FACT + DEFERRED QUESTION

**Evidence (full scan, 615,546 rows):**
- 279 trips have delay_minutes > 480 (8 hours); 20 trips > 1,440 (24 hours)
- All top-20 extreme values are `SPOT_2.0` product type
- Three vendors account for 272 of 279 >480-min rows: Pooja Mikhailov Travel (148), Pooja Sokolov Travel (97), Vikram Mikhailov Travel (27)
- Delay reasons are legitimate codes (TRAFFIC 185, DRIVER 85, EMPLOYEE 9)
- Distribution is spread across all three months (May 87, June 90, July 102)

**Conclusion:** The extreme values are real data points, not random artifacts. Their exclusive concentration in `SPOT_2.0` strongly suggests a product-type-specific phenomenon (different service model, different trip duration semantics, or systematic calculation issue within that product type). The cause is **unproven**.

**Deferred question:** What is SPOT_2.0? The answer determines whether extreme delay_minutes in that product type are valid data, anomalies to exclude, or require a separate OTA definition.

**Product decision for MVP:** Exclude SPOT_2.0 from OTA calculations. Document the exclusion explicitly. SPOT_2.0 is 0.3% of May trips — negligible impact on overall OTA signal.

---

### B.4 `bill_data` Trip Cardinality

**Type:** DATA-VALIDATED FACT + DEFERRED QUESTION

**Evidence (full scan):**
- 620,782 rows parsed; 613,783 distinct trip_ids
- 606,784 trip_ids (98.9%) have exactly 1 billing row
- 6,999 trip_ids (1.1%) have exactly 2 billing rows
- Maximum rows per trip_id: 2 (no trip has 3+)
- 99.1% of bill trip_ids match a ride trip_id
- 99.9% of ride trip_ids have at least one bill record

**DATA-VALIDATED FACT:** The cardinality structure is known and bounded. 1.1% of trips have exactly 2 billing rows; the maximum is 2.

**DEFERRED QUESTION:** What the two billing rows for the same trip represent (two slabs, a correction row, two legs, or another reason) is not determinable from the data alone. The correct business aggregation rule (sum, latest, specific row type) is unproven.

**Impact on PRD:** `bill_data` is not required for the OTA Watchdog MVP. This question can be deferred to when cost analysis is added. AMB-6 and Q-2 cardinality questions are data-validated; aggregation rule is deferred.

---

### B.5 `bill_data.vendor` vs `ride_data_trip.vendor_id` — Confirmed Same Entity

**Type:** DATA-VALIDATED FACT

**Evidence:**
- ride_data_trip.vendor_id: 23 distinct values
- bill_data.vendor: 24 distinct values
- Exact string overlap: 23/23 (all ride vendors appear verbatim in bill vendors)
- One bill-only vendor: `'Neha Mikhailov Travel'` — present in billing but has no trips in the May–Jul ride data
- No ride vendors are absent from billing

**Conclusion:** `bill_data.vendor` and `ride_data_trip.vendor_id` represent the same entity with the same string values. They can be joined directly by vendor name after normalisation. The `'Neha Mikhailov Travel'` billing-only vendor may have operated outside the May–Jul window or for a product type not captured in the trip data.

**Impact on audit:** Q-10 is closed. §9 "Possible but Unverified" relationship upgraded to Confirmed.

---

### B.6 `business_unit` as Multi-Tenancy Boundary

**Type:** ASSUMPTION → reclassified as POTENTIAL STRATEGY

**Previous claim:** §18 item 7 stated `business_unit` as an architecture-driving requirement for multi-tenancy.

**Correction:** The problem statement (§9 Bonus) lists "credible deployability story into an existing enterprise mobility platform — multi-tenancy, latency, cost" as a *bonus*, not a mandatory requirement. Treating `business_unit` as a mandatory multi-tenancy boundary over-specifies the architecture at this stage.

**Reclassification:** `business_unit` is a natural data partition dimension present in all five tables. It is a reasonable candidate for a multi-tenancy demonstration in the architecture story. It is not an architecture-driving requirement; it is a product decision available if the team wants to pursue the bonus criterion.

---

### B.7 Smallest Defensible MVP — Evidence Summary

**Type:** PRODUCT DECISION

**Candidate:** OTA Watchdog for the Transport Manager persona.

**Evidence that this candidate satisfies all mandatory requirements:**

| Requirement | How OTA Watchdog satisfies it |
|---|---|
| FR-1: Working prototype on provided dataset | `ride_data_trip` (3 CSVs) is self-contained; OTA can be computed without any other table |
| FR-2: Agentic behaviour (senses, reasons, acts) | Sense: computes OTA per vendor per month. Reason: detects deterioration vs prior month. Act: generates structured alert brief autonomously, without user prompting |
| FR-3: Serves at least one persona | Transport Manager: receives a brief naming the deteriorating vendor, magnitude, and dominant delay reason |
| FR-4: Contextualises against at least one reference point | Month-over-month OTA trend is the reference; satisfies the "historical trend" option |

**Evidence supporting the alert (required — not just LLM conclusion):** The alert must include: vendor name, current month OTA %, prior month OTA %, percentage point change, dominant delay reason and its share of delayed trips. These are deterministic facts from the data, not LLM-generated claims.

**Datasets required:** `ride_data_trip` (3 monthly CSVs) only.

**Datasets not required for MVP (optional enrichment):** `emp_data`, `bill_data`, `trip_feedback`, `alerts_data`.

---

### B.6 OTA Formula — Not Defined in Supplied Materials

**Type:** PRODUCT DEFINITION REQUIRED IN PRD

**Search result:** The problem statement (all pages), ride_data_trip.md, README.md, and all other dictionary files were searched for an explicit OTA formula, on-time criteria, tolerance threshold, and definition of which epoch columns define "arrival." None was found.

**SOURCE FACTS established by supplied materials:**
- `delay_minutes`: "Delay duration in minutes" — present in ride_data_trip with values 0–10,644. Calculation method not stated.
- `planned_start_epoch` / `actual_start_epoch`: trip start timing available.
- `planned_end_epoch` / `actual_end_epoch`: trip end timing available.
- ride_data_trip.md lists "on-time arrival (OTA) vs an SLA target" as an **idea to explore** — not a defined metric.
- Problem statement uses "OTA is 78%" as an illustrative example only — no formula attached.

**Defensible OTA formula candidates (see §12a for full table):**

| Candidate | Basis |
|---|---|
| A | `delay_minutes == 0` → on-time |
| B | `delay_minutes <= T` for configurable tolerance T |
| C | `actual_start_epoch <= planned_start_epoch + T` |
| D | `actual_end_epoch <= planned_end_epoch + T` |

**This does not block entering PRD. It is the first product definition to resolve within /plan-prd.**

---

### B.7 Questions Reclassified After Pre-PRD Validation Pass

| Question | Previous status | New status | Reason |
|---|---|---|---|
| Q-1: SLA thresholds | Blocked PRD | **Closed** | Historical trend satisfies FR-4; SLA is optional |
| Q-2: bill_data cardinality | Blocked PRD | **Closed (cardinality); Deferred (aggregation rule)** | Structure data-validated; business meaning of 2-row trips deferred |
| Q-3: Agentic form | Previously "still blocks PRD" | **Product decision during PRD** | Does not prevent starting PRD |
| Q-4: delay_minutes extreme values | Needed answer | **Deferred safely** | Exclude SPOT_2.0 from OTA |
| Q-5: Primary persona | Previously "still blocks PRD" | **Product decision during PRD** | Does not prevent starting PRD |
| Q-7: Non-marshal zero ratings | Open question | **Closed** | 0.0% zero rate for all four other dims |
| Q-8: SPOT_2.0 semantics | Open question | **Deferred safely** | Scope out of MVP OTA |
| Q-OTA: OTA formula definition | Not previously identified | **Product decision during PRD (first priority)** | No authoritative definition in supplied materials |
| Q-10: Vendor join validity | Unverified | **Closed** | 23/23 exact string match confirmed |
