# v1 Inclusion, Exclusion, and Eligibility Rules

## 1. Governing principles

1. Preserve the historical record before deciding analytical eligibility.
2. Keep an attempt even when its result was withdrawn, waved off, aborted, failed, superseded, bumped, or disallowed.
3. Never convert missing evidence into a zero, a completed lap, an exact timestamp, a lane label, or a queue position.
4. Apply year policy first as an upper bound on permitted roles, then apply row-level rules. A core year does not make every row core eligible.
5. Keep source values, normalized annotations, deterministic derivations, and uncertain inferences distinct through field-level provenance.

## 2. Attempt inclusion

Include one `attempts` row when at least one of the following holds:

- an official detailed Results report enumerates the qualifying attempt;
- official Section Results contain a distinct qualifying run block that can be separated from other outings;
- an official raw feed/replay identifies a qualifying release/current qualifier event;
- official editorial evidence explicitly documents a qualifying attempt omitted from a later summary; or
- third-party chronology identifies an attempt and official evidence independently confirms the car/session/run.

An attempt may be Class A, B, C, or D. It does not need a valid final result.

Exclude or redirect the following:

- `No Attempt` placeholders without evidence of a qualifying start: store the source row/evidence and, if useful, a `chronology_events` status fact; do not count it as an attempt.
- queue entry, lane choice, pit movement, withdrawal announcement, flag, or coverage gap without a qualifying start: store as `chronology_events`.
- duplicate final-summary rows referring to an existing attempt: link as corroborating/final-status evidence rather than creating a second attempt.
- practice, Fast 12/Fast Six, Last Chance, Pole Day, or race records: exclude from this Day 1 dataset.

## 3. Attempt identity and ordering

- Generate an immutable UUID `attempt_id` on first inclusion.
- Populate `car_attempt_index` only when within-car order is directly observed or reproducible from official section/replay chronology.
- Generate `attempt_key = session_id|entry_key|car_attempt_index` only after that index is supportable.
- Never use final qualifying rank, speed rank, PDF row rank, or report row number as attempt sequence.
- Never create a precise global sequence when only a range/order constraint is known. Use `global_order_lower_bound`, `global_order_upper_bound`, and `event_time_quality`.
- Preserve source-native record locators in evidence, so a UUID remains auditable even when order is unresolved.

## 4. Performance-class rules

### Class A: `A_COMPLETE`

Include when four qualifying laps are completed. Store each qualifying lap separately. A withdrawn, superseded, bumped, or disallowed result remains Class A if all four laps occurred.

- Four-lap target: eligible only with four complete, conflict-free official or validly reconstructed lap values and a target value that agrees within the frozen validation tolerance.
- Lap/section analysis: eligible at the corresponding observed grain.
- Chronology/queue calibration: separately determined; completion alone grants neither.

### Class B: `B_PARTIAL_COMPLETE_LAPS`

Include when one to three complete qualifying laps are observed and the four-lap run stops.

- Four-lap target: always ineligible.
- Completed laps: individually eligible when their values/provenance pass checks.
- Use: censored/partial outcome analysis, wave-off/abort behaviour, service-time calibration, and robustness.
- Never impute the missing qualifying laps as observations.

### Class C: `C_SECTION_ONLY`

Include when no complete qualifying lap is available for a portion of the run but official sections exist.

- Four-lap target: always ineligible.
- Lap target: eligible only if the frozen full-section reconstruction rule creates a validated complete lap.
- Section analysis: eligible at nested section grain.
- Use: partial-run shape, failure location, supporting and robustness analysis.

### Class D: `D_CHRONOLOGY_ONLY`

Include as an attempt only when the attempted qualifying occasion is identifiable but has no usable performance timing. Otherwise store the fact only in `chronology_events`.

- Performance targets: ineligible.
- Chronology: eligible if time/order quality is sufficient and does not cross an unresolved coverage gap.
- Simulator calibration: eligible only for the specific observed process, such as an attempt arrival, withdrawal, or interruption.

## 5. Repeated attempts

- Represent every attempt as a separate row with the same `entry_key` and a distinct `attempt_id`.
- Use `car_attempt_index` for within-car order. Never infer it from ranked Results order.
- Within-car comparison requires at least two attempts with known order and compatible outcome measurements.
- Retain the prior attempt after withdrawal; update its result status through separately sourced evidence.
- Record whether the comparison is complete-to-complete, complete-to-partial, or another censored pairing. Do not mix these as equivalent targets.

## 6. Withdrawn, waved-off, aborted, failed, and disallowed attempts

