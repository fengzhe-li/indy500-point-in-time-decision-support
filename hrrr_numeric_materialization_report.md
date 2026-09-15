# HRRR Numeric Materialization Report

Phase 4A materializes the frozen NOAA HRRR numeric extract at one forecast snapshot per model cycle, lead, and IMS grid point. It performs no attempt-weather alignment or decision-state join.

Frozen source: `/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈/weather/output/hrrr_ims_2020_2024_features.csv`
SHA-256: `79607d49c617dd8582bd5568c5fdb001b02171a5709100e9c4abc00896623ef3`

## Materialization result

| Metric | Result |
|---|---:|
| Frozen input rows read | 259 |
| Canonical forecast snapshots | 259 |
| Canonical numeric weather values | 4403 |
| Raw-source values | 2072 |
| Deterministically derived values | 2331 |
| Duplicate/conflict count | 0 |
| QA checks passed | 22 |
| QA checks failed | 0 |

## Coverage

| Year | Expected cycle × lead combinations | Materialized | Missing |
|---:|---:|---:|---|
| 2020 | 52 | 52 | `NONE` |
| 2021 | 52 | 52 | `NONE` |
| 2022 | 52 | 52 | `NONE` |
| 2023 | 52 | 52 | `NONE` |
| 2024 | 52 | 51 | `14Z_f03` |

## Time semantics

The provider/model identity is NOAA HRRR. The frozen extract does not identify a more specific model version, so `model_version` remains null.

`issue_time_utc` is the observed model cycle/initialization time. `valid_start_utc` and `valid_end_utc` are deterministic cycle-plus-lead valid times and are corroborated by the supplied CSV. `availability_time_utc` is null for every snapshot, `availability_time_quality` is `UNKNOWN`, and extraction metadata records `availability_status=POLICY_REQUIRED`. No cycle timestamp is treated as a public availability timestamp.

A future latency rule must be documented, configurable, versioned, and identified as a policy assumption. This phase does not freeze such a rule.

## Variable semantics and lineage

The layer contains 8 raw GRIB-derived variables and 9 deterministic derivatives per snapshot. Primary field provenance marks their numeric values as `RAW_OBSERVED` or `DERIVED_DETERMINISTIC`; supplied derived columns remain corroborating evidence after formula validation.

The extraction grid identity is preserved as `IMS_HRRR_GRID_POINT` with latitude 39.795 and longitude -86.234 on every snapshot.

`TMP_2m` is 2 m air temperature. `DSWRF_surface` is downward shortwave radiation at the surface. No track temperature, shade, tire, thermal-state, rubber, or track-evolution proxy exists in this output.

## Determinism and readiness

All 22 Phase 4A QA checks pass. Stable snapshot/value identifiers, deterministic source order, frozen input hashing, exact row preservation, and regression regeneration checks make the output deterministic.

Numeric weather layer readiness for Phase 4B environmental alignment: **READY**. Phase 4B must respect chronology uncertainty and establish a conservative availability policy before any decision-time forecast join.
