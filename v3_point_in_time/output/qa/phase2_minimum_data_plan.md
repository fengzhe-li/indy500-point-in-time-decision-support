# Phase 2 Step 2 — Minimum Defensible Data Requirement

## Method

For each of the 41 frozen same-car transitions (`r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv`, keyed by `year, car_number`), the real attempt timeline was reconstructed via `pipeline.reconcile.build()` (the same pipeline `tests/test_pipeline.py` already exercises — no pipeline code was modified). A transition was accepted as a **defensible point-in-time case** only if all of the following hold, with no fabricated or inferred value:

1. The car has **exactly two** attempts in that session (so the transition is unambiguous — no need to guess which of 3+ attempts a loyo row corresponds to).
2. **Both** attempts have a real, non-null `start_time_utc` in the pipeline's `attempts` table (`event_time_quality` other than `UNKNOWN`).
3. A real observed track/ambient reading exists at or before the first attempt's `start_time_utc` (`weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv`), used as `current_track_temp_c` / `current_ambient_temp_c` — never inferred or interpolated across a gap.

No timestamp was manufactured. No missing forecast was filled with realised weather. No case was force-included to reach a target sample size.

## Result

| Outcome | Count |
|---|---|
| Total frozen same-car transitions | 41 |
| Excluded — car has 3 or 4 attempts (ambiguous which pair the loyo row is) | 18 |
| Excluded — one or both attempts have no usable timestamp | 13 (**all 9 of the 2020 transitions** fall here: every 2020 attempt has `event_time_quality == "UNKNOWN"`, no `start_time_utc`; the remaining 4 are from other years) | 
| **Defensible candidate cases** | **10** |

**All 10 defensible candidates are from 2021.** None come from 2020, 2022, 2023, or 2024 — not because those years were skipped, but because none of their remaining transitions satisfied the unambiguous-pair-plus-real-timestamp requirement above. This is reported honestly rather than adjusted to look more balanced across years.

## The 10 candidates and their realised horizons

| Year | Car | Decision time t0 (UTC) | Realised attempt t1 (UTC) | Realised horizon (min) | Track/ambient reading gap before t0 (min) | Observed Δv (mph) |
|---|---|---|---|---|---|---|
| 2021 | 12 | 17:21:36 | 21:33:54 | 252.3 | 6.6 | +0.176 |
| 2021 | 18 | 16:19:56 | 21:07:57 | 288.0 | 4.9 | +0.798 |
| 2021 | 2  | 16:39:06 | 18:44:56 | 125.8 | 9.1 | +0.022 |
| 2021 | 21 | 16:43:16 | 18:49:55 | 126.7 | 13.3 | +0.642 |
| 2021 | 26 | 18:12:27 | 20:25:16 | 132.8 | 12.5 | −1.419 |
| 2021 | 4  | 17:44:56 | 21:46:39 | 241.7 | 14.9 | −0.927 |
| 2021 | 47 | 17:49:06 | 19:55:55 | 126.8 | 4.1 | −0.154 |
| 2021 | **60** | **17:58:16** | **19:02:24** | **64.1** | 13.3 | **+4.695** |
| 2021 | 7  | 17:35:46 | 21:21:31 | 225.8 | 5.8 | +0.246 |
| 2021 | 86 | 17:11:36 | 21:02:45 | 231.2 | 11.6 | −0.154 |

## Critical finding: realised horizons mostly exceed FINAL_V2's 120-minute production boundary

**9 of the 10** candidates have a realised horizon **above 120 minutes** (125.8–288.0 min). Per the frozen system's own applicability boundary (`operational_curve_metadata_v2.json`: `extrapolation_above_120: false`) and this specification's explicit instruction not to extend production support beyond 120 minutes, **these 9 cases cannot receive FINAL_V2 scientific inference at their realised horizon.** They are retained in the Phase 2 case table as `OUT_OF_SUPPORT` records (Step 13: failures/exclusions must be shown, not hidden), not silently dropped.

**Only car 60's transition** (realised horizon 64.1 minutes) falls close to a calibrated anchor (60 minutes, 4.1-minute mismatch). This is the **only case Phase 2 can evaluate scientifically** without extrapolating or inventing a new horizon model.

## Consequence for sample size

The genuinely defensible **scientific evaluation sample size for Phase 2 is N=1** (car 60, 2021). This is far too small to compute meaningful aggregate error/coverage statistics (Step 10). Per the specification's explicit instruction ("a smaller, defensible point-in-time sample is preferable to a larger, poorly reconstructed sample" / "a negative feasibility result is preferable to invalid evaluation"), Phase 2 proceeds with this single real case, reports it as illustrative only, and does not compute or present MAE/RMSE/coverage statistics that would be meaningless at N=1.

The other 9 real, non-fabricated candidates remain valuable evidence for a different reason: they demonstrate that FINAL_V2's 120-minute production boundary is not an abstract caution but an **empirically frequent** constraint — most real qualifying-session transitions in this dataset simply do not recur within the calibrated window.

## No new data acquisition required

Every input needed for the 10-case table (decision time, current physical state, realised outcome, and — per `phase2_existing_forecast_evidence_audit.md` — a real HRRR forecast vintage for the point-in-time comparison) already exists in the repository. **No download is proposed or performed for Phase 2.**
