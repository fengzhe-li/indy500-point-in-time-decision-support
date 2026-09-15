# V3 Step 13 — Historical Forecast-Vintage Gap Report

## Headline finding

**Genuine historically-available forecast vintages already exist in this project.** No download was performed or is recommended for Phase 1. This report documents the real coverage that exists, its limitations, and what a *defensible, small* future acquisition would look like if Phase 2 needs finer coverage — it does not request or begin that acquisition.

## What already exists

`weather/output/hrrr_ims_2020_2024_features.csv` (84 KB, 259 rows) — real NOAA HRRR model output at Indianapolis Motor Speedway's coordinates (39.7950, -86.2348), for qualifying-weekend windows across 2020–2024.

- **Required variables present:** 2 m temperature, dewpoint, 10 m wind components, surface gust, surface pressure, total cloud cover, downward shortwave radiation — i.e. everything the frozen V2-A future-track model and this V3 adapter actually use (`ambient_temp_c` for the M2b delta-ambient feature) plus several more that V3's schema optionally supports but the retained model does not require (§ "Do not invent new predictors").
- **Required years present:** 2020, 2021, 2022, 2023, 2024 — matches `CORE_PERFORMANCE_YEARS` used by the frozen physics core.
- **Required timestamps present:** real `cycle_time_utc` (nominal forecast issue/run time) and `valid_time_utc` (what the forecast is for), with `forecast_hour`/`forecast_lead_hours` — a genuine issue-vs-valid distinction, confirmed by direct inspection (see `existing_system_inventory.md` §4–5).

## Coverage limits (existing, not hypothetical)

1. **Lead-time window is narrow.** This extract covers only forecast hours 0–3 from cycles 11Z–23Z each qualifying day (`pipeline/parsers/weather.py`'s own QA expectation: `{(cycle,lead) for cycle in range(11,24) for lead in range(4)}`). It supports short-lead, same-day point-in-time queries well; it cannot supply a forecast issued, say, 20+ hours before a decision time.
2. **Valid-time grid is hourly; V2's horizons are not.** Calibrated horizons are 15/30/60/90/120 minutes, but HRRR valid times land on the hour. A decision time not itself on the hour (the realistic case) means the nearest available forecast for a 15- or 90-minute-ahead target can be up to ~30 minutes off from the exact target time. `forecast_vintage_store.py` records this as `valid_time_error_minutes` on every selection rather than hiding it; the Step 12 demonstration shows real values of 15–30 minutes across the five horizons for its one worked case.
3. **Issue-time is nominal, not a proven availability time.** `issue_time_utc` = the HRRR cycle time, not a measured "this was downloadable at this instant" timestamp. Real HRRR publication latency after the nominal cycle time is not quantified anywhere in this project (`availability_time_quality: "UNKNOWN"`, `availability_status: "POLICY_REQUIRED"` in the pipeline's own schema). V3's guard is conservative in the sense that it never selects a forecast whose *nominal* cycle is after decision_time, but it cannot currently prove the forecast bytes existed publicly by decision_time to a finer tolerance than "the nominal cycle hour."
4. **No pre-day / multi-day-ahead history.** Only the qualifying-day windows above were extracted; there is no archive of days-ahead forecast vintages for the same events.

## Smallest defensible acquisition strategy (if Phase 2 needs it — not started here)

If a future phase needs finer valid-time resolution or a real availability-latency figure, the smallest defensible next step would be:

- Re-pull the **same 5 qualifying days, same site, same 2020–2024 seasons**, but request **all lead hours 0–18** (not just 0–3) from the **same HRRR analysis/forecast archive** already in use (e.g. NOAA's HRRR archive on AWS/NCEP), so valid times can bracket every calibrated horizon (15/30/60/90/120 min) more tightly from multiple cycles.
- This is on the order of **tens of MB, not hundreds of GB** — the existing extract is 84 KB for a handful of variables at one point location across 5 lead hours × 5 days; extending to ~19 lead hours for the same 5 single-point days is still a few MB at most, since HRRR point extraction (not full-grid download) is what this project already does.
- **Recommended source:** the same NOAA HRRR archive the existing pipeline already draws from (point/column extraction at a single lat/lon, not full CONUS grids), which is what keeps this small.
- A real availability-latency figure would additionally require consulting NOAA/NCEP's own published HRRR production-and-dissemination timing documentation, or empirically timestamping when archived files actually became retrievable — this is a research task, not a download-size question, and is explicitly deferred.

## What this report does NOT recommend

- Downloading hundreds of GB of raw HRRR grids: explicitly out of scope for Phase 1, and unnecessary for this project's single-point, single-site use case regardless of phase.
- Expanding calibrated horizons or extrapolating production inference beyond 120 minutes to compensate for coverage gaps.
- Fabricating an availability-latency number in place of the real one that does not yet exist.

## Conclusion

Phase 1's demonstration (Step 12) uses the real coverage above end to end, with every valid-time mismatch disclosed rather than hidden. No archive acquisition is required to complete Phase 1. Any future widening of lead-hour coverage remains a small (single-digit-MB), point-extraction request against the same source already in use — a decision for a later phase, not this report.
