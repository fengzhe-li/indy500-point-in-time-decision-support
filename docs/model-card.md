# Model Card — FINAL_V2

## Purpose

Conditional physical-performance inference for repeat Indianapolis 500 qualifying opportunities.

The model is designed to answer a conditional question: if another qualifying opportunity occurs at a specified future horizon, how might the car's four-lap qualifying performance change relative to its current official result?

## Scientific target

`p(Δv | H = h)`

This is not a model of `P(H=h)` and is not an autonomous withdraw/retain strategy policy.

## Frozen reference regime

- Reference years: **2020–2024**
- Frozen evidence-qualified same-car transitions: **41**
- Performance form: zero-intercept thermal-response model
- Calibrated future horizons: **15 / 30 / 60 / 90 / 120 min**

## Core response model

`Δv = β_track ΔT_track + β_ambient ΔT_ambient + ε`

Frozen coefficients:

- `β_track = -0.03482533`
- `β_ambient = +0.18239338`

The ambient coefficient is interpreted conditionally rather than as an invariant causal parameter.

## Operational inputs

The complete inference chain is built around information that can be available at decision time, including:

- current official four-lap speed;
- current track-surface temperature;
- current ambient temperature;
- current thermal gap (`T_track - T_ambient`);
- future opportunity horizon;
- future ambient trajectory;
- future solar state used through the track-state pathway.

Other environmental variables may be retained for diagnostics or future extensions without being promoted automatically into the frozen production model.

## Outputs

At supported horizons the system can produce:

- expected physical `Δspeed`;
- median physical `Δspeed`;
- predictive intervals;
- `P(Δspeed > 0)`;
- expected future four-lap speed relative to the current official result.

## Future track-state component

The retained future-track model conditions track-temperature evolution on horizon, future ambient change, the current track-air thermal gap and mean future solar state.

Solar affects performance through the physical track-state pathway; it is not a direct speed feature.

## Uncertainty treatment

FINAL_V2 propagates multiple uncertainty sources rather than presenting a single deterministic point forecast:

1. bootstrap uncertainty in the frozen performance coefficients;
2. uncertainty in future physical track state, calibrated by horizon;
3. empirical unexplained same-car attempt-level performance variation.

The empirical performance residual is the dominant source of final predictive width in the V2-D ablation. That result is treated as sensitivity/ablation evidence rather than a strict variance decomposition.

## Validation

Historical validation includes leave-one-year-out diagnostics and interval calibration.

External evaluation applies the frozen 2020–2024 reference core to later 2025 hybrid-era evidence without refitting the reference model.

Selected 2025 end-to-end metrics:

| Metric | Value |
|---|---:|
| Cases | 15 |
| MAE | 0.492 mph |
| Median absolute error | 0.425 mph |
| RMSE | 0.610 mph |
| 80% PI coverage | 80.0% |
| 90% PI coverage | 100.0% |
| Directional accuracy | 46.7% |

The weak directional accuracy is retained as an explicit limitation. The system is not positioned as a deterministic next-attempt classifier.

## Technical-regime transfer

Three technical periods were investigated:

- **2018–2019:** pre-Aeroscreen evidence; 2019 provides a small clean quantitative comparison sample;
- **2020–2024:** Aeroscreen / pre-hybrid frozen reference regime;
- **2025–2026:** hybrid-era / later-regime analysis, with 2025 supporting quantitative external comparison and 2026 retained mainly as a qualifying-format/applicability boundary case.

Coefficient stability across eras is investigated but invariance is not claimed.

## Known limitations

- Queue timing is not predicted.
- Lane choice is not recommended.
- Team intent is not inferred.
- Weather-forecast error is not fully validated by realised-environment external evaluation.
- The frozen core is small because evidence-quality and same-car comparability rules are deliberately strict.
- Tyre state, setup, fuel, driver state and other attempt-level factors remain partly latent.
- 120 minutes is the validated model boundary, not a claim that longer-horizon physical forecasting is impossible.
- Intermediate operational minute values are derived interpolation, not independently calibrated scientific forecasts.

## Intended use

The intended use is a pit-wall-style decision-support component: combine a quantified physical-performance opportunity envelope with live queue state, leaderboard context and engineer judgement.

## Not intended for

- autonomous strategy decisions;
- deterministic statements that the next attempt will improve;
- historical queue-duration reconstruction from inter-attempt elapsed time;
- extrapolation beyond the supported horizon presented as validated production inference.
