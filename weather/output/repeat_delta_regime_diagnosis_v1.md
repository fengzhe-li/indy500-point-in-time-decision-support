# Repeat-Delta Regime Diagnosis V1

Primary rows: `39`

## Robust target structure

- Median delta: `0.174000 mph`
- IQR: `0.461000 mph`
- Tukey upper threshold: `1.122000 mph`
- MAD-based upper threshold: `1.179203 mph`
- Diagnostic combined threshold: `1.179203 mph`
- Diagnostic large-gain rows: `4`

The large-gain label is diagnostic only. It is not yet a frozen predictive class.

## Baseline recovery diagnostic

- Year-centered baseline-speed Pearson correlation with delta: `-0.698657`
- Year-centered baseline-speed Spearman correlation with delta: `-0.220636`
- Mean delta below year-median baseline: `0.682778 mph`
- Mean delta at/above year-median baseline: `0.108762 mph`

## Interpretation boundary

- No predictive model was trained.
- No outlier was deleted.
- No target row was excluded from the frozen delta layer.
- Large-gain thresholds are sensitivity diagnostics only.
- 2024 remains outside primary regime conclusions.

## Status

**REPEAT_DELTA_REGIME_DIAGNOSIS_COMPLETE**