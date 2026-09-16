# OTA Watchdog — Agentic Vendor Performance Monitor

---

## Problem

Transport Managers at large enterprises using MoveInSync's mobility platform are accountable for vendor coordination, escalations, and delay management. The platform generates rich structured trip data continuously, but performance insight is surfaced through static periodic reports. When a vendor's on-time performance deteriorates, the Transport Manager must manually assemble and compare data across time periods to detect it. MoveInSync's own problem statement identifies this as a core gap: metrics are presented without historical context, and contextualisation against trend, SLA, or peer "is currently absent." The cost of leaving this unsolved is that actionable deterioration signals arrive late — or not at all — because a human must first think to look.

---

## Evidence

**Source facts (from MoveInSync challenge brief):**
- §3: "Most of [Transport Managers'] time goes into assembling data, not acting on it."
- §4: "A metric without context is just a number" — benchmarking against historical trend, SLA, or peer comparison "is currently absent."
- §4 example: "OTA is 78%" is described as insufficient context; "it was 85% last month, SLA is 90%, and two vendors are responsible for the gap" is the desired state.

**Data-validated:**
- The supplied dataset contains 615,546 trip records across three months (May–July 2026), 23 vendors, and 5 business units, establishing that the signal required to detect deterioration is present in the operational data.

**Evidence limitation:**
Problem evidence is grounded in MoveInSync's first-party challenge brief and the supplied operational dataset. No independent user interviews, support tickets, NPS data, or quantified manual-reporting-time measurements have been conducted within this project. Independent end-user validation is recorded as a future activity, not a blocker.

---

## Users

- **Primary:** Transport Manager — responsible for day-to-day mobility operations: vendor coordination, escalations, shift planning, delay management. Receives a generated alert and evidence without running a report or initiating a query.
- **Not for (MVP):** Transport & Facilities Head (different output format and reporting cadence), Team / Line Manager (shift-level grain, different decision type), external vendor contacts, platform administrators.

---

## Hypothesis

We believe an automated OTA Watchdog that detects meaningful vendor performance deterioration and generates an evidence-backed operational brief will reduce the need for manual report assembly for this decision workflow and give Transport Managers faster, contextual information for vendor coordination and escalation.

For the MVP, we will consider the hypothesis demonstrated when the system can autonomously identify a qualifying vendor deterioration from the supplied dataset, generate a brief containing deterministic supporting evidence, and make that brief available to the Transport Manager without the manager running a manual report or initiating a query.

**What we do not claim:** measured time savings, productivity gains, or adoption impact — these require independent user evidence not available at this stage.

---

## MVP Validation Criteria

A correctly functioning MVP must satisfy all of the following. These are acceptance criteria, not implementation tasks.

1. A scheduled or replay-driven run starts without a user query or manual trigger.
2. Vendor OTA is calculated deterministically from trip data using the defined OTA formula (see §OTA Formula Definition).
3. The current period is compared with the immediately preceding period (month-over-month).
4. Only vendors meeting the configured minimum trip-volume rule are eligible to generate an alert.
5. A vendor whose OTA deteriorates by more than the configured threshold produces exactly one alert for that period.
6. No qualifying deterioration means no alert is fabricated.
7. Every alert contains the following as deterministic computed values — not LLM-generated:

   **Vendor evidence**
   - Vendor name
   - Current period OTA %
   - Prior period OTA %
   - OTA percentage-point change
   - Trip count (current period)
   - Trip count (prior period)
   - Periods compared (e.g., "July 2026 vs June 2026")

   **Recorded delay-reason context** (not causal attribution — see data-quality note below)
   - Full delay_reason distribution for OTA-late trips in the current period (reason → count → share of OTA-late trips)
   - NODELAY share of OTA-late trips
   - Top non-NODELAY recorded reason (if any)
   - Top non-NODELAY reason count
   - Top non-NODELAY reason share of OTA-late trips
   - Data-quality flag when NODELAY > 50% of OTA-late trips: *"The operational delay_reason field is not aligned with the OTA definition used by this product. Recorded reasons are contextual evidence, not causal attribution."*

   **Fleet / cohort context**
   - Fleet OTA % (current period, eligible vendors only)
   - Fleet OTA % (prior period, eligible vendors only)
   - Fleet OTA pp change (current vs prior)
   - Eligible vendor count (current period)
   - Count of eligible vendors breaching the deterioration rule in this comparison
   - Percentage of eligible vendors breaching the deterioration rule