- Preserve the raw official status string and assign a normalized `result_status` without deleting performance.
- `WITHDRAWN`: keep completed laps/result and record withdrawal evidence/time separately. Unknown withdrawal time stays null.
- `WAVED_OFF` or `ABORTED`: store every observed complete lap and official section. Missing laps remain null, not zero unless the source explicitly reports zero as a source value.
- `FAILED` or `INCOMPLETE`: retain the observed portion and official outcome annotation.
- `DISALLOWED`: retain the performance and source evidence; set `result_counted_at_session_end = false` when supported.
- `BUMPED` and `ON_BUBBLE` are outcome/state annotations and do not by themselves determine whether the underlying attempt was complete or valid when run.

## 7. Lap and section rules

- `attempt_laps.lap_number` is limited to qualifying laps 1-4. `source_report_lap_index` preserves the official Section Report index on both lap and section rows and is never overwritten by `lap_number`. Cooldown, warm-up, pit-return, or continuous session lap counters remain source evidence/chronology and are not qualifying laps.
- Store a lap only when the lap position within the attempt is identified. If position is ambiguous, keep sections/evidence unassigned until resolved.
- Store official section values with their published section name, order, section-set version, value, and unit.
- Do not treat section rows as independent samples or expand the effective attempt count.
- Reconstruct a lap only when the official sequence is known, sections do not overlap, full coverage exists, no required section is missing, and the rule validates against known official laps.
- Store reconstructed lap values as `RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE`, not raw.
- Never reconstruct a valid four-lap result from an incomplete attempt.

## 8. Chronology rules and missing intervals

- Source time and event time are distinct. Preserve replay capture timestamp/basis and classify the event-time quality.
- `EXACT_OBSERVED` requires a timestamp directly attached to the event with event-time semantics.
- Timing71 event alignment is normally `APPROXIMATE_OBSERVED` because it is recorder/capture time.
- If only a bracket is known, populate lower/upper bounds and use `BOUNDED_INTERVAL`; do not insert the midpoint as fact.
- If only order is known, use `ORDERING_ONLY` and leave time fields null.
- Add explicit `COVERAGE_GAP` events for the 2020 internal 7m15s gap and the 2023 terminal ~58m38s gap.
- Do not forward-fill leaderboard, rank, current qualifier, weather alignment, pit state, lane, or queue state across a coverage gap.
- Attempts inside/after an unresolved gap can remain performance eligible while chronology eligibility is false.

## 9. Lane, withdrawal, requeue, and queue-state rules

- Populate `lane_action` only with direct or editorially documented evidence, or mark it explicitly inferred. Do not derive lane from withdrawal status alone.
- An inferred lane uses `INFERRED_LANE`, `INFERRED_UNCERTAIN`, and is never a historical target or direct calibration observation.
- Pit exit/entry does not automatically prove requeue. Requeue requires direct/reconstructed action evidence.
- Withdrawal status does not supply withdrawal time. Store the time only to the supported quality level.
- The schema does not store exact queue length, exact queue position, future wait, or future priority insertions as default ground truth.
- Store directly observed queue information as a textual/structured `QUEUE_FACT` chronology event with `OBSERVED_QUEUE_FACT` or `PARTIAL_QUEUE_FACT`.
- Qualitative inference remains `INFERRED_QUALITATIVE_STATE` and cannot be promoted by downstream code.

## 10. Evidence conflicts

1. Preserve all conflicting evidence assertions.
2. Resolve at field level using evidence quality, field specificity, source purpose, and temporal version.
3. Earlier official detailed evidence can establish an attempt even if a later final summary omits it.
4. Later final standing/status can update the disposition but cannot erase the attempt.
5. Section evidence can add existence/performance components and cannot silently rewrite final status.
6. Third-party timestamps augment official performance and stay separately sourced.
7. Editorial evidence can annotate status/action; it cannot silently override official timing.
8. Community claims require independent corroboration or remain weak/non-canonical.
9. Unresolved critical conflicts set relevant eligibility flags false and require a reason code.
10. Never average conflicting canonical values.

## 11. Field-level provenance

- Every substantive populated canonical or derived field requires one primary `field_evidence_links` record.
- Additional evidence links may corroborate, conflict with, or supersede that primary assertion.
- The link records source item, evidence quality through `sources`, value classification, direct/reconstructed state, conflict disposition, rule ID, and uncertainty note.
- Null because unavailable receives an `UNAVAILABLE` link when the field is analytically important; routine optional nulls need not create noise.
- Manual annotations require reviewer, annotation rule/version, and evidence item.
- Deterministic values may have a null `evidence_item_id`; they require derivation rule/version, input lineage, input entity/field references, and optional input snapshot/hash, then must be recomputable. Direct, reconstructed, manual, and inferred assertions must reference real evidence appropriate to their classification.

