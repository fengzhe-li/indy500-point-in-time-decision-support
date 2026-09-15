# Global Pipeline Consistency Audit V1

Policy version: `GLOBAL_PIPELINE_CONSISTENCY_AUDIT_V1`
Global policy hash: `8972ef7667126756eedf27624163201fcf3fed011b9f524b9d32016a94d05144`

## Purpose

Verify cross-phase row counts, frozen evidence boundaries, recommendation restrictions, QA status, and policy-hash presence.

## Numeric invariants

- `canonical_attempts`: expected `329`, actual `329`, status `PASS`
- `performance_timing_total`: expected `136`, actual `136`, status `PASS`
- `repeat_uncertainty_rows`: expected `39`, actual `39`, status `PASS`
- `normal_rows`: expected `35`, actual `35`, status `PASS`
- `recovery_rows`: expected `4`, actual `4`, status `PASS`
- `direct_queue_wait_pairs`: expected `0`, actual `0`, status `PASS`
- `complete_run_duration_rows`: expected `260`, actual `260`, status `PASS`
- `mc_scenarios`: expected `120`, actual `120`, status `PASS`
- `draws_per_scenario`: expected `100000`, actual `100000`, status `PASS`
- `total_mc_draws`: expected `12000000`, actual `12000000`, status `PASS`
- `target_compact_rows`: expected `480`, actual `480`, status `PASS`
- `loyo_profile_rows`: expected `24`, actual `24`, status `PASS`
- `robustness_envelope_rows`: expected `480`, actual `480`, status `PASS`
- `final_profile_rows`: expected `480`, actual `480`, status `PASS`

## Decision boundary

- Recommendation-enabled final rows: `0`
- Final rows marked NOT_ISSUED: `480/480`
- Historical queue-wait claim present: `False`
- Historical leaderboard claim present: `False`

## Evidence boundary

- Direct queue wait: `UNOBSERVED`
- Exact queue position: `UNOBSERVED`
- 2024 session cutoff: `EXACT_SUPPORTED`

## Phase QA

All audited phase QA files pass: `True`

## Status

**GLOBAL_PIPELINE_CONSISTENCY_FROZEN**