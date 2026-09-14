# Implementation Map

The full research workspace contains a large number of chronology-recovery, evidence-adjudication and exploratory scripts. This public `src/` view is organized by the final technical story rather than by the order in which experiments were run.

## Reconstruction / evidence engineering

The source workspace contains dedicated modules for source registration, provenance, chronology constraints, attempt reconciliation, eligibility, materialization and QA. These are the engineering foundation for the modelling tables.

## Future physical state

Representative source-workspace scripts include:

- `v2_build_future_track_samples.py`
- `v2_evaluate_future_track_models.py`
- `v2_add_solar_features.py`
- `v2_evaluate_solar_models.py`
- `v2_future_track_residual_diagnostics.py`
- `v2_future_track_conformal_calibration.py`

The conformal implementation is included under `src/uncertainty/` as a concrete example of the horizon-specific calibration pipeline.

## Probabilistic performance inference

Representative source-workspace scripts include:

- `v2_integrate_track_to_performance_mc.py`
- `materialize_repeat_performance_uncertainty_v1.py`
- `v2a_build_operational_scenario_outlook.py`

These combine the frozen physical-response core with future track-state uncertainty, paired coefficient draws and empirical performance residuals.

## Mechanism / feature diagnostics

- `v2b_build_section_mechanism_audit.py`
- `v2b_section_residual_diagnostics.py`
- `v2b_section_magnitude_control.py`
- `v2c_wind_linkage_coverage_audit.py`
- `v2c_wind_residual_diagnostic.py`

The point of these diagnostics is not to maximize feature count. They test whether residual structure justifies expanding the predictive model. In FINAL_V2 it did not.

## Uncertainty / stress testing

- `v2d_uncertainty_source_ablation.py`
- `v2e_systematic_scenario_stress_test.py`

V2-D tests sensitivity to uncertainty-source removal. V2-E evaluates 135 systematic physical-state scenarios.

## Operational layer / freezing

- `build_operational_curve_v2.py`
- `freeze_operational_curve_v2.py`
- `final_v2_freeze.py`
- `final_architecture_audit.py`

The operational curve is explicitly downstream of the scientific layer. Freeze manifests and QA outputs prevent presentation interpolation from being mistaken for new scientific calibration.

## Why not publish every exploratory script at repository root?

The research workspace contains more than one hundred historical rescue / audit / exploratory scripts. They are valuable provenance, but placing every intermediate version at the top level would make the final architecture harder to inspect. The public repository therefore foregrounds frozen implementation paths and documents the deeper archaeology separately.