8. An LLM may compose or summarise the operational brief from these facts; it must not calculate, invent, or alter any evidence value.
9. The Transport Manager can inspect the generated alert and its full deterministic evidence in the in-app alert feed without leaving the product.
10. SPOT_2.0 trips are excluded from all OTA calculations; this exclusion is explicitly documented and visible to the user.

---

## OTA Formula Definition

> **PRODUCT DECISION — not a MoveInSync source fact.**

No authoritative OTA formula, on-time threshold, or tolerance appears in any supplied material (problem statement, data dictionaries, or dataset). The following is adopted as a product definition for this implementation:

**A trip is considered on-time if:**
```
actual_end_epoch <= planned_end_epoch + T
```
where **T** is a configurable tolerance in seconds.

**Demo default for T:** 5 minutes (300 seconds) — calibrated from empirical profiling of the supplied dataset (n = 613,223 eligible trips, SPOT_2.0 excluded). Key findings: fleet-wide median arrival delta = +445 s (7.4 min). T = 0 is the strict product baseline and yields 33.5% on-time across the supplied eligible dataset. T = 5 minutes is adopted as the demo default because it provides greater operating differentiation across vendors in this dataset. It is an empirically calibrated product choice, not a MoveInSync SLA or validated business standard. Configurability is mandatory.

**Trips excluded from OTA computation:**
- `SPOT_2.0` product type — excluded pending clarification of its service semantics. All top-20 extreme delay values in the dataset are SPOT_2.0 trips; their semantics are unknown (see Open Questions OQ-3). Exclusion must be visible in the product.
- Trips with null `actual_end_epoch` — incomplete trip records; excluded with count surfaced.

---

## Deterioration Trigger

> **PRODUCT / DEMO DEFAULTS — not supplied requirements.**

| Parameter | Demo default | Configurable? |
|---|---|---|
| Minimum OTA deterioration to trigger alert | 5 percentage points vs prior month | Yes |
| Minimum vendor trip volume per period | 500 trips — see calibration evidence below | Yes |

The 5 percentage-point threshold is a product/demo default chosen for plausibility. It has no MoveInSync-supplied basis and must not be presented as one.

The 500-trip threshold is an empirical demo policy. In the supplied dataset it cleanly excludes the isolated low-volume vendor cohort (114–121 trips/month), while thresholds from 250 through 2,600 produce the same alert set for the remaining vendors. No statistical significance analysis has been performed; 500 is not claimed to be a statistically proven threshold. Configurability is mandatory.

---

## Success Metrics

| Metric | Target | How measured |
|---|---|---|
| Alerts are fully evidence-backed | 100% of fired alerts contain all deterministic fields defined in criterion 7 | Verified against MVP Validation Criteria |
| Rule-consistent alert behaviour | Alerts fire exactly when the configured OTA, volume, and deterioration rules are met; zero alerts generated when no vendor qualifies | Run against a period where no vendor meets the threshold; verify zero output |
| Autonomous execution | Agent completes a full run without user initiation | Observable in scheduled / replay demo |
| Evidence integrity | LLM output contains no values inconsistent with the deterministic evidence payload | Manual review of generated brief vs computed evidence for each alert |

*Broader outcome metrics (manager time saved, escalation rate reduction) require independent user research and are not measurable within this project.*

---

## Scope

### MVP — OTA Watchdog for Transport Manager

- **Data:** `ride_data_trip` (May, June, July 2026) — no other tables required for core MVP
- **OTA computation:** per-vendor, per-month, using the product-defined formula
- **Context:** month-over-month comparison (current month vs immediately prior month)
- **Detection:** configurable deterioration threshold + configurable minimum volume filter
- **Alert generation:** deterministic evidence payload assembled first; LLM composes operational brief from that payload
- **Delivery:** in-app Transport Manager alert inbox / feed
- **Evidence view:** Transport Manager can inspect all computed fields for each alert
- **Execution model:** scheduled run or simulated data-replay over the static dataset
- **SPOT_2.0:** explicitly excluded from OTA computation; exclusion documented and visible

### Out of scope

