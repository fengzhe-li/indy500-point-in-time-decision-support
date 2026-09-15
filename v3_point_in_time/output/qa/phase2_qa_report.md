# Phase 2 QA Report

| Check | Result |
|---|---|
| Phase 1 tests | **PASS** — all 20 Phase 1 tests re-run and pass unmodified (after the Step 5 provenance-authority fix, which required small, disclosed updates to `shadow_engine.py`'s call signature and two Phase 1 test files that called it directly — behaviour re-verified via the Phase 1 demo producing identical numbers before/after) |
| V2 byte immutability | **PASS** — `v2_immutability_report.txt`: 32/32 frozen dependencies byte-identical, re-checked after all Phase 2 work |
| V3↔V2 behavioural regression | **PASS** — `v3_v2_behavioural_regression_report.md`: all 5 horizons agree with the frozen batch script's own recorded output within a Monte-Carlo-sampling-error tolerance (5σ of the combined standard error), using an intentionally different RNG stream |
| Forecast provenance single-source-of-truth | **PASS** — Step 5 fix implemented: `shadow_engine.select_and_build_snapshot` selects forecasts exactly once, before the snapshot exists; `run_single_horizon` raises `ForecastProvenanceMismatch` if given any other vintage; tested directly in `test_phase2_provenance_and_evaluation.py` and exercised in the real 10-case evaluation |
| Historical forecast source authoritative | **PASS** — real NOAA HRRR extract (`weather/output/hrrr_ims_2020_2024_features.csv`), already in the repository; re-verified independently in `phase2_existing_forecast_evidence_audit.md` |
| Forecast issue timestamps available | **PASS**, with a disclosed caveat — `issue_time` = real HRRR nominal cycle time; real-world publication latency beyond the nominal cycle is not quantified anywhere in this project (unchanged from Phase 1's finding) |
| Future-information leakage | **PASS** — every one of the 10 real cases' decision snapshots passed the point-in-time guard; no case used a forecast issued after its decision_time or a current-state reading known only after it |
| Synthetic data excluded | **PASS** — `SYNTHETIC_TEST_FIXTURE` never appears in `phase2_case_table.csv` (tested directly); the real case table's `forecast_source` is `NOAA` for the one evaluated case |
| **Real point-in-time cases available** | **N = 10** (all from 2021; see `phase2_minimum_data_plan.md` for why 2020/2022/2023/2024 transitions were excluded — ambiguous multi-attempt pairing or no usable timestamp, not a sampling choice) |
| **Supported ≤120 min cases** | **N = 1** (2021, car 60; realised horizon 64.1 min, evaluated at the predeclared nearest anchor of 60 min, 4.1-minute mismatch disclosed) |
| **Out-of-support cases** | **N = 9** (realised horizons 125.8–288.0 minutes; correctly excluded from FINAL_V2 scientific inference per the 120-minute production boundary, not extrapolated, not hidden — all 9 are rows in `phase2_case_table.csv` with `applicability_status=OUT_OF_SUPPORT`) |
| Forecast target-time mismatch | Single supported case: **15 minutes** (nearest available HRRR valid time vs. the h=60 anchor target) |
| Queue model introduced | **NO** |
| Retain/withdraw recommendation introduced | **NO** |
| FINAL_V2 refitted | **NO** — `final_v2_adapter.py` unchanged from Phase 1 in this respect; still never calls `.fit()` |
| New high-capacity model introduced | **NO** |
| Large uncontrolled archive download | **NO** — zero bytes downloaded; every input already existed in the repository (see `phase2_existing_forecast_evidence_audit.md`) |

## Point-in-time forecast metrics (N=1 — reported, not aggregated)

| Field | Value |
|---|---|
| Case | 2021, car 60 |
| Realised horizon | 64.1 min (evaluated at predeclared nearest anchor, 60 min) |
| Observed Δv | **+4.695 mph** |
| Point-in-time-forecast E[Δv] | +0.0236 mph |
| Point-in-time-forecast 80% PI | [-0.75, +0.82] mph (does not cover the observed value) |
| Absolute error (forecast-based) | 4.67 mph |
| Realised-environment E[Δv] | +0.0451 mph |
| Absolute error (realised-environment) | 4.65 mph |
| Forecast ambient error (forecast − realised) | see `phase2_case_table.csv` `forecast_ambient_error_c` |

**No MAE/RMSE/coverage/directional-accuracy statistic is computed from N=1** — any such number would be either exactly 0% or 100% and would misrepresent a single data point as a distributional result. This is a deliberate omission, not an oversight (specification Step 10: "at minimum calculate where sample size permits").

## Forecast degradation / operational penalty (Step 7 answer, heavily qualified)

For this single case, the forecast-based and realised-environment predictions are close to each other (0.0236 vs. 0.0451 mph) relative to the very large gap between either of them and the actual observed outcome (4.695 mph). **The dominant source of error in this one case is the frozen physical-response model's own residual uncertainty (latent setup/tyre/execution variation), not forecast quality.** This is consistent with the frozen system's own documented position (`indy500_final_v2_system_specification.md`, `docs/technical_challenges.md`-equivalent limitations) that empirical performance residual is the dominant uncertainty source at every horizon. **This single-case observation cannot be generalized** — a genuine estimate of the operational penalty from forecast error, as opposed to model residual uncertainty, would require many more supported-horizon cases than currently exist in this project's evidence base.

## Worst case and why it "failed"

The one scientifically evaluated case is also the only available worst-case example: the frozen model predicted an essentially flat outcome (~0 mph) while the driver's second attempt was +4.695 mph faster. Both the forecast-based and realised-environment (perfect-information) versions of the model missed this by almost the same margin, which is itself informative: **even perfect knowledge of the future ambient temperature would not have caught this case**, because the actual driver of the large speed change was evidently not track/ambient thermal state. This matches the frozen system's own stated scope: it is a conditional physical-performance model, not a complete predictor of qualifying performance.

## Scientific limitations (Phase 2, in addition to Phase 1's)

1. N=1 supported case is not sufficient to estimate forecast-driven operational penalty, error decomposition, or interval calibration in any general sense.
2. All 10 real candidates come from a single year (2021); 2020 is fully excluded (no usable attempt timestamps anywhere in the pipeline's chronology reconstruction for that year), and 2022–2024 transitions were excluded for ambiguous multi-attempt pairing, not a deliberate year-based choice.
3. The single supported case required evaluating at the nearest calibrated anchor (60 min) rather than the exact realised horizon (64.1 min) — a predeclared, disclosed 4.1-minute mismatch, not a new interpolation model.
4. Forecast `issue_time` remains the nominal HRRR cycle time; true publication-latency-adjusted availability remains unquantified (unchanged from Phase 1).

## Design decisions requiring human approval

1. **The Step 5 provenance fix changed `shadow_engine.run_single_horizon`'s call signature** (it now takes an already-selected `ForecastVintage` instead of a `ForecastVintageStore`) and required updating Phase 1's own demo script and two Phase 1 test cases to match. This was necessary to make forecast-selection single-source-of-truth as instructed, and Phase 1's behaviour was re-verified identical afterward (same demo, same numbers), but it is a structural change to Phase 1 code, flagged for visibility even though it was completed without pausing (no scientific ambiguity or frozen-asset risk was involved).
2. **The predeclared "nearest calibrated anchor" rule for car 60** (evaluate at h=60 rather than the realised h=64.1, with the 4.1-minute mismatch disclosed) is a defensible but judgment-based choice. An alternative would have been to exclude this case too (making N=0 for scientific evaluation) rather than accept a 4.1-minute anchor mismatch. Both are defensible; this report used the inclusive choice and disclosed it — worth explicit sign-off given N=1 is otherwise the entire scientific result of Phase 2.
3. **Whether to pursue Phase 2b/expanded evidence acquisition** (more years' worth of usable attempt timestamps, or finer-lead-time HRRR coverage per `historical_forecast_gap_report.md`) to grow beyond N=1 is a decision for you, not started here (Phase 3 is explicitly out of scope for this response regardless).
