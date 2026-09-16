# OTA Watchdog — Sample Output

Representative output for **Meera Pavlov Travel**, May → June 2026.
All values are deterministic and verified against the real dataset.

---

## Alert card (feed view)

```
Meera Pavlov Travel
76.4% → 68.5%                          ↓ 7.86 pts

[5,294 trips]  [Fleet −5.84 pts]  [Top non-NODELAY: TRAFFIC]  [NODELAY most frequent label]
```

---

## Alert detail — deterministic evidence

### Vendor Evidence

| Field | Value |
|---|---|
| Prior OTA (May) | 76.39% |
| Current OTA (June) | 68.53% |
| OTA Change | ↓ 7.86 pts |
| Prior trips | 5,392 |
| Current trips | 5,294 |

### Fleet Context

| Field | Value |
|---|---|
| Fleet prior OTA | 46.98% |
| Fleet current OTA | 41.14% |
| Fleet change | −5.84 pts |
| Eligible vendors | 21 |
| Threshold crossings | 18 of 21 (85.7%) |

### Recorded Delay Context

> Recorded delay context — not a causal determination.

| Reason | Count | Share of late trips |
|---|---|---|
| NODELAY | 1,518 | 91.1% |
| TRAFFIC | 97 | 5.8% |
| DRIVER | 34 | 2.0% |
| EMPLOYEE | 17 | 1.0% |
| **Total late** | **1,666** | — |

NODELAY most frequent: Yes

### Policy

| Parameter | Value |
|---|---|
| T_SECONDS | 300 s (5 min) |
| VOL_MIN | 500 |
| Threshold | > 5.0 percentage points |
| Policy version | ota-watchdog-v1 |

---

## Operational Brief

> **Representative Claude-generated brief** (produced by Claude Sonnet 4.6 via Amazon Bedrock
> from the deterministic evidence above; actual wording varies per invocation)

**Observation:** Meera Pavlov Travel recorded a 7.86 percentage-point decline in on-time arrival from
May to June (76.39% → 68.53%), based on 5,294 current-period trips.

**Fleet Context:** Across 21 eligible vendors, fleet OTA moved from 46.98% to 41.14%
(a change of 5.84 percentage points). 18 of 21 vendors crossed the deterioration threshold of >5 percentage points. **Recorded Delay Context:** Of 1,666 late trips, 1,518 (91.1%) were labeled NODELAY. The most-recorded non-NODELAY reason was TRAFFIC (97 trips, 5.8% of
late trips). Recorded delay context shows operational data only; causality cannot be
inferred from delay reason codes.

**Suggested Action:** Review vendor operations and validate contributing conditions.
Validate the operational meaning of NODELAY before using the recorded label
distribution diagnostically.

---

> The deterministic fallback uses the same verified evidence but its wording and
> formatting may differ.

---

## Deterministic fallback brief (always available)

```
Observation: Meera Pavlov Travel recorded a 7.86 percentage-point OTA decline
(76.39% to 68.53%) from May to June, based on 5,294 trips.

Fleet context: Across 21 eligible vendors, fleet OTA moved 46.98%
to 41.14% (a change of 5.84 percentage points). 18 of 21 vendors crossed the deterioration
threshold.

Recorded delay context: Of 1,666 late trips, 1,518 (91.1%) were labeled NODELAY. The most-recorded non-NODELAY
reason was TRAFFIC (97 trips, 6% of late trips). Recorded delay
context shows operational data only; causality cannot be inferred
from delay reason codes.

Suggested action: Review the OTA deterioration with the vendor and validate
operational conditions. Validate the operational meaning of NODELAY before
using the recorded label distribution diagnostically.
```