| Item | Reason deferred |
|---|---|
| Safety Pulse (SOS, geofence, over-speeding alerts) | First stretch vertical slice after MVP — reuses the same agentic alerting pattern |
| Cost analysis (bill_data) | Separate vertical slice |
| Employee experience ratings (trip_feedback) | Separate vertical slice |
| No-show / shift readiness reporting (emp_data) | Separate vertical slice |
| Transport & Facilities Head persona | Different output format and reporting cadence |
| Team / Line Manager persona | Different data grain and decision type |
| Conversational NL querying | Not required for MVP |
| Near-real-time reactive triggers | Architecture should accommodate this pattern; not day-one |
| Email / Slack / Teams / SMS delivery integrations | External notification; future enhancement |
| Full analytics / BI dashboard | Not the agentic model required |
| Manual data exploration / ad-hoc chat | Not required for MVP |
| Predictive forecasting or ML-based vendor scoring | Out of scope |
| Automated actions against external vendor systems | Out of scope |
| Production streaming infrastructure | Out of scope — static dataset only |
| Production-grade multi-tenancy | Out of scope for MVP; bonus criterion for future |
| Production authentication / security | Explicitly out of scope per problem statement §8 |
| Live vendor system integration | Explicitly out of scope per problem statement §8 |
| Industry benchmark or peer comparison data | Not supplied; month-over-month historical trend is the reference |

---

## Delivery Milestones

*Business outcomes, not engineering tasks. `/plan` turns each into an implementation plan.*
*Status: pending | in-progress | complete*

| # | Milestone | Outcome | Status | Plan |
|---|---|---|---|---|
| 1 | Data foundation | `ride_data_trip` is ingested and normalised (trip_id format, epoch columns, "NA"/"null" string placeholders, schema drift across months); SPOT_2.0 trips are identified and excluded; OTA is computable per vendor per month | in-progress | `.claude/plans/ota-watchdog.plan.md` |
| 2 | OTA computation & context engine | Deterministic per-vendor OTA % is produced for each month; month-over-month comparison is available; minimum-volume filter is applied before comparison | pending | — |
| 3 | Detection & evidence assembly | Deterioration detection fires correctly against the configured threshold; all deterministic evidence fields defined in criterion 7 are assembled and verifiable for each qualifying vendor | pending | — |
| 4 | Brief generation & alert delivery | LLM composes an operational brief from the evidence payload; brief is delivered to the in-app Transport Manager alert feed; rule-consistent alert behaviour is verified (alerts fire exactly when the configured rules are met; no alerts fabricated when no vendor qualifies); Transport Manager can view full evidence detail for each alert | pending | — |
| 5 | Scheduled / replay execution | Agent runs on schedule or simulated replay without user initiation; the complete sense → reason → act cycle operates end-to-end on the supplied dataset; demo-ready | pending | — |

---

## Open Questions

### MVP calibration items — unresolved before demo

- [x] **OQ-1 — OTA tolerance T:** **RESOLVED — demo default T = 5 minutes (300 s).** Empirical basis: fleet-wide median arrival delta = +445 s across 613,223 eligible trips. T = 0 is the strict product baseline and yields 33.5% on-time in this dataset; T = 5 min is adopted as the demo default because it provides greater operating differentiation across vendors in this dataset. This is an empirically calibrated product choice, not a MoveInSync SLA or validated business standard.

- [x] **OQ-2 — Minimum vendor trip volume:** **RESOLVED — demo default = 500 trips/period.** This is an empirical demo policy: in the supplied dataset, thresholds from 250 to 2,600 all produce the same alert set; 500 cleanly excludes the isolated low-volume cohort (114–121 trips/month). No statistical significance analysis was performed; 500 is not claimed to be a statistically proven threshold.

- [ ] **OQ-3 — SPOT_2.0 semantics:** What service model does SPOT_2.0 represent? Its trips produce all extreme delay values in the dataset; behaviour is unexplained by any supplied material. Excluded from MVP OTA pending clarification. If semantics are confirmed before demo, inclusion may be revisited.

### Deferred — not relevant to OTA Watchdog MVP

