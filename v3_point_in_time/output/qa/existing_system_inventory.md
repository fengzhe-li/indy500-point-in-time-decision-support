# V3 Step 0 — Existing System Inventory

Scope: locate and understand the frozen FINAL_V2 scientific system before writing any V3 code, per the Phase 1 specification. Nothing in this document changes any existing file.

## 1. Components V3 can reuse directly

| Component | Path | Reuse |
|---|---|---|
| Frozen M2b future-track coefficients (per horizon) | `weather/output/v2_future_track/v2a_full_sample_track_model_coefficients_v1.csv` | Read as plain numbers: `intercept_c, beta_delta_ambient_temp_c, beta_thermal_gap_0_c, beta_solar_elevation_mean_deg` per horizon. Hashed and listed in `v2a_freeze_manifest_v1.json["artifact_hashes_sha256"]`, so this is an official frozen artifact, not a side effect. |
| Frozen track-residual pool | `weather/output/v2_future_track/future_track_residuals_v1.csv` | Filtered to `model == "M2b_mean_solar"` and `horizon_min == h`, column `residual_c`. Same pool the frozen MC script draws from. |
| Frozen performance-core bootstrap draws | `r5_2/manual/probabilistic_physics_coefficient_bootstrap_v1.csv` | 5000 paired `(beta_track_temp, beta_ambient_temp)` rows — drawn by row index to preserve joint correlation, exactly as the frozen script requires. |
| Frozen performance-residual pool | `r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv` | Column `residual_loyo_centered`. |
| Pure helper functions `symmetrized_draws_from_values`, `summarize_draws` | `weather/scripts/v2_integrate_track_to_performance_mc.py` | Imported directly (via `importlib`, by file path — this script is not a package) and called unmodified. This is the actual reused Monte Carlo mechanics; V3 does not retype this math. |
| Pure solar-geometry function `solar_elevation_deg` + `LATITUDE_DEG`/`LONGITUDE_DEG` | `weather/scripts/v2_add_solar_features.py` | Imported directly and called unmodified. `solar_elevation_mean_deg = (solar_elevation_deg(t0) + solar_elevation_deg(t0+h)) / 2`, matching the frozen feature construction exactly. |
| Applicability boundary text | `weather/output/final_integration/applicability_gate_v2.md`, `weather/output/operational_curve_v2/operational_curve_metadata_v2.json` | Read for the exact supported-horizon / non-extrapolation rules the V3 applicability gate must mirror (see §7 below — some thresholds are explicitly **not** numerically defined beyond horizon support and are reported as such, not invented). |
| Real historical current-state rows | `weather/output/v2_future_track/future_track_samples_with_solar_v1.csv` | Used only to source a genuine (non-fabricated) `current_track_temp_c` / `current_ambient_temp_c` / `t0_utc` for the Step 12 demonstration. |
| Real historical HRRR forecast cycles | `weather/output/hrrr_ims_2020_2024_features.csv` | Used only to source a genuine (non-fabricated) forecast vintage (`cycle_time_utc` = issue time, `valid_time_utc`, `temp_c`) for the Step 12 demonstration. |

None of the above files are modified. V3 code only opens them for reading.

## 2. Components that require an adapter (cannot be called as-is)

`weather/scripts/v2_integrate_track_to_performance_mc.py` is a **batch script**, not an importable single-scenario function: its `main()` reads a fixed pre-built samples file, refits `LinearRegression` on the *full* sample per horizon (a deterministic, already-frozen-and-hashed result — see §3), loops over every row of that file, and **overwrites its own hardcoded output paths**. Calling `main()` directly would (a) not accept a new point-in-time scenario at all, and (b) violate "do not overwrite existing frozen outputs."

`final_v2_adapter.py` (new, in V3) is therefore a genuine adapter: it loads the same frozen numeric artifacts listed in §1, reuses the same two pure helper functions from that script unmodified, and evaluates the same closed-form Monte Carlo formula documented in `indy500_final_v2_system_specification.md` §9 for a single new snapshot instead of the pre-built row set. No coefficient, residual pool, or bootstrap draw is refit, resampled from new data, or altered.

## 3. Components that must remain immutable

Everything under:
- `r5_2/manual/` (physics-core bootstrap + LOYO residuals)
- `weather/output/v2_future_track/`, `v2b_section_mechanism/`, `v2c_wind_diagnostic/`, `v2d_uncertainty_ablation/`, `v2e_scenario_stress_test/`, `final_integration/`
- `weather/output/operational_curve_v2/` (including `freeze/`)
- `results/final_v2/`
- `docs/final_v2_system_specification.md`
- All `weather/scripts/*.py` (read/imported, never edited)

These are exactly the files hashed before Step 1 and re-hashed after Phase 1 implementation (see `v2_immutability_report.txt`).

**Important nuance on "the M2b coefficients are a full-sample refit":** `v2_integrate_track_to_performance_mc.py` does call `LinearRegression().fit()` when it originally ran — but that run already happened, is frozen, hashed, and listed in `v2a_freeze_manifest_v1.json`. V3 never calls `.fit()` again; it only reads the five rows of already-fitted coefficients from the frozen CSV. This is loading a frozen result, not refitting FINAL_V2.

## 4. What historical forecast data already exists

`weather/output/hrrr_ims_2020_2024_features.csv` contains real NOAA HRRR model output for 2020–2024, at Indianapolis Motor Speedway's coordinates, with genuine forecast-cycle structure:

