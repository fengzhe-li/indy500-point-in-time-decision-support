# Repeat-Attempt Delta Context V1

Target:

`current_speed_mph - best_prior_supported_speed_mph`

Rows: `40`
Primary rows (2020/2021/2023): `39`
2024 sensitivity rows: `1`

## Interpretation

The baseline attempt is the highest-speed earlier supported complete attempt for the same car/session.
If multiple prior attempts have exactly the same best speed, the latest such prior attempt is selected deterministically.
The target therefore measures gain/loss relative to the best prior supported performance baseline.

## Weather

Current, baseline-attempt, and current-minus-baseline forecast weather values are preserved.
Wind direction is represented with sin/cos terms rather than direct degree subtraction.

## Boundary

- This is a repeat-attempt performance layer.
- It is not a retain/withdraw decision-state layer.
- It does not infer queue state or decision time.
- 2024 remains sensitivity-only.

## Status

**REPEAT_ATTEMPT_DELTA_CONTEXT_READY**