- **marshal_rating = 0 meaning:** Whether zero means "no marshal present" is unproven by supplied data. Relevant only when `trip_feedback` is used (future experience slice).
- **Duplicate bill_data row aggregation rule:** What two billing rows for the same trip represent, and the correct aggregation rule, is unknown. Relevant only when `bill_data` is used (future cost slice).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Vendor trip volumes too low for statistically meaningful OTA signal | Medium | High — alerts become unreliable or misleading | Set minimum-volume threshold via empirical profiling (OQ-2); suppress alerts below threshold |
| No qualifying deterioration detected in the supplied dataset at the chosen threshold | Low — MITIGATED | Medium — demo has nothing to show | Calibration confirmed 18 rule-qualified alerts in May→June at T = 5 min, 5 pp; demo signal is available |
| LLM produces values inconsistent with the deterministic evidence payload | Medium | High — undermines trust in the output | Architecture must pass evidence as a structured payload; LLM composes narrative only; validate output against evidence before display |
| Alert volume too high or too low for the demo period | Low — MITIGATED | Medium — demo credibility | Calibration showed 18 alerts May→Jun (broad period-wide event), 0 Jun→Jul; fleet context fields in the evidence payload provide the denominator the Transport Manager needs to interpret alert volume |
| SPOT_2.0 exclusion later proves significant | Low (0.3% of May trips) | Low | Document exclusion explicitly; revisit if semantics are clarified |
| Epoch calculation produces extreme delay values for non-SPOT trips | Low | Medium — OTA figures skewed | Profile `actual_end_epoch − planned_end_epoch` for CAB and BUS trips; apply outlier detection |
| Schema drift across months causes silent data loss during concat | Medium | Medium — incorrect OTA figures | Explicit dtype reconciliation required in data foundation milestone |

---

## Calibration Evidence

Empirical profiles run against `ride_data_trip` May–July 2026 (SPOT_2.0 excluded). Source: pre-implementation calibration profiling. These numbers are inputs to product decisions — they are not implementation code.

### Profile 1 — Eligibility
| Month | Total trips | SPOT_2.0 excluded | Eligible | Vendors | Null-epoch rows |
|---|---|---|---|---|---|
| May 2026 | 188,992 | 648 | 188,344 | 22 | 0 |
| June 2026 | 210,669 | 702 | 209,967 | 22 | 0 |
| July 2026 | 215,885 | 973 | 214,912 | 22 | 0 |
| **Total** | **615,546** | **2,323** | **613,223** | 22 | 0 |

### Profile 2 — Arrival delta distribution (all eligible trips, n = 613,223)
`delta = actual_end_epoch − planned_end_epoch` (seconds)

| Statistic | Value | Interpretation |
|---|---|---|
| p1 | −2,418 s | Early-arrivals tail |
| p5 | −1,325 s | |
| p25 | −230 s | ~4 min early |
| **Median** | **+445 s** | **~7.4 min late** |
| p75 | +1,282 s | ~21 min late |
| p90 | +2,325 s | ~39 min late |
| p95 | +3,259 s | ~54 min late |
| p99 | +5,684 s | ~95 min late |
| Strict on-time (≤0 s) | 33.5% | Strict product baseline |
| On-time at T=5 min | 44.7% | **Demo default** |
| On-time at T=10 min | 55.4% | |

### Profile 3 — Vendor / month volume distribution (66 cohorts across 22 vendors, 3 months)
| Statistic | Value |
|---|---|
| Min | 114 (Meera Lebedev Travel — micro-vendor, 3 months) |
| p10 | 2,936 |
| p25 | 4,871 |
| Median | 6,403 |
| p75 | 10,712 |
| p90 | 19,168 |
| Max | 25,857 |

Volume threshold impact: thresholds of 250, 500, 1,000, and 2,000 all produce identical eligible sets (21 vendors). Only Meera Lebedev Travel (114–121 trips/period) is excluded above 250.

### Profile 3b — Fleet-wide OTA aggregate (T = 5 min, vol ≥ 500, SPOT_2.0 excluded, eligible vendors only)
| Period | Fleet OTA | Eligible vendors |
|---|---|---|
| May 2026 | 46.98% | 21 |
| June 2026 | 41.14% | 21 |
| July 2026 | 46.13% | 21 |

| Transition | Fleet pp change | Vendors breaching 5 pp deterioration rule | % of eligible vendors |
|---|---|---|---|
| May → June | −5.84 pp | 18 | 86% |
| June → July | +4.99 pp | 0 | 0% |

Note: fleet OTA is computed over the 21 eligible vendors only; Meera Lebedev Travel (below volume threshold) is excluded. This context is a mandatory component of every alert evidence payload (see criterion 7).

