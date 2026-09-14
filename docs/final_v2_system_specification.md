# Indianapolis 500 Conditional Performance Decision-Support System

## FINAL_V2 System Specification

### 1. Operational problem
Indianapolis 500 qualifying permits repeat attempts under an operational trade-off involving retained qualifying performance, queue priority, remaining session time, and future physical conditions.

Historical reconstruction showed that exact future queue waiting time and next-run opportunity could not be reliably identified from the available historical evidence. The system therefore does not model queue waiting time as a historical training target.

### 2. Final research question
> If another on-track opportunity occurs h minutes from now, what distribution of four-lap qualifying-performance change should be expected relative to the current official result?

The future opportunity horizon h is an externally supplied scenario axis. Supported horizons are 15, 30, 60, 90 and 120 minutes.

### 3. Physics-conditioned performance core
The frozen zero-intercept performance model is:

`Delta_v = beta_track * Delta_T_track + beta_ambient * Delta_T_ambient + epsilon`

The production core uses same-car repeat-attempt transitions and leave-one-year-out validation. Coefficient uncertainty is represented using paired bootstrap draws. Attempt-level unexplained performance variation is represented using symmetrized empirical LOYO residual magnitude.

### 4. V2-A — Future physical-state model
V2-A predicts future track-temperature change conditional on future ambient-temperature change, current track-to-ambient thermal gap, and mean future solar elevation. One separately fitted M2b model is used for each supported horizon. Horizon-specific symmetrized LOYO residuals represent future-track uncertainty and are propagated into the performance model using Monte Carlo simulation.

### 5. V2-B — Section / trap mechanism diagnostic
Section-level evidence is diagnostic rather than predictive. Meaningful attempt-level performance changes are generally spatially coherent across the lap rather than isolated to a small number of sections. Section rows are not treated as independent training observations and do not expand effective sample size.

### 6. V2-C — Wind residual diagnostic
Historical fixed-point wind and gust proxies were evaluated against absolute physics-model residuals. The available historical wind evidence was not sufficiently stable across years to justify either a deterministic wind coefficient or a production heteroskedastic residual-scale model. This does not imply that wind is physically irrelevant.

### 7. V2-D — Uncertainty-source ablation
The final predictive spread was studied diagnostically through source ablation involving future-track uncertainty, paired coefficient uncertainty and empirical performance-residual uncertainty. This is a sensitivity analysis, not a strict additive variance decomposition. Empirical attempt-level residual variation is the dominant uncertainty source.

### 8. V2-E — Systematic scenario stress test
The frozen system was evaluated across 135 empirically grounded physical-state scenarios: 3 thermal-gap states × 3 ambient trajectories × 3 solar states × 5 supported horizons. Scenario separation increased substantially with horizon.

At 15 minutes, P(improvement) ranged from 0.39646 to 0.58500 and expected delta-speed from -0.12261 to +0.10369 mph. At 120 minutes, P(improvement) ranged from 0.20552 to 0.67040 and expected delta-speed from -0.46298 to +0.22479 mph.

### 9. Final uncertainty architecture
For Monte Carlo draw m:

`Delta_T_track^(m) = predicted_Delta_T_track + track_residual^(m)`

`Delta_v^(m) = beta_track^(m) * Delta_T_track^(m) + beta_ambient^(m) * Delta_T_ambient + performance_residual^(m)`

The coefficient pair is always sampled jointly from the same bootstrap row.

### 10. Supported outputs
Expected and median qualifying speed change, probability of improvement, 80% and 90% predictive intervals, and future track-temperature outlook.

### 11. Explicitly unsupported outputs
The system does not predict exact queue waiting time, exact next-run opportunity, Lane 1/Lane 2 waiting-time distribution, probability that another run occurs, autonomous retain/withdraw decisions, overall strategy-success probability, or unique causal attribution of residual performance variation.

### 12. Operational interpretation
The output is conditional: given another on-track opportunity at horizon h and the supplied physical-state scenario, what performance distribution should be expected? It is one input into a larger strategy decision.

### 13. Applicability boundary
Use is subject to technical-regime applicability, qualifying-format applicability, supported horizon, credible physical-state inputs, empirical-support/extrapolation checks, and external queue/competitive-state information.

### 14. Prospective extension
Prospective exact timestamps, lane state, queue position, cars ahead, withdrawal/requeue events, attempt starts/completions, rank/bubble state, remaining session time, interruptions and physical conditions could support a future opportunity model `p(H=h | queue state)`, later combined with the present conditional performance model.

### 15. Final methodological position
The central contribution is the sequence: real strategy problem → historical identifiability audit → rejection of weak queue-time labels → physically identifiable conditional subproblem → uncertainty-aware probabilistic inference → mechanism/residual diagnostics → systematic sensitivity/scenario analysis → explicit applicability boundary.