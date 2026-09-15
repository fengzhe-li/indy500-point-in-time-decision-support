# Data dictionary

The project contains several interfaces rather than one modelling table. Column names vary across frozen phases; this guide defines the scientific meaning of the central fields.

## Attempt and transition identity

| Field family | Meaning |
|---|---|
| `attempt_id`, `before_attempt_id`, `after_attempt_id` | Stable canonical identifiers for an attempt or transition endpoints |
| `year`, `car_number`, `driver_name` | Event and entry identity; car number is conceptually a string |
| `four_lap_average_speed_mph` | Official complete-attempt result |
| `delta_four_lap_average_speed_mph`, `delta_speed_mph` | After-minus-before four-lap average |
| `before_time_utc`, `after_time_utc` | Reconstructed attempt timestamps with associated lineage |
| `actual_wait_min` | Elapsed endpoint time in the external backtest; not a general queue-wait label |

## Physical state

| Field family | Unit | Meaning |
|---|---:|---|
| `track_temp_c` | °C | Structured observed track-temperature state |
| `ambient_temp_c`, `air_temp_c` | °C | Ambient temperature |
| `delta_track_temp_c` | °C | After-minus-before track temperature |
| `delta_air_temp_c`, `delta_ambient_temp_c` | °C | After-minus-before ambient temperature |
| `thermal_gap_0_c` | °C | Current track minus ambient temperature |
| `solar_elevation_mean_deg` | degrees | Deterministic geometry proxy over a future interval |
| wind/gust fields | m/s | Diagnostic fixed-point or gridded proxies, absent from the production mean model |

## Future-state interface

| Field | Meaning |
|---|---|
| `horizon_min` | Conditional future opportunity horizon |
| `model_expected_delta_track_temp_c` | Expected future track-temperature change |
| `track_residual_mode` | Residual uncertainty source used in retrospective inference |
| `CALIBRATED_ANCHOR` | Scientifically fitted/calibrated horizon |
| `INTERPOLATED_OPERATIONAL` | Presentation interpolation between anchors |
| `CURRENT_STATE_BOUNDARY` | Zero-horizon identity state |

## Predictive output

| Field family | Meaning |
|---|---|
| `model_expected_delta_speed_mph` | Mean conditional speed-change prediction |
| `model_median_delta_speed_mph` | Median conditional speed-change prediction |
| `lower_80_mph`, `upper_80_mph` | 80% predictive interval |
| `lower_90_mph`, `upper_90_mph` | 90% predictive interval |
| `p_improve` | Conditional probability that Δspeed exceeds zero |

## Evidence semantics

Provenance, linkage status, coverage and eligibility fields control whether a value is measured, reconstructed, diagnostic, model-ready or quarantined. Missing operational state must not be inferred from a blank status. Section rows remain repeated diagnostics inside one transition. Historical elapsed intervals do not become queue waits without direct evidence.

