# Attempt-Performance Residual / Stability Diagnosis V1

Aggregate-best Phase 5B-0 model: `MEAN_BASELINE`

## Year-level target structure

- Primary year mean range: `3.046793 mph`
- Descriptive year eta-squared: `0.352766`
- Maximum absolute Mean-Baseline year bias: `2.703198 mph`

The eta-squared quantity is descriptive only. It measures observed target variation associated with year-level mean differences.

## Prior-speed persistence

- Repeat target rows: `40`
- Correlation current vs best prior speed: `0.905112`
- Naive best-prior-speed MAE on repeat rows: `0.552425 mph`

This is diagnostic evidence only, not a promoted model.

## Interpretation boundary

- No new predictive model was trained.
- No hyperparameter tuning was performed.
- No feature or target definition was changed.
- Car identity is descriptive only.
- 2024 remains sensitivity-only.

## Status

**RESIDUAL_STABILITY_DIAGNOSIS_COMPLETE**