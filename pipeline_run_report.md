# Pipeline Run Report

Schema: `INDY500_V1_2026-09-08`
Canonical format: UTF-8 CSV in `/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈/data/canonical/v1`. CSV was selected because Parquet support is not installed in the frozen runtime.
All datetime fields use explicit UTC `Z` text; local session dates carry `America/Indiana/Indianapolis` separately.

## Source processing

| Source | Status | Staging rows |
|---|---:|---:|
| `official_session_2020.json` | PASS | 59 |
| `official_session_2021.json` | PASS | 59 |
| `official_session_2022.json` | PASS | 44 |
| `results_2023_1.pdf` | PASS | 84 |
| `results_2024_0.pdf` | PASS | 74 |
| `section_2020.pdf` | PASS | 266 |
| `section_2021.pdf` | PASS | 277 |
| `section_2022.pdf` | PASS | 200 |
| `section_2023.pdf` | PASS | 337 |
| `section_2024.pdf` | PASS | 156 |
| `timing71_2020_part1.zip` | PASS | 40 |
| `timing71_2020_part2.zip` | PASS | 18 |
| `timing71_2021_sample.zip` | PASS | 65 |
| `timing71_2023.zip` | PASS | 72 |
| `timing71_2024.zip` | PASS | 97 |
| `2024_indy500_day1_chronology_evidence_pack.docx` | PASS | 13 |
| `hrrr_ims_2020_2024_features.csv` | PASS_NUMERIC | 259 |

## Canonical row counts

| Table | Rows |
|---|---:|
| `qualifying_events` | 5 |
| `attempts` | 329 |
| `attempt_laps` | 1174 |
| `attempt_sections` | 9898 |
| `chronology_events` | 305 |
| `chronology_constraints` | 77 |
| `forecast_snapshots` | 259 |
| `weather_forecasts` | 4403 |
| `sources` | 25 |
| `evidence_items` | 1881 |
| `field_evidence_links` | 133138 |
| `row_eligibility` | 12998 |
| `decision_state_features` | 0 |

## Year status

| Year | Attempts | Complete | Partial | Supported repeats | Usable attempt timestamps | Chronology | Performance core | Chronology core |
|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 2020 | 63 | 46 | 12 | 25 | 0 | PARTIAL | 46 | 0 |
| 2021 | 60 | 51 | 8 | 23 | 54 | PARTIAL | 51 | 0 |
| 2022 | 44 | 40 | 0 | 8 | 0 | FAIL | 0 | 0 |
| 2023 | 85 | 69 | 15 | 34 | 0 | PARTIAL | 69 | 0 |
| 2024 | 77 | 54 | 17 | 4 | 8 | PARTIAL | 54 | 0 |

## Reconstruction, provenance, and missingness

- Canonical attempt count before this correctness patch: 320; after preserving unresolved Section runs: 329.
- Partial source-report lap observations newly preserved: 31 groups (300 section rows); complete candidates preserved but disabled after failed validation: 36.
- Section validation groups: 997; maximum absolute residual among validated groups: 0.0 seconds; maximum failed-candidate residual: 5523.0773 seconds.
- Unmatched/ambiguous Section runs materialized conservatively as `C_SECTION_ONLY`: 9.
- Timing71 qualifier-capture events: 292; linked after conservative matching: 62; left unresolved: 230.
- 2024 constrained pass: 97 captures, 8 uniquely linked and 89 unresolved; attempt constraints are 4 approximate, 4 bounded, 1 ordering-only, and 68 unknown.
- Evidence items: 1881; field evidence/lineage links: 133138.
- HRRR numeric layer: 259 unique cycle/lead snapshots and 4403 numeric values; Phase 4A weather QA failures: 0.
- Public HRRR availability timestamps remain null with `POLICY_REQUIRED` status; cycle time is never substituted for availability.
- `decision_state_features` is intentionally empty: Phase 4A does not align weather to attempts or decision states.

## Analysis readiness

| Analysis target | Status |
|---|---|
| `FOUR_LAP_PERFORMANCE` | `READY` |
| `LAP_PERFORMANCE` | `READY` |
| `WITHIN_CAR_COMPARISON` | `READY_WITH_SUPPORTED_SUBSET` |
| `CHRONOLOGY` | `NOT_READY` |
| `QUEUE_CALIBRATION` | `READY_FOR_LIMITED_CAPTURE_BASED_CALIBRATION` |

## Known limitations

- Timing71 produces recorder/capture times only; canonical capture-event quality remains `APPROXIMATE_OBSERVED`. Capture time is not release time or timed-run start. Positional linking occurs only when independently supported and unambiguous.
- The 2020 internal gap and 2023 terminal gap are explicit `COVERAGE_GAP` rows. State is never forward-filled across them.
- Chronology reconciliation is incomplete, including 2021 and 2024; ambiguous capture events remain unlinked rather than being assigned by ranked Results order.
- 2022 has no Timing71 replay in the frozen evidence and no fabricated attempt timestamps.
- 2024 Section Results preserve all attributable selected/partial section rows but do not prove repeated-attempt coverage.
- Within-car comparison is a robustness/sub-analysis population; it is not a prerequisite for cross-car performance modelling.
- Lane, withdrawal time, requeue, and queue state remain unknown unless directly documented. No inferred queue/lane value is promoted.
- Exact historical HRRR public availability is unresolved. A documented, configurable, versioned latency policy is required before time-safe decision-state joins.
- `TMP_2m` remains 2 m air temperature and `DSWRF_surface` remains downward shortwave radiation; neither is labelled as track temperature.

## Validation outcome

Blocking machine-check failures: 1.
The global gate requires all requested analysis families to be ready. Chronology is not globally ready because no year reaches reconciliation PASS. Queue calibration is limited to observed capture-based attempt processes and does not claim exact lane or queue state.

`PIPELINE NOT READY — BLOCKING DATA INTEGRITY ISSUES`
