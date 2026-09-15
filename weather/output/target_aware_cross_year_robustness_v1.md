# Target-Aware Cross-Year Robustness V1

Policy hash: `540fe455f49d9f77e8ee762467f460dc9c7134929a88d1ddad761ddd869771a1`

## Validation protocol

Leave one primary year out at a time: 2020, 2021, and 2023.

For each training subset, recompute:

- empirical normal performance target rates;
- empirical recovery-like target rates;
- baseline-conditioned Beta recovery posterior;
- resulting target-success probability conditional on completion.

No model is retrained and no historical leaderboard target is introduced.

## Stability

- Maximum absolute deviation from full-data target probability: `0.102381`
- Maximum LOYO probability range: `0.151282`

These values quantify year sensitivity caused by the small repeat-attempt sample.

## Interpretation boundary

- LOYO is a robustness diagnostic, not a new model-selection exercise.
- Recovery events remain sparse.
- Large deviations must be reported rather than tuned away.
- No recommendation is enabled.

## Status

**TARGET_AWARE_CROSS_YEAR_ROBUSTNESS_COMPLETE**