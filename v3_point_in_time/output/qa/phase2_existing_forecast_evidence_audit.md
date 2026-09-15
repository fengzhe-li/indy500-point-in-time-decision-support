# Phase 2 Step 1 — Existing Forecast Evidence Audit

Independently re-verifies `historical_forecast_gap_report.md` (Phase 1) against the repository, and extends the search to `data/`, `evidence/`, `tmp/`, and the raw PTSC observation series, which Phase 1's narrower audit did not exhaustively enumerate.

## Candidate sources found

| Source | Years | Issue-time | Valid-time | Variables | Temporal res. | Spatial res. | Forecast or observation? | Usable for point-in-time? |
|---|---|---|---|---|---|---|---|---|
| `weather/output/hrrr_ims_2020_2024_features.csv` | 2020–2024 (5 qualifying days) | **Yes** — real `cycle_time_utc` (nominal HRRR model run) | `valid_time_utc` = cycle + lead hour | 2m temp, dewpoint, 10m wind u/v, gust, pressure, cloud cover, shortwave radiation | Hourly valid-time grid; leads 0–3h from cycles 11Z–23Z | Single point (IMS coordinates) | **Genuine forecast** (NOAA HRRR model output) | **Yes** — this is the only genuine forecast-vintage source in the project |
| `weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv` | 2020–2024 | N/A (observation, not forecast) | N/A | ambient_c, track_c, humidity, wind, pressure, multiple sensor channels | Irregular, ~15 min typical spacing (31–36 obs/day) | Single point (IMS) | **Real observation**, not a forecast | Yes, but only as the *current-state* input (ground truth at/around decision_time), never as a stand-in for a forecast |
| `weather/output/v2_future_track/future_track_samples_with_solar_v1.csv` | 2020–2024 | N/A | N/A | derived track/ambient deltas, solar elevation | Same as PTSC above, paired at 15/30/60/90/120-min offsets | Single point | **Derived from realised observations**, not a forecast | No — Phase 1 initially used this file's "future" columns as if standing in for an evaluation target; on closer inspection each row pairs an observation with a *later observation in the same series*, not with a real subsequent attempt or a forecast. It remains valid for what V2-A actually used it for (fitting/validating the future-track model against realised outcomes), but it is **not** a source of forecast vintages and is **not**, by itself, a table of real attempt-to-attempt transitions (see Step 2). |
| `r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv` | 2020–2024 | N/A | N/A | `delta_four_lap_average_speed_mph` (observed outcome) keyed by `(year, car_number)` | One row per same-car transition (41 rows) | N/A | Observed outcome, not weather | Source of ground-truth `observed_delta_v` for Step 9's case table |
| `pipeline.reconcile.build()` → `tables["attempts"]` | 2020–2024 | `start_time_utc` / `event_time_quality` per attempt | N/A | Attempt timestamps, quality flags | Per-attempt | N/A | Chronology reconstruction | Source of real `decision_time` candidates — see Step 2 for the critical finding that 2020 has **no usable attempt timestamps at all** (`event_time_quality == "UNKNOWN"`, `start_time_utc is None` for every 2020 attempt) |
| `evidence/*.json`, `evidence/*.pdf`, `evidence/hrrr_*.idx` | 2020–2024 | HRRR `.idx` files are GRIB index files, not extracted forecast values | — | — | — | Raw source documents, not structured forecast data | No direct use; the already-extracted `hrrr_ims_2020_2024_features.csv` supersedes these for V3's purposes |
| `data/` (repo root) | — | — | — | Empty of additional weather content (contains only pipeline SQLite/output artifacts already covered by `tests/test_pipeline.py`) | — | — | — | No additional forecast evidence found here |
| `tmp/` | — | — | — | Working-directory scratch content unrelated to weather/forecast data | — | — | — | No additional forecast evidence found here |

## Confirmation of Phase 1's conclusions

Phase 1's `historical_forecast_gap_report.md` conclusion — "genuine historically-available forecast vintages already exist (HRRR), no download needed for the demo, hourly valid-time grid mismatch and unquantified publication latency are real limitations" — is **confirmed** by this broader search. No additional forecast-vintage source was found in `data/`, `evidence/`, or `tmp/`.

## One correction to a Phase 1 assumption

Phase 1's demo (and its inventory doc) treated `future_track_samples_with_solar_v1.csv` rows as usable "real decision points." That remains true for what V2-A used them for (track-state model fitting/validation), but for Phase 2's specific need — a real historical *attempt-to-attempt transition* with a known outcome `Δv` — the correct source is the combination of `pipeline.reconcile.build()`'s `attempts` table (for real attempt timestamps) and `probabilistic_physics_loyo_residuals_v1.csv` (for the matching observed outcome), not this samples file. See `phase2_minimum_data_plan.md` for the resulting case count.
