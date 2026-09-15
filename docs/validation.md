# Validation

## Development discipline

The performance and future-state components use out-of-year evaluation to expose transfer risk. Model selection was completed before the 2025 external-regime evaluation. The 2025 cases were not pooled into the frozen 2020–2024 core.

## External 2025 evaluation

The frozen physical-inference chain was evaluated on 15 eligible same-car repeat transitions from the hybrid era.

| Metric | All 15 cases ≤180 min | 4 cases ≤120 min |
|---|---:|---:|
| MAE | 0.4916 mph | 0.2208 mph |
| Median AE | 0.4253 mph | 0.1897 mph |
| RMSE | 0.6095 mph | 0.2692 mph |
| Direction accuracy | 46.7% | 50.0% |
| 80% PI coverage | 80% | 100% |
| 90% PI coverage | 100% | 100% |

The 120–180 minute cases are extended retrospective diagnostics. Production inference remains capped at 120 minutes. The small four-case supported subset cannot establish general calibration.

## Interpretation

Point direction discrimination is weak: cases that improved did not receive meaningfully higher average predicted P(improvement) than cases that declined. Interval behaviour is more useful, with 12/15 outcomes inside the 80% interval and 15/15 inside the 90% interval.

The 100% 90% coverage result is not evidence of perfect long-run calibration. With 15 cases, coverage rates are discrete and uncertain.

## Weather semantics

The backtest uses realized PTSC ambient trajectories. It validates the frozen physical inference conditional on realized environmental evolution, not the accuracy of a live weather forecast available at the earlier decision time.

## Section and regime checks

Section linkage covers 39/41 transitions and supports spatial coherence. Separate 2019 and 2025 fits give qualified evidence that directional physical sensitivity transfers across regimes. Broad 2019 intervals and small samples prevent an invariance claim.

