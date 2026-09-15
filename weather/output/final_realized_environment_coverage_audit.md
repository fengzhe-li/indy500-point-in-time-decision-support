# Final Realized-Environment Coverage Audit

## Scope

This audit consolidates coverage status only. It does not manufacture new attempt timestamps, modify canonical chronology, or overwrite any existing realized-environment alignment.

## Frozen semantic policy

- Performance-grade Timing71 recorder captures are approximate environment-alignment timestamps only.
- Recorder captures are not exact timed-run starts.
- 2024 chronology-derived constrained alignments remain a separate, stronger-provenance layer.
- 2022 remains unavailable for attempt-level realized environment because no trustworthy absolute-time bridge was found.
- No new chronology salvage is performed by this audit.

## Coverage

| year | canonical_attempts | performance_grade_environment_rows | chronology_derived_environment_rows | cross_layer_overlap_attempts | combined_unique_environment_attempts | combined_unique_coverage_pct | realized_environment_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 63 | 46 | 0 | 0 | 46 | 73.016 | READY_WITH_SUPPORTED_SUBSET |
| 2021 | 60 | 53 | 0 | 0 | 53 | 88.333 | READY_WITH_SUPPORTED_SUBSET |
| 2022 | 44 | 0 | 0 | 0 | 0 | 0.000 | UNAVAILABLE_NO_TRUSTWORTHY_ATTEMPT_TIME_BRIDGE |
| 2023 | 85 | 28 | 0 | 0 | 28 | 32.941 | READY_WITH_SUPPORTED_SUBSET |
| 2024 | 77 | 7 | 4 | 1 | 10 | 12.987 | READY_WITH_SUPPORTED_SUBSET |

## Global totals

- Performance-grade aligned rows: 134
- Combined unique realized-environment attempts: 137
- Canonical attempts across 2020-2024: 329
- Combined unique coverage: 41.641%

## 2024 cross-layer audit

- Performance-grade successful attempts: 7
- Chronology-derived successful attempts: 4
- Overlapping attempt IDs: 1
- Combined unique 2024 attempts: 10

### Overlap differences

- Track temperature MAE: 0.1104938271604965
- Track temperature max absolute difference: 0.1104938271604965
- Ambient temperature MAE: 0.11049382716049294
- Humidity MAE: 0.0

## Freeze checks

- PASS — legacy_2020_matches_expected_46
- PASS — legacy_2021_matches_expected_53
- PASS — 2022_has_zero_attempt_environment_rows
- PASS — legacy_2023_matches_expected_28
- PASS — 2024_supported_performance_matches_expected_7
- PASS — 2024_chronology_has_successful_environment

## Final audit status

**REALIZED_ENVIRONMENT_LAYER_READY_TO_FREEZE**

The supported historical realized-environment layer is ready to freeze. The next phase may move to forecast/decision-state weather alignment without further timing salvage.