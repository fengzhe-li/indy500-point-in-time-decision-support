# Repeat-Attempt Delta Baseline Ladder V1

Primary rows: `39`
Target: `target_speed_delta_vs_best_prior_mph`

## Reference baseline

`ZERO_DELTA_BASELINE` assumes the next attempt matches the best prior supported speed.
Primary pooled MAE: `0.563846 mph`

## Aggregate result

Best model: `ZERO_DELTA_BASELINE`
Best pooled MAE: `0.563846 mph`
Improvement vs zero-delta baseline: `0.000000 mph`
Relative improvement: `0.000%`

## Interpretation boundary

- This predicts repeat-attempt performance delta only.
- It does not model queue waiting.
- It does not yet produce retain/withdraw expected utility.
- 2024 has one supported row and is sensitivity-only.
- No hyperparameter search was performed.

## Status

**REPEAT_DELTA_BASELINE_LADDER_COMPLETE**