# Model card: FINAL_V2

| Item | Definition |
|---|---|
| Intended use | Conditional physical-performance outlook for a supplied future opportunity horizon |
| Response | Change in official four-lap average speed relative to the current result |
| Reference era | 2020–2024 Aeroscreen, pre-hybrid Indianapolis 500 qualifying |
| Core evidence | 41 evidence-qualified same-car transitions |
| Scientific horizons | 15, 30, 60, 90, 120 minutes |
| Outputs | Expected/median Δspeed, 80%/90% PI, P(improvement), future track state |
| Validation | Leave-one-year-out development analysis; 2025 external-regime retrospective evaluation |
| Status | Frozen scientific core; operational display frozen separately |

## Intended interpretation

`p(Δv | H = h)` describes the performance distribution conditional on another on-track opportunity occurring at horizon `h`. It can inform a pit-wall discussion when combined with live operational evidence.

## Unsupported uses

- predicting queue duration or attempt availability;
- choosing Lane 1 or Lane 2;
- recommending retain, withdraw or reattempt actions;
- treating P(improvement) as an overall strategy-success probability;
- extrapolating beyond 120 minutes for production use;
- treating minute-level interpolation as independently calibrated inference;
- assuming coefficients are invariant across technical eras.

## Model components

The physical response is a robust zero-intercept regression on track- and ambient-temperature changes. The future-state model is horizon-specific M2b. Predictive uncertainty combines paired coefficient bootstrap draws, future track-state residual uncertainty and empirical performance residuals.

## Performance

The 15-case 2025 external evaluation reports MAE 0.492 mph, median AE 0.425 mph, RMSE 0.610 mph, 80% PI coverage 80%, 90% PI coverage 100%, and directional accuracy 46.7%. Only four cases are within the ≤120-minute production boundary. These empirical rates are descriptive for small samples.

## Known risks

The dataset is small. Latent run state dominates interval width. Future track-state coverage is weaker in 2022. Historical wind proxies are incomplete representations of aerodynamic exposure. The external evaluation uses realized ambient paths and therefore does not test forecast-provider error.

## Governance

FINAL_V2 artefacts and manifests are immutable inputs to the public presentation layer. New data must enter a separately versioned study; it cannot silently alter frozen parameters or validation cases.

