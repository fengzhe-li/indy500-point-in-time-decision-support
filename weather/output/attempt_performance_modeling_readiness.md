# Attempt-Performance Modeling Readiness Audit

Target: `four_lap_average_speed_mph`

Input rows: 136
Rows with target: 123

## Hard leakage exclusions

- `attempt_class`
- `four_lap_average_speed_mph`
- `four_lap_total_seconds`
- `result_counted_at_session_end`
- `result_status`
- `speed_change_vs_best_prior_supported_mph`
- `speed_change_vs_prior_supported_attempt_mph`

## Baseline V1 candidate features

- `forecast_temp_c`
- `forecast_dewpoint_c`
- `forecast_relative_humidity_pct`
- `forecast_wind_speed_10m_ms`
- `forecast_wind_direction_deg`
- `forecast_pressure_hpa`
- `forecast_gust_ms`
- `forecast_cloud_cover_pct`
- `forecast_shortwave_radiation_wm2`
- `prior_supported_attempt_count`
- `seconds_since_prior_supported_attempt`
- `prior_supported_attempt_average_speed_mph`
- `prior_supported_attempt_total_seconds`
- `best_prior_supported_average_speed_mph`
- `best_prior_supported_total_seconds`
- `car_attempt_index`

## Modeling policy

- Raw HRRR fields are retained for QA but excluded from V1 when a deterministic derived equivalent exists.
- Current-attempt result/status/performance derivatives are excluded from predictors.
- Prior supported same-car performance is allowed because it precedes the current supported attempt timestamp.
- Missing prior-history values are structural for first supported attempts and must be handled explicitly.
- `car_number` is not included in the first baseline to reduce identity memorization / overfitting.
- 2022 is absent from this performance-context layer because no trustworthy attempt-time bridge exists.
- 2024 contributes only the seven supported timing rows; year-level validation must therefore be interpreted cautiously.

## Validation recommendation

Use year-grouped validation rather than random row splitting. The primary evaluation should test generalization across years, with special caution around the very small 2024 supported subset.

## Readiness

**ATTEMPT_PERFORMANCE_MODELING_READY_FOR_BASELINE_DESIGN**