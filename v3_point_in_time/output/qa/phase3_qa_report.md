# Phase 3 QA Report

| Check | Result |
|---|---|
| Existing Phase 1/2 tests | **PASS** — all 28 retained tests re-run unmodified |
| New Phase 3 tests | **PASS** — 18/18 (`test_phase3_replay.py`), covering all 18 required items |
| Total tests | **46 / 46 PASS** |
| V2 immutability | **PASS** — `v2_immutability_report.txt`: 32/32 frozen dependencies byte-identical, re-checked after all Phase 3 work |
| V3↔V2 behavioural regression | **PASS** — `run_v3_v2_behavioral_regression.py` re-run: all 5 horizons within Monte-Carlo-sampling-error tolerance |
| Future-information leakage | **PASS** — `build_information_state` excludes any item known after decision_time (test 2); a post-decision-time forecast never enters an issued outlook (test 3); `select_and_build_snapshot`'s guard is re-checked defense-in-depth inside `replay_case` |
| Forecast provenance | **PASS** — every `SHADOW_INFERENCE_ISSUED`/`PREDICTION_SCORED` event's `provenance_ids` match the exact `ForecastVintage` actually used (test 12); `shadow_engine.ForecastProvenanceMismatch` remains armed underneath (unchanged from Phase 2) |
| Replay time ordering | **PASS** — every case's event list is emitted in non-decreasing `event_time` order by construction (all decision-time events, including the case-level `APPLICABILITY_CHANGED` summary, are appended before any event timestamped at the later `realised_attempt_time`); verified directly (test 1) |
| Abstention auditability | **PASS** — abstention is a `ReplayEvent` with `evaluation_status=ABSTAINED` and a closed-vocabulary `abstention_reason_codes` tuple, never a swallowed exception or a dropped row; all 31 excluded pre-candidates and all abstained scoring attempts appear in `output/replay/replay_case_summary.csv` (test 18) |
| Illustrative case excluded from aggregate validation | **PASS** — the 2021 car 60 case's `PREDICTION_SCORED` event carries `counts_toward_aggregate_validation: false` and `evaluation_status: ILLUSTRATIVE_ONLY` (test 6); the substitution rule is looked up from a single named table (`ILLUSTRATIVE_APPROVED_CASES`), never derived from a general distance/tolerance threshold that could silently apply to another case |
| Queue model introduced | **NO** |
| Strategy recommendation introduced | **NO** |
| FINAL_V2 refitted | **NO** |
| New ML model introduced | **NO** |

## Replay counts (all 41 real same-car transitions Phase 2 already inventoried; no new data acquired)

| Category | Count |
|---|---|
| Candidate cases considered | 41 (10 defensible + 31 excluded pre-candidates) |
| Conditional inference supported (≥1 of the 5 calibrated anchors) | **9** (all 9 real out-of-support-for-scoring 2021 cases: car 12, 18, 2, 21, 26, 4, 47, 7, 86) |
| Historical scoring formally supported (exact anchor match) | **0** |
| Illustrative only | **1** (2021, car 60) |
| Abstained — insufficient timestamp | **31** |
| Abstained — out of support (case-level; none — see note) | 0 |
| Abstained — forecast unavailable (case-level) | 0 |

**Note on "abstained — out of support" = 0 at the case level:** this is the intended, correct result of Phase 3's Step 6 fix, not an omission. Phase 1/2 evaluated each case at its *realised* horizon, which is why the 9 non-illustrative real cases were labelled `OUT_OF_SUPPORT` there. Phase 3 instead evaluates every case's *conditional outlook* only at the five calibrated anchors (which never exceed 120 min by construction), so those 9 cases now show full inference support; the horizon-out-of-support fact still governs — and abstains — their *historical scoring* (`HORIZON_OUT_OF_SUPPORT` appears 9 times as a reason code on their `PREDICTION_SCORED`-abstained events; see `replay_abstention_summary.csv`).

## Abstention reason breakdown (`output/replay/replay_abstention_summary.csv`)

| Reason code | Count | Where |
|---|---|---|
| `INSUFFICIENT_ATTEMPT_TIMESTAMP` | 31 | pre-candidates excluded before a decision_time could be constructed (ambiguous multi-attempt pairing or no usable timestamp) |
| `HORIZON_OUT_OF_SUPPORT` | 9 | historical-scoring abstention for the 9 real candidates whose realised horizon (125.8–288.0 min) exceeds the 120-min production boundary |
| `NON_ANCHOR_EVALUATION_NOT_APPROVED` | 1 | the illustrative car 60 case's scoring event (illustrative, not aggregate-validation) |

`NO_VALID_FORECAST_VINTAGE`, `INSUFFICIENT_CURRENT_STATE`, `POINT_IN_TIME_VIOLATION`, `MISSING_REQUIRED_FORECAST_INPUT`, `REGIME_APPLICABILITY_UNRESOLVED`, and `PROVENANCE_MISMATCH` are wired and tested (`test_phase3_replay.py` tests 3-5) but do not occur in this real evidence set — every real candidate already has an available point-in-time HRRR forecast at each of the five anchors.

## What is new, engineering-wise

The 9 real 2021 candidates that Phase 2 could only record as `OUT_OF_SUPPORT` (because Phase 2 evaluated at the *realised* horizon) now each have a genuine, non-fabricated conditional physical outlook at all five calibrated anchors, using their real current physical state and a real point-in-time HRRR forecast vintage selected under the same `issue_time <= decision_time` rule as before. This makes Phase 3's structural distinction between **inference support** and **historical evaluation support** (Step 6) a real, populated result rather than a documentation-only distinction — see `output/replay/replay_case_summary.csv`, category `CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED`.

## Scientific limitations (Phase 3, in addition to Phase 1/2's)

1. All 9 `CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED` outlooks are real, defensible FINAL_V2 inferences, but **none of them can be checked against a realised outcome** — there is no aggregate accuracy claim to make about them, by construction.
2. The illustrative car 60 case remains N=1 and is not statistically generalizable (unchanged from Phase 2; restated in `phase2_interpretation_addendum.md`).
3. The `explanation_terms()` display decomposition (thermal gap, forecast ambient trajectory, predicted track-temperature change, solar elevation) duplicates the exact closed-form arithmetic already inside `final_v2_adapter.infer()` for display purposes; it is not an independently verified second implementation, so a bug in the shared formula would appear identically in both places (acceptable for a display value, called out here for transparency).
4. The V2-D uncertainty-source reference attached to each outlook (`_uncertainty_source_reference`) is a frozen, horizon-level ablation result, not a per-prediction decomposition; it is labelled as such in every payload that carries it.

## Design decisions requiring human approval

1. **Case-level category definition for the 9 real out-of-support cases.** This report labels them `CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED` rather than `ABSTAINED_OUT_OF_SUPPORT`, on the reasoning that inference genuinely succeeds at the calibrated anchors even though scoring against the realised outcome is correctly abstained. An alternative, more conservative labelling would classify them as `ABSTAINED_OUT_OF_SUPPORT` at the case level (treating "the realised horizon is out of support" as disqualifying the whole case, not just its historical scoring). Both are defensible; this report used the more granular, information-preserving choice and documents it here for explicit sign-off.
2. **`explanation_terms()` duplicates rather than reuses `final_v2_adapter.infer()`'s internal computation** (see limitation 3 above), specifically to avoid modifying the Phase 1/2-tested `final_v2_adapter.py` file for a display-only feature. If exposing these intermediate terms is wanted long-term, refactoring `infer()` itself to return them (still without changing any computation) would remove this duplication — not done here to minimize risk to already-regression-tested code, flagged for a decision.
