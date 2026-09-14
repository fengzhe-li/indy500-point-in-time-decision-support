# Methodology Summary

## 1. Original operational question

The project began from the practical Indy 500 qualifying trade-off between retaining an existing four-lap result and waiting for another opportunity, or withdrawing that result to gain higher requalification priority.

A complete end-to-end system would need both:

1. an opportunity model: when another on-track opportunity will occur; and
2. a performance model: what four-lap performance should be expected at that time.

Historical reconstruction showed that the first quantity was not consistently identifiable across seasons because queue entry, lane state, withdrawals, requeue behaviour, live queue position, exact timing and team intent were incomplete or inconsistent.

The project therefore reformulated the target as:

> If another on-track opportunity occurs *h* minutes from now, what distribution of four-lap qualifying-performance change should be expected relative to the current official result?

The model estimates `p(Δv | H=h)` rather than `P(H=h)`.

## 2. Historical evidence architecture

The evidence base was reconstructed from multi-season official qualifying results, detailed timing, section and trap records, repeat-attempt chronology, environmental observations and supplementary historical evidence.

The primary statistical unit is one complete four-lap qualifying attempt. Same-car repeated attempts are differenced as

`Δv = v(i+1) - v(i)`

with corresponding physical-state changes such as

`ΔT_track = T_track(i+1) - T_track(i)`

and

`ΔT_ambient = T_ambient(i+1) - T_ambient(i)`.

The frozen 2020–2024 performance core contains 41 evidence-qualified same-car transitions.

## 3. Physical-response model

The retained compact zero-intercept model is

`Δv = β_track ΔT_track + β_ambient ΔT_ambient + ε`

with frozen coefficients:

- `β_track = -0.03482533`
- `β_ambient = +0.18239338`

The zero intercept prevents the model from learning a generic reattempt bonus or penalty when the retained measured physical state does not change.

The fitted coefficients are conditional relationships, not universal causal constants.

## 4. Future physical state

Future track temperature is modelled separately from qualifying performance.

The retained future-state interface is conceptually

`(h, ΔT_ambient(h), G0, S_mean(h)) -> p(ΔT_track(h))`

where

- `G0 = T_track,0 - T_ambient,0` is the current thermal gap;
- `S_mean(h)` represents mean solar state across the future interval.

Solar therefore enters through

`solar state -> track heating -> track temperature -> performance`

rather than as a direct deterministic performance term.

The independently calibrated horizons are exactly 15, 30, 60, 90 and 120 minutes.

## 5. Probabilistic inference

The final Monte Carlo system propagates three uncertainty sources:

1. future track-state uncertainty;
2. paired bootstrap uncertainty in the two physical-response coefficients;
3. empirical out-of-year attempt-level performance residual variation.

The two bootstrap coefficients are sampled as paired draws rather than independently. Their empirical bootstrap correlation is approximately `-0.9085`.

The empirical performance residual dominates final predictive interval width under uncertainty-source ablation.

## 6. Diagnostics rather than feature expansion

Additional analyses were used to interrogate the frozen core rather than automatically enlarge it.

### Section-level mechanism evidence

Usable comparable section evidence was linked for 39 of the 41 frozen transitions. The section analysis supports the interpretation that meaningful performance changes are commonly broad and spatially coherent rather than isolated to one small part of the circuit.

### Wind diagnostics

Available historical wind proxies did not provide sufficiently stable evidence to justify an explicit deterministic or heteroskedastic wind term. This is not a claim that wind has no physical effect.

### Scenario stress test

A 135-scenario stress test spans thermal-gap state, ambient trajectory, solar state and the five supported future horizons.

## 7. External evaluation

The frozen 2020–2024 inference core was evaluated externally on 15 eligible 2025 hybrid-era repeat attempts.

Frozen aggregate results:

- MAE: `0.492 mph`
- median absolute error: `0.425 mph`
- RMSE: `0.610 mph`
- 80% predictive-interval coverage: `80%`
- 90% predictive-interval coverage: `100%`
- directional accuracy: `46.7%`

The external experiment uses realised environmental trajectories retrospectively to isolate physical-inference performance. It is not a validation of live weather-forecast skill.

## 8. Operational presentation layer

`FINAL_V2` is the scientific / modelling layer.

`OPERATIONAL_CURVE_V2` is a separate derived visualization layer.

At the calibrated anchors, frozen outputs are reproduced exactly. Intermediate 15–120 minute values are piecewise-linear interpolations of frozen output summaries. They are presentation approximations, not independently calibrated forecasts or newly generated Monte Carlo distributions.

At `h=0`, the present state is an observed boundary. No future probability or predictive interval is fabricated there.

## 9. Queue-context overlay

External pit-wall information may provide a plausible future opportunity window. That window can be overlaid on the frozen operational curve without estimating a queue-time distribution.

The architecture therefore remains:

`external opportunity context -> relevant horizon window`

plus

`FINAL_V2 / OPERATIONAL_CURVE_V2 -> conditional performance outlook`.

The model does not infer an optimal wait, queue-time probability distribution or automatic withdraw / retain strategy recommendation.