## 12. Weather inclusion and alignment

- Store forecast issue time, estimated/known availability time, valid interval, grid/station, model/version, variable, value, and unit.
- Primary source priority is NOAA HRRR; issued NWS/IEM products and MOS are supplementary/cross-validation.
- A decision state may use only a forecast snapshot available at or before its as-of time.
- Positive forecast lead is preferred for a decision-time forecast. Do not substitute future observations or model cycles released after the decision.
- If original availability time is uncertain, record the uncertainty and apply a conservative lag/cutoff rule.
- Do not treat HRRR air/surface fields as observed track temperature.

## 13. Fuel-strategy uncertainty

- Do not estimate or store exact fuel mass in v1.
- Use `STANDARD_SINGLE_ATTEMPT_CONTEXT` only when chronology supports an ordinary non-consecutive context; use `UNKNOWN_FUEL_STRATEGY` when chronology cannot distinguish ordinary versus consecutive context.
- Use `SUSPECTED_CONSECUTIVE_ATTEMPT_STRATEGY` only when immediate chronology is consistent with no refuelling/consecutive attempts.
- Use `CONFIRMED_CONSECUTIVE_ATTEMPT_STRATEGY` only with explicit official reporting, interview, or documented team strategy evidence.
- Consecutive timing never establishes exact fuel quantity and may also reflect tyre, engine, hybrid/thermal, weather, track, and mechanical changes.
- Flag these cases, group separately, include them in sensitivity analysis, and repeat relevant analyses with them excluded.

## 14. Row-level eligibility assignment

Eligibility is evaluated after normalization and conflict checks using a versioned deterministic ruleset. Each row is scoped by `analysis_target`; the logical key is `entity_type + entity_id + analysis_target + ruleset_version`. Supported targets are `FOUR_LAP_PERFORMANCE`, `LAP_PERFORMANCE`, `WITHIN_CAR_COMPARISON`, `SECTION_ANALYSIS`, `CHRONOLOGY`, and `QUEUE_CALIBRATION`.

### Attempt

- `eligible = true` for `FOUR_LAP_PERFORMANCE` only for Class A with four validated laps/result and no critical conflict.
- `eligible = true` for `WITHIN_CAR_COMPARISON` only when another compatible attempt for the same entry exists and within-car order is known.
- `eligible = true` for `CHRONOLOGY` only when required event time/order is usable and does not depend on a missing interval.
- `eligible = true` for `QUEUE_CALIBRATION` only for directly observed/reconstructed queue-related facts or usable attempt/service-time observations.
- `eligible_core_training = true` only within the named `analysis_target` when row eligibility and year policy both permit core use.

### Lap

- `eligible = true` for `LAP_PERFORMANCE` only for a complete raw or validly reconstructed lap.
- A lap with missing required section coverage remains ineligible even if a model could impute it later.

### Section

- `eligible = true` for `SECTION_ANALYSIS` with official value, unit, section order/set, and attempt association.
- `eligible_core_training = false` for section rows as independent samples.

### Chronology event

- Chronology eligibility requires usable event time/order and no unresolved coverage-gap dependency.
- Queue-calibration eligibility requires the event itself to observe/reconstruct a relevant process. An inferred qualitative queue label alone is insufficient.

### Role flags

- `supporting_only = true` when the row is retained for annotation, section recovery, context, or a supporting-only year but fails core use.
- `robustness_only = true` only with a prespecified weaker-evidence/year-policy reason.
- `eligible_core_training`, `supporting_only`, and `robustness_only` describe intended analytical role and must be mutually consistent under the ruleset.

## 15. Year-specific enforcement

- **2020:** core performance; partial chronology. Block chronology-dependent rows in/crossing the 7m15s gap.
- **2021:** core performance and chronology after replay reconciliation. Queue observations remain calibration-only.
- **2022:** supporting/robustness performance and section evidence. Preserve Sato's cancelled first attempt; no core chronology or exact weather join.
- **2023:** core performance; partial chronology. Original 84-row Results is the attempt backbone. Block late-session chronology after replay termination unless separately timed.
- **2024:** core performance and chronology after reconciliation. Section Results cannot establish repeated-attempt or partial-attempt coverage.

The machine-readable policy is in `v1_year_usage_policy.csv`.
