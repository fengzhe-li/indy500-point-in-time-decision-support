# Attempt-Performance Baseline Ladder V1

Target: `four_lap_average_speed_mph`

Feature set: `ATTEMPT_PERFORMANCE_FEATURE_SET_V1`
Validation protocol: `YEAR_GROUPED_LOYO_V1`
Model policy hash: `599dee972901168e7297d02344e29079cd45fe0f34813db733b15470fcaab806`

## Models

- `MEAN_BASELINE`
- `RIDGE`
- `ELASTIC_NET`
- `RANDOM_FOREST`
- `HIST_GRADIENT_BOOSTING`

## Primary validation

Leave-one-year-out across 2020, 2021, and 2023.

2024 remains sensitivity-only because the supported target subset contains only seven attempts.

## Aggregate result

Best model: `MEAN_BASELINE`
Best pooled primary MAE: `1.654169 mph`
Mean baseline pooled primary MAE: `1.654169 mph`
MAE improvement: `0.000000 mph`
Relative MAE improvement: `0.000%`

## Interpretation boundary

- This is a baseline comparison, not final model selection.
- No hyperparameter tuning was performed.
- No random row split was used for primary evaluation.
- 2022 remains unavailable in the timing-dependent performance-context layer.
- The seven 2024 rows are sensitivity evidence only.

## Readiness

**BASELINE_MODEL_LADDER_COMPLETE**