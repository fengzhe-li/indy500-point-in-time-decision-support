# FINAL_V2 Frozen Results

Status: **FINAL_FROZEN**

## Performance core

- Frozen same-car transitions: **41**
- Reference years contributing retained transitions: **2020, 2021, 2023, 2024**
- No 2022 transition met the final frozen performance-core requirements.

### Frozen coefficients

```text
beta_track   = -0.03482533
beta_ambient = +0.18239338
```

### Leave-one-year-out coefficient stability

| Omitted year | beta_track | beta_ambient |
|---:|---:|---:|
| 2020 | -0.034907 | +0.202992 |
| 2021 | -0.034584 | +0.175674 |
| 2023 | -0.045606 | +0.208781 |
| 2024 | -0.029243 | +0.164000 |

## Future-state model

Retained specification: **M2b** — current thermal gap plus mean future solar state.

Supported calibrated horizons:

```text
15, 30, 60, 90, 120 minutes
```

The 120-minute limit is an empirical model-validation / applicability boundary, not a rule-derived session limit.

### Model-selection summary

Common-sample comparison (`n=611`):

| Model | MAE (°C) |
|---|---:|
| B0 | 3.1442 |
| B1 | 2.4204 |
| M0 | 2.0230 |
| M1 | 1.9719 |
| M2a (+ current rate) | 1.9866 |

Solar comparison, macro MAE:

| Model | MAE (°C) |
|---|---:|
| M1 | 1.9903 |
| M2a delta solar | 2.0981 |
| **M2b mean solar** | **1.9392** |
| M2c both | 1.9845 |

## Future-state conformal calibration

Aggregate empirical coverage:

- nominal 80%: **0.8064**
- nominal 90%: **0.9085**

Aggregate interval widths:

- 80%: **5.6720 °C**
- 90%: **7.7179 °C**

2022 was a difficult held-out regime:

- 80% coverage: **0.6098**
- 90% coverage: **0.6992**

This is treated as an applicability / distribution-shift warning rather than hidden by pooled calibration.

## Final performance uncertainty

| Horizon (min) | 80% PI width (mph) | 90% PI width (mph) |
|---:|---:|---:|
| 15 | 1.4659 | 2.4239 |
| 30 | 1.4751 | 2.4349 |
| 60 | 1.5129 | 2.4620 |
| 90 | 1.5437 | 2.4827 |
| 120 | 1.5666 | 2.4984 |

Empirical attempt-level performance residual variation is the dominant final uncertainty source under ablation.

## 2025 external-regime evaluation

Eligible repeat-attempt cases: **15**

| Metric | Result |
|---|---:|
| MAE | 0.492 mph |
| Median AE | 0.425 mph |
| RMSE | 0.610 mph |
| 80% PI coverage | 80% |
| 90% PI coverage | 100% |
| Directional accuracy | 46.7% |
| Observed improvement rate | 60% |
| Mean predicted P(improve) | 0.535 |

The weak classification separation is retained as a limitation rather than converted into a stronger strategy claim.

## V2-E stress test

Scenario grid:

```text
3 thermal-gap states
x 3 ambient trajectories
x 3 solar states
x 5 horizons
= 135 scenarios
```

At 120 minutes:

- `P(improve)` range: **0.20552–0.67040**
- expected speed-change range: **-0.46298 to +0.22479 mph**

## Frozen system artifacts

Scientific system specification SHA256:

```text
2cb5ce48585938131c91ad0bf9782255c55fa7808b14451a58a7414b4ab8f00d
```

Scientific freeze manifest SHA256:

```text
fe4c35e8c01610757c96e219153820d108c7063c542ed65a09e38dd77e32cf87
```

Operational presentation-layer manifest SHA256:

```text
790c159c33c38f5adeb9245827421f5036f9183337f52ba87ec30b2df29b0a7a
```
