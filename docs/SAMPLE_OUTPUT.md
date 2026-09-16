# OTA Watchdog — Sample Output

Representative output for **Meera Pavlov Travel**, May → June 2026.
All values are deterministic and verified against the real dataset.

---

## Alert card (feed view)

```
Meera Pavlov Travel
76.4% → 68.5%                          −7.86 pp

[5,294 trips]  [Fleet −5.84 pp]  [Recorded: TRAFFIC]  [NODELAY dominant]
```

---

## Alert detail — deterministic evidence

### Vendor Evidence

| Field | Value |
|---|---|
| Prior OTA (May) | 76.39% |
| Current OTA (June) | 68.53% |
| OTA Change | −7.86 pp |
| Prior trips | 5,392 |
| Current trips | 5,294 |

### Fleet Context

| Field | Value |
|---|---|
| Fleet prior OTA | 46.98% |
| Fleet current OTA | 41.14% |
| Fleet change | −5.84 pp |
| Eligible vendors | 21 |
| Breaches | 18 of 21 (85.7%) |

### Recorded Delay Context

> Recorded delay context — not a causal determination.

| Reason | Count | Share of late trips |
|---|---|---|
| NODELAY | 1,518 | 91.1% |
| TRAFFIC | 97 | 5.8% |
| DRIVER | 34 | 2.0% |
| EMPLOYEE | 17 | 1.0% |
| **Total late** | **1,666** | — |

NODELAY dominates: Yes

### Policy

| Parameter | Value |
|---|---|
| T_SECONDS | 300 s (5 min) |
| VOL_MIN | 500 |
| Threshold | > 5.0 pp |
| Policy version | ota-watchdog-v1 |

---

## Operational Brief

> **Representative Claude-generated brief** (produced by Claude Sonnet 4.6 via Amazon Bedrock
> from the deterministic evidence above; actual wording varies per invocation)

**Observation:** Meera Pavlov Travel recorded a 7.86 pp decline in on-time arrival from
May to June (76.39% → 68.53%), based on 5,294 current-period trips.

**Fleet Context:** Across 21 eligible vendors, fleet OTA moved from 46.98% to 41.14%
(−5.84 pp). 18 of 21 vendors crossed the deterioration threshold of >5 pp. Meera
Pavlov Travel's decline of 7.86 pp is above the fleet-level OTA change of −5.84 pp.

**Recorded Delay Context:** Of 1,666 late trips, 1,518 (91.1%) had no recorded delay
reason (NODELAY). The most-recorded non-NODELAY reason was TRAFFIC (97 trips, 5.8% of
late trips). Recorded delay context shows operational data only; causality cannot be
inferred from delay reason codes.

**Suggested Action:** Review vendor operations and validate contributing conditions.
Confirm data completeness for trips marked NODELAY before drawing operational
conclusions.

---

> The deterministic fallback narrative uses the same structure and wording when Bedrock
> is not configured or unavailable.

---

## Deterministic fallback brief (always available)

```
Observation: Meera Pavlov Travel recorded a 7.9 pp OTA decline
(76.4% to 68.5%) from May to June, based on 5,294 trips.

Fleet context: Across 21 eligible vendors, fleet OTA moved 46.98%
to 41.14% (-5.8 pp). 18 of 21 vendors crossed the deterioration
threshold.

Recorded delay context: Of 1,666 late trips, 1,518 (91%) had no
recorded delay reason (NODELAY). The most-recorded non-NODELAY
reason was TRAFFIC (97 trips, 6% of late trips). Recorded delay
context shows operational data only; causality cannot be inferred
from delay reason codes.

Suggested action: Review vendor operations and validate contributing
conditions. Confirm data completeness for trips marked NODELAY
before drawing operational conclusions.
```
