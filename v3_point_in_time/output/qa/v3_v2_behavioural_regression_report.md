# Phase 2 Step 6 — V3 vs Frozen V2 Behavioural Regression Report

n_mc=50000, tolerance = 5.0 x mc_sd_reference x sqrt(2/n_mc) (Monte Carlo sampling-error bound, not an arbitrary number).

V3 intentionally uses a different RNG seed/stream than the frozen batch script
(documented design decision, see existing_system_inventory.md). This checks
statistical agreement of two independent Monte Carlo estimates of the same
frozen analytic model, not bitwise equality.

| Horizon | Ref E[Δv] | V3 E[Δv] | Diff | Tolerance | Pass | Ref median | V3 median | Pass | Ref P(imp) | V3 P(imp) |
|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|
| 15 | +0.0827 | +0.0876 | +0.0049 | 0.0332 | PASS | +0.0815 | +0.0847 | PASS | 0.5704 | 0.5779 |
| 30 | +0.1511 | +0.1678 | +0.0167 | 0.0334 | PASS | +0.1616 | +0.1649 | PASS | 0.6311 | 0.6402 |
| 60 | +0.3789 | +0.3855 | +0.0066 | 0.0333 | PASS | +0.3727 | +0.3795 | PASS | 0.7712 | 0.7757 |
| 90 | +0.1568 | +0.1516 | -0.0052 | 0.0331 | PASS | +0.1550 | +0.1537 | PASS | 0.6221 | 0.6248 |
| 120 | +0.3575 | +0.3633 | +0.0058 | 0.0335 | PASS | +0.3548 | +0.3589 | PASS | 0.7597 | 0.7586 |

80% predictive interval comparison (illustrative; PI bounds are quantiles, not
means, so no formal tolerance is applied -- shown for qualitative agreement only):

| Horizon | Ref 80% PI | V3 80% PI |
|---|---|---|
| 15 | [-0.662, +0.830] | [-0.635, +0.820] |
| 30 | [-0.597, +0.879] | [-0.546, +0.909] |
| 60 | [-0.343, +1.179] | [-0.337, +1.191] |
| 90 | [-0.597, +0.906] | [-0.590, +0.925] |
| 120 | [-0.412, +1.163] | [-0.382, +1.182] |

## Overall result: PASS

V3's adapter reproduces the frozen FINAL_V2 physical-response Monte Carlo
integration within Monte Carlo sampling error at all five calibrated horizons,
using a different (intentionally independent) random stream. The observed
differences are consistent with sampling noise, not a change in the underlying
model, coefficients, or residual pools.