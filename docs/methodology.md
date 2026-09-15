# Methodology

## 1. Evidence reconstruction

The canonical unit is one complete official four-lap qualifying attempt. Source-specific parsers recover official results and section records; chronology and environmental joins carry provenance, confidence and exclusion semantics. Partial and waved-off traces may support reconstruction but do not automatically become response observations.

## 2. Same-car transition design

The response dataset compares consecutive usable attempts by the same car. For each transition:

```text
Δv = four-lap average speed_after − four-lap average speed_before
ΔTtrack = track temperature_after − track temperature_before
ΔTambient = ambient temperature_after − ambient temperature_before
```

Same-car differencing reduces persistent driver, car and configuration variation. It does not eliminate setup changes, tyre preparation, execution or other latent run state.

## 3. Physical response

The frozen robust model has zero intercept:

```text
Δvphysical = βtrack ΔTtrack + βambient ΔTambient
```

Verified coefficients are `βtrack = −0.03482533 mph/°C` and `βambient = +0.18239338 mph/°C`. The zero intercept constrains only the modelled physical contribution.

Model selection and evaluation use leave-one-year-out logic. Paired bootstrap rows preserve dependence between coefficient draws. Empirical centered leave-one-year-out residuals represent unexplained attempt-level variation.

## 4. Future track state

The future-state target is `ΔTtrack(h)`. M2b uses future ambient-temperature change, current track-to-ambient thermal gap and mean solar elevation. A separate model is fitted at 15, 30, 60, 90 and 120 minutes. Finite-sample absolute-residual conformal logic supplies horizon-specific track-state uncertainty.

Solar is a deterministic geometry proxy; it is not measured irradiance, cloud or shade exposure. Realized historical future ambient change is used in retrospective model evaluation and is not presented as live forecast validation.

## 5. Monte Carlo propagation

Each draw samples:

1. future track-state residual uncertainty;
2. a paired physical-response coefficient row;
3. an empirical performance residual.

The output includes expected and median Δspeed, P(Δv > 0), and 80%/90% predictive intervals. Opportunity probability, queue duration and decision utility are absent by design.

## 6. Diagnostics

Section timing tests spatial coherence without sample inflation. Wind variables are evaluated as residual diagnostics and are not retained in production. Uncertainty-source ablation measures sensitivity of predictive width; it is not an additive variance decomposition. The 135-case scenario matrix tests conditional system behaviour within historical ambient-trajectory support.

## 7. Validation and freeze

The core is frozen on 2020–2024. The 2025 hybrid-era sample remains external. Operational one-minute curves preserve the five calibrated anchors exactly and label intermediate points as interpolation.

