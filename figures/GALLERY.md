# Figure gallery

Repository figure names are semantic. Manuscript numbering is kept only in the paper and legacy publication assets. The curated set below is generated or copied by `scripts/generate_portfolio_figures.py`.

| Preview | Purpose | Source analysis | Scientific status |
|---|---|---|---|
| [![Identifiability](portfolio/identifiability-system-boundary.svg)](portfolio/identifiability-system-boundary.svg) | Identifiability-driven scope and human decision boundary | Historical reconnaissance + FINAL_V2 specification | System architecture |
| [![Pipeline](portfolio/evidence-engineering-pipeline.svg)](portfolio/evidence-engineering-pipeline.svg) | End-to-end evidence and model pipeline | Canonical pipeline through FINAL_V2 | System architecture |
| [![Evidence products](portfolio/evidence-products-and-attrition.svg)](portfolio/evidence-products-and-attrition.svg) | Verified products and distinct observation units | R5.2, V2-A, V2-B, 2025 evaluation | Evidence summary |
| [![Hierarchy](portfolio/evidence-hierarchy.svg)](portfolio/evidence-hierarchy.svg) | Evidence authority and quarantine | Canonical eligibility rules | Evidence summary |
| [![Same car](portfolio/same-car-transition-design.svg)](portfolio/same-car-transition-design.svg) | Same-car differencing design | Frozen response core | Methodology |
| [![Physical response](portfolio/frozen-physical-response.svg)](portfolio/frozen-physical-response.svg) | Frozen zero-intercept response and coefficients | R5.2 FINAL_V2 | Frozen model |
| [![Future state](portfolio/future-track-state-model.svg)](portfolio/future-track-state-model.svg) | Separate future track-state layer | V2-A | Frozen model |
| [![Model selection](portfolio/future-track-model-selection.png)](portfolio/future-track-model-selection.png) | Out-of-year future-state candidate comparison | V2-A | Paper-aligned result |
| [![Uncertainty architecture](portfolio/three-source-uncertainty.svg)](portfolio/three-source-uncertainty.svg) | Three propagated sources | FINAL_V2 | System architecture |
| [![Ablation](portfolio/uncertainty-source-ablation.png)](portfolio/uncertainty-source-ablation.png) | Predictive-width sensitivity | V2-D | Frozen diagnostic |
| [![Horizon boundary](portfolio/calibrated-horizon-boundary.svg)](portfolio/calibrated-horizon-boundary.svg) | Calibration versus interpolation | OPERATIONAL_CURVE_V2 | Operational semantics |
| [![Sections](portfolio/section-mechanism-coherence.png)](portfolio/section-mechanism-coherence.png) | Spatial coherence without sample inflation | V2-B | Frozen diagnostic |
| [![Wind](portfolio/wind-residual-diagnostic.png)](portfolio/wind-residual-diagnostic.png) | Rejected wind extension | V2-C | Frozen diagnostic |
| [![Stress test](portfolio/scenario-stress-test-120min.png)](portfolio/scenario-stress-test-120min.png) | 120-minute physical-state scenario surface | V2-E | Frozen stress test |
| [![External validation](portfolio/external-validation-2025.png)](portfolio/external-validation-2025.png) | All 15 external cases and support boundary | R6 external evaluation v2 | External validation |
| [![Supported external subset](portfolio/external-validation-2025-supported.png)](portfolio/external-validation-2025-supported.png) | Four cases within production horizon | R6 external evaluation v2 | External validation subset |
| [![Regime timeline](portfolio/technical-regime-timeline.svg)](portfolio/technical-regime-timeline.svg) | Technical and format boundaries | R6 frozen extension | Transfer/applicability |
| [![Regime coefficients](portfolio/regime-coefficient-comparison.png)](portfolio/regime-coefficient-comparison.png) | Coefficient estimates and 90% intervals | R6 regime comparison | Supporting transfer analysis |
| [![Operational curve](portfolio/operational-performance-outlook.png)](portfolio/operational-performance-outlook.png) | Expected speed and predictive bands | OPERATIONAL_CURVE_V2 | Operational presentation |
| [![Operational probability](portfolio/operational-probability-outlook.png)](portfolio/operational-probability-outlook.png) | Conditional P(improvement) curve | OPERATIONAL_CURVE_V2 | Operational presentation |
| [![Freeze](portfolio/freeze-and-reproducibility.svg)](portfolio/freeze-and-reproducibility.svg) | Versioning and external-evidence separation | Freeze manifests | Reproducibility architecture |

The SVG diagrams are explanatory views. Numerical plots are generated from or copied byte-for-byte from frozen outputs. None of the gallery assets refits a scientific model.

## Manuscript-aligned and supplementary source assets

These legacy names retain the numbering used during paper production. They remain evidence-grounded source assets; GitHub-facing references use the semantic names above.

| Asset group | Purpose | Source analysis | Scientific status |
|---|---|---|---|
| [`figure3a_physical_state_transitions`](figure3a_physical_state_transitions.png), [`figure3b_observed_vs_frozen_prediction`](figure3b_observed_vs_frozen_prediction.png) | Physical-state examples and frozen response comparison | R5.2 response core | Paper-aligned |
| [`figure4_future_track_model_selection`](figure4_future_track_model_selection.png) | Candidate future-state comparison | V2-A | Paper-aligned; curated semantic copy used above |
| [`figure5_conformal_calibration`](figure5_conformal_calibration.png) | Future track-state interval calibration | V2-A | Paper-aligned |
| [`figure6_uncertainty_ablation`](figure6_uncertainty_ablation.png) | Uncertainty-source sensitivity | V2-D | Paper-aligned; curated semantic copy used above |
| [`figure7_v2e_120min_stress_test`](figure7_v2e_120min_stress_test.png) | 120-minute scenario matrix | V2-E | Paper-aligned; curated semantic copy used above |
| [`figure8_external_2025_validation`](figure8_external_2025_validation.png), [`supported subset`](figure8_external_2025_supported_120min.png) | 2025 external evaluation | R6 evaluation v2 | Paper-aligned; semantic copies used above |
| [`appendix_external_2025_beyond_120min`](appendix_external_2025_beyond_120min.png) | Cases beyond production boundary | R6 evaluation v2 | Extended retrospective diagnostic |
| [`figure9a_operational_performance_curve`](figure9a_operational_performance_curve.png), [`figure9b_probability_improvement_curve`](figure9b_probability_improvement_curve.png) | Continuous presentation from frozen anchors | OPERATIONAL_CURVE_V2 | Paper-aligned; semantic copies used above |
| [`figure10a_scenario_probability_range`](figure10a_scenario_probability_range.png), [`figure10b_scenario_performance_envelope`](figure10b_scenario_performance_envelope.png) | Horizon-wise stress-test envelope | V2-E | Supplementary frozen diagnostic |
| [`figure11a_loyo_beta_track`](figure11a_loyo_beta_track.png), [`figure11b_loyo_beta_ambient`](figure11b_loyo_beta_ambient.png) | Leave-one-year-out coefficient stability | R5.2 response core | Supplementary diagnostic |
| [`figure12a_queue_context_performance_overlay`](figure12a_queue_context_performance_overlay.png), [`figure12b_queue_context_probability_overlay`](figure12b_queue_context_probability_overlay.png) | Externally supplied opportunity-window overlay | OPERATIONAL_CURVE_V2 | Operational illustration; not a queue prediction |

Matching PDF versions preserve publication-quality export, and adjacent plotting-data CSV files retain auditable figure inputs. The obsolete duplicate with a non-semantic `_副本` suffix and the superseded standalone root architecture export were removed during the consistency audit.