- `cycle_time_utc` — the HRRR model run ("cycle") time. **This is a real issue-time field.**
- `forecast_hour` / `forecast_lead_hours` — lead time from the cycle (this extract covers leads 0–3 hours only, cycles 11Z–23Z, per `pipeline/parsers/weather.py`'s own QA expectation `{(cycle,lead) for cycle in range(11,24) for lead in range(4)}`).
- `valid_time_utc` — the timestamp the forecast is *for* (`cycle_time_utc + forecast_hour` hours).

So: **yes, genuine historically-available forecast vintages already exist in this project**, with a real issue time distinct from the valid time. No download was needed for Phase 1.

## 5. Whether forecast issue/vintage timestamps exist — the important caveat

`pipeline/parsers/weather.py::build_snapshot` sets:
```python
"issue_time_utc": row["cycle_time_utc"],
"availability_time_utc": None,
"availability_time_quality": "UNKNOWN",
"extraction_metadata_json": {..., "availability_status": "POLICY_REQUIRED", ...}
```
`issue_time_utc` (the nominal HRRR cycle time) **is populated and reliable as a nominal model-run timestamp.** But the pipeline's own tests (`tests/test_pipeline.py::test_hrrr_cycle_valid_and_availability_are_distinct`) explicitly assert that **real-world publication/availability latency is unknown** — HRRR cycles are not actually downloadable at the instant of their nominal cycle time; there is real-world processing and distribution delay (typically on the order of an hour or more), and this project has deliberately never asserted a number for it (`availability_status: POLICY_REQUIRED`, not a defined value).

**Consequence for V3's leakage guard:** V3 uses `issue_time_utc` (= nominal cycle time) as the conservative `forecast.issue_time` check required by the specification (`forecast.issue_time <= decision_time`). This is the only timestamp that exists. It is documented here, in the guard's own docstring, and in the QA report as a **known, named limitation**: the guard proves "not-issued-after-decision-time" against the *nominal* cycle time, not against the (unknown) real publication time. If real HRRR publication latency is later quantified, the guard should be tightened by that margin. This is exactly the kind of threshold the specification says must be reported as **NOT YET DEFINED** rather than invented — so V3 does not fabricate a latency margin.

## 6. Additional data that would be required for *true* end-to-end point-in-time evaluation

- A quantified HRRR (or equivalent) publication-latency figure, so `available_at` can be distinguished from nominal `issue_time` (see §5).
- Forecast vintages at finer-than-hourly valid-time resolution, or an interpolation policy, since V2's calibrated horizons (15/30/60/90/120 min) do not all land on HRRR's hourly valid-time grid — see `historical_forecast_gap_report.md` for the concrete sizing of this gap.
- A real "current official result known_at" timestamp series (when a four-lap average became officially known) distinct from the attempt's own timing — the existing `pipeline` chronology tables carry attempt timing but no explicit "official result publication time" field; V3's guard therefore currently accepts a caller-supplied `known_at` for the current official speed and documents this as an input, not something V3 derives on its own.

## 7. Applicability / support thresholds already defined vs. not yet defined

Already defined by the frozen system (V3 reuses these exactly, does not invent new ones):
- Supported horizons: exactly 15, 30, 60, 90, 120 minutes (`v2a_freeze_manifest_v1.json`, `operational_curve_metadata_v2.json`).
- `extrapolation_above_120: false` — horizons above 120 minutes are explicitly out of production support.
- The operational curve's own intermediate-minute values (between anchors) are explicitly labelled "piecewise-linear operational interpolation; not independently calibrated" — V3's applicability gate treats a request for a non-anchor horizon the same way the frozen system already does (`CALIBRATED_ANCHOR` vs `INTERPOLATED_OPERATIONAL` vs `CURRENT_STATE_BOUNDARY`), rather than inventing a new interpolation policy.

Not yet defined anywhere in the frozen system (V3 reports these as `NOT_YET_DEFINED`, does not invent a threshold):
- A numeric "historical support range" boundary for `current_track_temp_c` / `current_ambient_temp_c` / `thermal_gap_0_c` inputs (i.e., an explicit out-of-distribution check on the *current* physical state, as opposed to the ambient-trajectory support check already done for V2-E's scenario grid). V2-E checked that its *scenario* ambient trajectories stayed within each horizon's historical range, but did not publish a reusable numeric boundary for arbitrary future current-state inputs.
- A quantified HRRR publication-latency margin (§5).

## Files inspected for this report

`indy500_final_v2_system_specification.md`, `indy500_final_v2_freeze_manifest.json`, `indy500_final_project_freeze_manifest_v1.json`, `v2a_freeze_manifest_v1.json`, `v2d_freeze_manifest_v1.json`, `v2e_freeze_manifest_v1.json`, `operational_performance_curve_v2.csv`, `operational_curve_metadata_v2.json`, `operational_curve_v2_freeze_manifest.json`, `v2_build_future_track_samples.py`, `v2_add_solar_features.py`, `v2_integrate_track_to_performance_mc.py`, `v2_future_track_conformal_calibration.py` (both copies — identical logic, one reformatted), `pipeline/parsers/weather.py`, `tests/test_pipeline.py`, `final_v2_freeze.py` (hashing convention: plain `hashlib.sha256` over file bytes — V3's `hashing.py` follows the same convention).
