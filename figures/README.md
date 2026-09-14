# Figures

This directory presents the main visual evidence from the project. The public repository deliberately keeps a broad figure set because model selection, calibration, diagnostics, stress testing, transfer evaluation and operationalisation are separate technical claims.

## Core figure suite

| Figure | Purpose |
|---|---|
| `figure1_identifiability_architecture.svg` | Shows why the original queue-time strategy target was separated from the identifiable conditional-performance problem. |
| `figure3a_physical_state_transitions` | Physical-state changes associated with evidence-qualified same-car transitions. |
| `figure3b_observed_vs_frozen_prediction` | Observed transition response versus the frozen physical-response core. |
| `figure4_future_track_model_selection` | Future track-temperature model comparison / retained M2b specification. |
| `figure5_conformal_calibration` | Horizon-specific uncertainty calibration diagnostics. |
| `figure6_uncertainty_ablation` | Sensitivity to coefficient, future-state and empirical performance-residual uncertainty. |
| `figure7_v2e_120min_stress_test.svg` | V2-E systematic stress test; the underlying frozen study contains 135 scenarios across all calibrated horizons. |
| `figure8_external_2025_validation.svg` | External 2025 hybrid-era evaluation, with the 120-minute product-support boundary visible. |
| `figure8_external_2025_supported_120min.svg` | The four realised 2025 cases whose horizons fall inside the frozen ≤120-minute product support. |
| `figure9a_operational_performance_curve` | Derived operational expected-performance curve. |
| `figure9b_probability_improvement_curve` | Derived operational P(improve) curve. |
| `figure10a_scenario_probability_range` | Range of improvement probabilities across scenario states. |
| `figure10b_scenario_performance_envelope` | Performance envelope across scenario states. |
| `figure11a_loyo_beta_track` | Leave-one-year-out stability of the track-temperature coefficient. |
| `figure11b_loyo_beta_ambient` | Leave-one-year-out stability of the ambient-temperature coefficient. |
| `figure12a_queue_context_performance_overlay` | Display-only overlay of an externally supplied plausible opportunity window on the performance curve. |
| `figure12b_queue_context_probability_overlay` | Display-only opportunity-window overlay on P(improve); this is not a queue model. |
| `appendix_external_2025_beyond_120min.svg` | Explicit out-of-support diagnostic for 2025 realised horizons beyond 120 minutes. |

Where compact SVG renderings are used for GitHub presentation, the associated CSV files under `data/plotting/` preserve the numerical plotting data. Publication PNG/PDF originals remain part of the research workspace and are not treated as additional model evidence.

## Interpretation boundary

The figure suite must not be read as a strategy recommender. In particular, queue-context overlays accept an external plausible `H` window; they do not estimate `P(H|Q)`, queue waiting time, or an optimal withdrawal time. Intermediate operational-curve minutes are presentation interpolation between the five independently calibrated anchors (15/30/60/90/120 min).