### Profile 4 — Per-vendor OTA summary at T = 5 minutes (May–June–July)
Top deteriorations May → June (largest to smallest):

| Vendor | May OTA% | Jun OTA% | Change |
|---|---|---|---|
| Meera Pavlov Travel | 76.39% | 68.53% | −7.86 pp |
| Amit Volkov Travel | 41.80% | 34.02% | −7.78 pp |
| Sanjay Mikhailov Travel | 44.78% | 37.79% | −6.99 pp |
| Priya Mikhailov Travel | 53.64% | 46.89% | −6.74 pp |
| Pooja Mikhailov Travel | 42.72% | 36.00% | −6.72 pp |
| Karan Mikhailov Travel | 46.19% | 39.46% | −6.72 pp |

June → July: most vendors recovered (+6 to +10 pp). No vendor deteriorated by ≥ 5 pp June → July at T = 5 min except Meera Lebedev Travel (micro-vendor, excluded by volume filter).

### Profile 5 — Alert trigger sensitivity (threshold = 5 pp, T = 5 min)
All volume thresholds from 250 to 2,000 trips produce identical alert sets:
- **May → June: 18 rule-qualified alerts fired** (18 of 21 eligible vendors met the deterioration rule)
- **June → July: 0 rule-qualified alerts fired** (no eligible vendor met the deterioration rule)

The system behaved consistently with the configured OTA, volume, and deterioration rules in both periods. No external ground-truth labels are available to assess whether individual alerts represent genuine operational incidents.

### Profile 6 — Strongest alert candidate (full evidence payload)
Vendor: **Meera Pavlov Travel** | Period: May → June 2026 | T = 5 minutes

**Vendor evidence**

| Evidence field | Value |
|---|---|
| Vendor | Meera Pavlov Travel |
| Current period OTA | 68.53% (June 2026) |
| Prior period OTA | 76.39% (May 2026) |
| OTA pp change | −7.86 pp |
| Trip count (current) | 5,294 (June 2026) |
| Trip count (prior) | 5,392 (May 2026) |
| Periods compared | June 2026 vs May 2026 |

**Fleet / cohort context** *(eligible vendors, T = 5 min, vol ≥ 500, SPOT_2.0 excluded)*

| Evidence field | Value |
|---|---|
| Fleet OTA — current period | 41.14% (June 2026) |
| Fleet OTA — prior period | 46.98% (May 2026) |
| Fleet OTA pp change | −5.84 pp |
| Eligible vendor count | 21 |
| Vendors breaching deterioration rule (May → June) | 18 of 21 (86%) |

This context allows the Transport Manager to distinguish a vendor-specific signal from a period-wide pattern. In this case, 18 of 21 eligible vendors (86%) deteriorated by more than 5 pp in the same transition, and the fleet-wide OTA fell −5.84 pp. The alert for Meera Pavlov (−7.86 pp) is rule-qualified; the brief should surface the fleet context so the manager can assess whether this is an isolated vendor issue or a broader operational event. Whether the pattern is "systemic" is left for operational judgement — the product surfaces the deterministic evidence.

**Recorded delay-reason context** *(not causal attribution)*

> **Data-quality note:** The operational `delay_reason` field is not aligned with the OTA definition used by this product. Recorded reasons are contextual evidence, not causal attribution. NODELAY is assigned by the source system and does not mean no delay occurred under this product's formula.

| Metric | May 2026 | June 2026 |
|---|---|---|
| OTA-late trips (delta > T) | 1,273 | 1,666 |
| NODELAY share of OTA-late trips | 96.9% (1,234) | 91.1% (1,518) |
| TRAFFIC | 1.3% (17) | 5.8% (97) |
| DRIVER | 1.0% (13) | 2.0% (34) |
| EMPLOYEE | 0.7% (9) | 1.0% (17) |

Top non-NODELAY recorded reason in current period: **TRAFFIC** — 97 instances, 5.8% of OTA-late trips.

Secondary recorded signal: TRAFFIC instances increased from 17 (May) to 97 (June), a 5.7× increase in recorded count. This is a data observation, not a causal claim about what drove the OTA change. The LLM brief may surface this as a secondary recorded signal alongside the NODELAY data-quality note.

---

*Status: DRAFT — calibration complete. Implementation planning pending via `/plan`.*
