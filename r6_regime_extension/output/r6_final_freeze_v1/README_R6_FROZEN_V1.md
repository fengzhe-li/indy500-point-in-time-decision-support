# R6 Regulation-Aware Physics Extension — Frozen V1

## Status

`R6_REGULATION_AWARE_EXTENSION_V1_FROZEN`

The 2020–2024 R5.2 core remains unchanged.

## Scientific question

Does the physical sensitivity of Indianapolis 500 qualifying
performance remain stable across technical regulation regimes?

## Technical regimes

- **A — Universal Aero Kit / pre-Aeroscreen**
  - Direct repeat-physics evidence: 2019
  - Primary transitions: 10
  - Huber no-intercept beta_track: -0.05059376 mph/°C
  - Huber no-intercept beta_ambient: 0.17008053 mph/°C
  - Delta-track / delta-ambient correlation:
    0.925658
  - Interpretation: limited, small-sample, highly collinear evidence.

- **B — Aeroscreen / pre-hybrid**
  - Frozen R5.2 reference
  - 2020–2024
  - Primary transitions: 41
  - beta_track: -0.03482533 mph/°C
  - beta_ambient: 0.18239338 mph/°C
  - This core was not refitted or modified by R6.

- **C — Aeroscreen / hybrid**
  - Direct repeat-physics evidence: 2025
  - Primary transitions: 23
  - Huber no-intercept beta_track: -0.06308090 mph/°C
  - Huber no-intercept beta_ambient: 0.12099925 mph/°C
  - Delta-track / delta-ambient correlation:
    0.615486

## Chronology status

- 2018: `PARTIAL_SOURCE_COVERAGE`
- 2019: `PASS`
- 2025: `PASS`
- 2026: `STRUCTURALLY_NO_REPEAT_BY_FORMAT`

## Physical linkage

- 2019: 10 / 10 clean transitions safely linked to PTSC.
- 2025: 23 / 24 clean transitions safely linked to PTSC.
- One 2025 Conor Daly transition was excluded because its endpoint
  occurred after the final PTSC observation.
- Long PTSC observation gaps were not extrapolated into the
  primary physics set.

## Main result

Within the recoverable historical evidence, there is no clear
evidence of a regulation-era shift in physics-conditioned
Indianapolis 500 qualifying sensitivity.

The hybrid-era 2025 sample preserves the same directional response
as the frozen 2020–2024 reference:

- higher track temperature conditional on ambient is associated
  with lower qualifying speed;
- the fitted ambient coefficient conditional on track remains
  positive.

All 90% bootstrap intervals for direct A−B, C−B, and A−C
coefficient differences include zero.

This is **not** an equivalence proof and **not** a causal
regulation-effect analysis.

## Identifiability limitation

Regime A has only 10 primary repeat transitions and strong predictor
collinearity:

`corr(delta_track, delta_ambient) =
0.925658`

Therefore A should be treated as supporting / compatibility evidence,
not a precise independent sensitivity estimate.

Regime C is substantially better conditioned:

`corr(delta_track, delta_ambient) =
0.615486`

## Physics invariance

For every regime:

`delta_track = 0` and `delta_ambient = 0`
implies
`predicted physical delta_speed = 0`.

PASS.

## Scope

R6 extends the frozen project with regulation-aware evidence.
It does not replace the 2020–2024 probabilistic decision-support core.

The model remains a physical performance-change support layer and
does not recommend DELETE / WITHDRAW / RETAIN / REATTEMPT actions.
