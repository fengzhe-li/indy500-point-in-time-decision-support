# Attempt-Performance V1 Design Freeze

Feature set ID: `ATTEMPT_PERFORMANCE_FEATURE_SET_V1`
Feature set hash: `f67c11b217f60b67868ddafd050d5a900f708364de2f3d0e10e7b4e10e749fa4`

Validation protocol ID: `YEAR_GROUPED_LOYO_V1`
Validation protocol hash: `4f26fae389c94fb9756cb1fb004a3c515130f9089dbc31516414eebbe182f812`

## Target

`four_lap_average_speed_mph`

## Frozen V1 features

- `forecast_temp_c`
- `forecast_relative_humidity_pct`
- `forecast_wind_speed_10m_ms`
- `forecast_wind_direction_sin`
- `forecast_wind_direction_cos`
- `forecast_pressure_hpa`
- `forecast_cloud_cover_pct`
- `forecast_shortwave_radiation_wm2`
- `prior_supported_attempt_count`
- `seconds_since_prior_supported_attempt`
- `best_prior_supported_average_speed_mph`
- `has_prior_supported_attempt`

## Structural missingness policy

- First supported attempts have no prior-attempt history.
- `seconds_since_prior_supported_attempt` is set to 0 only when `has_prior_supported_attempt = 0`.
- `best_prior_supported_average_speed_mph` is set to 0 only when `has_prior_supported_attempt = 0`.
- The explicit indicator prevents those zeros from being interpreted as ordinary physical values.

## Validation

- Primary evaluation: leave-one-year-out over 2020, 2021, and 2023.
- 2024 is a sensitivity-only tiny holdout because only seven supported target rows are available.
- Random row split is not the primary validation method.

## Excluded from V1

- `forecast_dewpoint_c`
- `forecast_gust_ms`
- `car_attempt_index`
- `prior_supported_attempt_average_speed_mph`
- `prior_supported_attempt_total_seconds`
- `best_prior_supported_total_seconds`
- `attempt_class`
- `result_status`
- `result_counted_at_session_end`
- `four_lap_total_seconds`
- `speed_change_vs_prior_supported_attempt_mph`
- `speed_change_vs_best_prior_supported_mph`

## Readiness

**ATTEMPT_PERFORMANCE_V1_DESIGN_FROZEN**