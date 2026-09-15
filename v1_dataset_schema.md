# Indy 500 Qualifying Decision Support: v1 Dataset Schema

## 1. Frozen scope

The v1 dataset supports attempt-performance modelling, observed chronology where available, historical decision-time forecasts, official section timing, and a probabilistic queue/wait-time simulator. It does not represent exact historical queue state as known truth.

The prior feasibility findings remain fixed:

- Original Gate A: `FAIL`
- Original Gate B: `FAIL`
- Performance modelling: `CONDITIONAL PASS`
- Exact historical queue reconstruction: `FAIL`
- Probabilistic sequential decision simulation: `CONDITIONAL PASS`
- Fuel load: `MODERATE_MANAGEABLE_CONFOUNDER`
- Project recommendation: `PROCEED WITH REDUCED SCOPE`

## 2. Table set

### Canonical lower-level tables

| Table | Grain and purpose | Primary key | Main foreign keys |
|---|---|---|---|
| `qualifying_events` | One official Day 1 qualifying session. Holds session identity and official schedule boundaries. | `session_id` | None |
| `attempts` | One identifiable qualifying attempt, including complete, partial, zero-lap, withdrawn, waved-off, aborted, or officially recoverable attempts. | `attempt_id` | `session_id` |
| `attempt_laps` | One qualifying lap position within one attempt. Only qualifying laps 1-4 belong here; cooldown/pit-return laps do not. | `attempt_lap_id` | `attempt_id` |
| `attempt_sections` | One official section observation within an attempt/lap. Supports section review and permitted lap reconstruction. | `attempt_section_id` | `attempt_id`; optionally `attempt_lap_id` |
| `chronology_events` | One observed or reconstructed chronological fact, including attempt start/end, withdrawal, pit movement, flag, coverage gap, lane evidence, requeue evidence, or queue fact. | `chronology_event_id` | `session_id`; optionally `attempt_id` |
| `chronology_constraints` | One strongest-supported attempt-level chronology constraint for each 2024 canonical attempt, with capture, anchor, timed-run, uncertainty, and origin semantics kept separate. | `chronology_constraint_id` | `session_id`; `attempt_id`; optional capture event and evidence item |
| `forecast_snapshots` | One forecast model cycle, spatial reference, issue/availability context, and valid-time context. | `forecast_snapshot_id` | `session_id`; `source_id` |
| `weather_forecasts` | One variable-level value under one normalized forecast snapshot. | `weather_forecast_value_id` | `forecast_snapshot_id` |

### Evidence and policy support tables

| Table | Grain and purpose | Primary key | Main foreign keys |
|---|---|---|---|
| `sources` | One source family/artifact origin with evidence quality and priority metadata. | `source_id` | None |
| `evidence_items` | One citable source unit: PDF page/row, API record, replay frame/message, article passage, or manual review note. | `evidence_item_id` | `source_id` |
| `field_evidence_links` | One evidence assertion or reproducible derivation for one field on one logical entity. Allows different fields of one attempt to come from different sources. | `field_evidence_link_id` | nullable `evidence_item_id`; logical entity reference |
| `row_eligibility` | Deterministically evaluated permission for one entity and one analysis target. | (`entity_type`, `entity_id`, `analysis_target`, `ruleset_version`) | Logical entity reference |

### Derived table

| Table | Grain and purpose | Primary key | Main foreign keys |
|---|---|---|---|
| `decision_state_features` | A reproducible state snapshot immediately before a defined decision or attempt. It is a cache/view of canonical history, never the source of truth. | `decision_state_id` | `session_id`; `subject_attempt_id`; optional `forecast_snapshot_id` |

No separate driver/team/entry dimension is required for v1. `entry_key`, car number, driver name, and team name remain on the attempt/event records. A normalized entrant dimension may be added later only if identity changes cannot be handled reliably.

## 3. Qualifying attempt definition and identity

One qualifying attempt is an identifiable occasion on which an entry is officially released/presented to make an Indy 500 Day 1 qualifying run, or an official source explicitly records the occasion as a qualifying attempt. It may end with four completed laps, fewer completed laps, section-only evidence, a wave-off, an abort, a withdrawal/disallowance of its result, or no usable performance timing.

The following do not independently create an attempt:

- a final-standing row that only repeats an already represented attempt;
- a `No Attempt` placeholder without evidence that the car began a qualifying run;
- entry into a pit or queue without a qualifying release/start;
- a cooldown or pit-return lap;
- one section row.

Repeated attempts are separate `attempts` rows. Withdrawal changes the status/use of an attempt; it does not delete the attempt. A later final-summary omission also does not delete an earlier officially observed attempt.

`attempt_id` is a generated UUID and is the permanent identifier. When per-car order is supportable, `attempt_key` is generated as:

`session_id | entry_key | car_attempt_index`

`car_attempt_index` is the observed/reconstructed order within that car and session. It is not global session order. If even the per-car order is unresolved, `car_attempt_index` and `attempt_key` remain null; the UUID, source-native locator, and order bounds preserve identity until resolution. No globally exact session sequence is required. `global_order_lower_bound` and `global_order_upper_bound` may encode a known interval; equality means exact reconstructed order.

## 4. Attempt classes

| Class | Definition | Four-lap target | Lap analysis | Section analysis | Within-car repeat comparison | Chronology | Robustness | Simulator calibration |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `A_COMPLETE` | Four qualifying laps completed. Result may later be withdrawn, superseded, bumped, or disallowed. | yes if all four lap values and target status pass validation | yes | yes when present | yes when car order is known | yes when time/order quality permits | yes | yes when chronology quality permits |
| `B_PARTIAL_COMPLETE_LAPS` | At least one complete qualifying lap exists but fewer than four. | no | yes for observed complete laps | yes when present | yes for censored/partial comparison, never as a four-lap target | yes when time/order permits | yes | yes for abort/wave-off/service-time calibration when chronology permits |
| `C_SECTION_ONLY` | No complete qualifying lap is available for part of the run, but at least one official qualifying-section observation exists. | no | only if a complete lap is validly reconstructed | yes | supporting-only | yes when time/order permits | yes | limited to partial-run/duration calibration |
| `D_CHRONOLOGY_ONLY` | An identifiable attempt/event has useful chronology or decision evidence but no usable qualifying performance timing. | no | no | no | chronology comparison only | yes when time/order permits | yes | yes only for event/arrival/status processes |

A Class D item that is clearly an attempt may remain in `attempts`; a non-attempt action such as a withdrawal announcement or flag change belongs in `chronology_events` and may link to an attempt.

## 5. Section reconstruction rule

Sections may reconstruct a complete lap only when all five conditions hold:

1. the official section sequence and section-set version are known;
2. sections are non-overlapping;
3. their union covers the complete lap;
4. no required section is missing; and
5. the sum/reconstruction rule has passed validation against official known complete laps for that report format/year within a frozen tolerance.

The reconstructed lap receives `RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE`, links to every contributing section, records the reconstruction rule/version, and retains the validation result. If any condition fails, the lap time remains null and only observed sections are stored. A reconstructed complete lap is not automatically a valid four-lap qualifying result. Section rows remain nested components and are never independent attempt-level training samples.

Section ingestion precedes reconstruction validation. Every attributable official section value is retained, including partial source-report laps. `source_report_lap_time_seconds` preserves the report's lap-time cell when present, while `section_lap_coverage_status` distinguishes `PARTIAL_OBSERVATION`, `COMPLETE_CANDIDATE`, `VALIDATED_COMPLETE`, and `VALIDATION_FAILED`. Only `VALIDATED_COMPLETE` may create a reconstructed lap; failed or partial groups remain section evidence.

`SECTION_SUM_2020_2023_V1` and `SECTION_SUM_2024_V1` are separate frozen configurations. Their tolerances are calculated from published precision and empirical residuals on known complete official laps, then written to the rule registry. Continuous source-report numbering is never treated as a native attempt identifier. Both `attempt_laps` and `attempt_sections` preserve `source_report_lap_index`; qualifying `lap_number` remains the reconstructed position 1-4.

## 6. Data-classification vocabulary

Every important populated value receives exactly one classification in its primary `field_evidence_links` record:

| Classification | Meaning |
|---|---|
| `RAW_OBSERVED` | The value appears directly in the cited source. A replay capture timestamp is raw as a capture timestamp, though the corresponding event time may be approximate. |
| `RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE` | Official source components are combined by a documented, validated rule to create a value not supplied ready-made. |
| `DERIVED_DETERMINISTIC` | The value is exactly reproducible from lower-level canonical fields and a versioned rule. |
| `INFERRED_UNCERTAIN` | The value depends on an assumption or probabilistic/qualitative inference and is not historical ground truth. |
| `MANUALLY_ANNOTATED` | A reviewer assigned the value from documented evidence under a written annotation rule. |
| `UNAVAILABLE` | The available evidence cannot recover the value. The canonical value remains null. |

Technical surrogate keys are deterministic system metadata and do not need source evidence. All substantive values do. A `DERIVED_DETERMINISTIC` link may have `evidence_item_id = NULL`, but it must record `derivation_rule_id`, `derivation_rule_version`, `input_lineage_json`, `input_entity_field_refs_json`, and optionally `input_snapshot_hash`. Reconstructed, manual, inferred, and direct-observed assertions require appropriate real evidence; the pipeline never manufactures a source item to satisfy a constraint.

## 7. Evidence hierarchy and conflict resolution

The default evidence-quality order is:

`OFFICIAL_RAW` > `OFFICIAL_REPORT` > `OFFICIAL_EDITORIAL` > `THIRD_PARTY_CAPTURE` > `COMMUNITY_CLAIM`

This order is applied per field, not per row. Source purpose, temporal version, specificity, and completeness are also considered. Conflict resolution follows these frozen rules:

1. An earlier official raw/detailed record can establish that an attempt existed even when a later final summary omits it.
2. A later final summary updates final standing/status where appropriate but never erases an earlier officially observed attempt.
3. Official Section Results may recover existence or performance components of an omitted attempt. They do not silently overwrite final classification; status remains separately sourced.
4. Third-party replay timestamps may augment official attempt performance. Their provenance and event-time quality remain separate.
5. Editorial evidence may annotate event/status/action facts. It cannot replace official timing performance unless the official value is absent, the substitution is explicit, and its lower evidence quality remains recorded.
6. Community claims are weak supplementary evidence. They cannot define a canonical value without independent corroboration; otherwise the field remains uncertain or unavailable.
7. Two disagreeing official values are not resolved by “latest wins” alone. Preserve both evidence assertions, choose a primary value only through a documented field-specific rule, and record the rejected/superseded disposition.
8. Never average conflicting times, speeds, statuses, or lane labels.

## 8. Field-level provenance mechanism

`sources` describes origin and evidence quality. `evidence_items` identifies the precise row/page/frame/passage. `field_evidence_links` connects that evidence to one entity field.

Example for one attempt:

- `attempt_id` existence and Lap 1-4 values: official Results evidence items;
- `start_time_utc`: a Timing71 qualifier-transition frame;
- `result_status`: official Results or official editorial evidence;
- section values: official Section Results rows;
- lane evidence: a distinct official/editorial action statement.

The primary evidence link carries the value classification, uncertainty note, conflict disposition, rule version, and reproducible input lineage where applicable. Secondary/corroborating links remain queryable. An attempt row never receives a single blanket source label. Direct observations normally require an evidence item; reconstructions require all contributing items and a reconstruction rule; manual annotations require evidence and an annotation rule; uncertain inference requires evidence or explicit assumption metadata.

## 9. Chronology uncertainty

### Event time quality

- `EXACT_OBSERVED`: a source directly timestamps the specific event with event-time semantics.
- `APPROXIMATE_OBSERVED`: a displayed/replay capture time directly accompanies the event but may be rounded or delayed.
- `BOUNDED_INTERVAL`: only lower and upper event-time bounds are defensible.
- `ORDERING_ONLY`: relative order is known without a useful time interval.
- `UNKNOWN`: neither usable time nor order is recoverable.

Timing71 recorder timestamps normally map to `APPROXIMATE_OBSERVED`, not `EXACT_OBSERVED`. Raw recorder/source time is stored on `evidence_items.source_timestamp_utc` with `source_timestamp_basis`; canonical event time is stored separately as `event_time_utc`, lower/upper bounds, and quality. A capture timestamp is never silently promoted to an exact event timestamp.

Each session has a machine-checkable `chronology_reconciliation_status`: `PASS`, `PARTIAL`, or `FAIL`. The versioned reconciliation checks cover official-attempt disposition, duplicates, within-car ordering conflicts, timestamp conflicts, replay-only attempts, coverage gaps affecting the claimed window, and recorded source conflicts.

For Phase 3.5A, generic attempt start/end fields are not used for 2024 recovered anchors because their frozen meaning is broader than first timed-lap start and final timed-lap end. `chronology_constraints` therefore separates recorder capture, editorial event anchor, and timed-run endpoint fields. `event_time_quality` records precision, while `value_classification` and field-level provenance record origin. A deterministic duration calculation propagates the input anchor's uncertainty and cannot create an exact observation.

### Action evidence enums

- Withdrawal: `DIRECTLY_OBSERVED_WITHDRAWAL`, `RECONSTRUCTED_WITHDRAWAL`, `EDITORIALLY_DOCUMENTED_WITHDRAWAL`, `INFERRED_WITHDRAWAL`, `UNKNOWN`.
- Requeue: `DIRECTLY_OBSERVED_REQUEUE`, `RECONSTRUCTED_REQUEUE`, `INFERRED_PROBABLE_REQUEUE`, `UNKNOWN`.
- Lane: `DIRECTLY_OBSERVED_PRIORITY_LANE`, `DIRECTLY_OBSERVED_NON_PRIORITY_LANE`, `EDITORIALLY_DOCUMENTED_LANE`, `INFERRED_LANE`, `UNKNOWN`.
- Queue state: `OBSERVED_QUEUE_FACT`, `PARTIAL_QUEUE_FACT`, `INFERRED_QUALITATIVE_STATE`, `UNKNOWN`.

Inferred lane/requeue/queue values must use `INFERRED_UNCERTAIN`, include an assumption/note, and are ineligible as historical ground truth or supervised targets. The schema contains no default numeric fields for exact queue length, queue position, future wait, or future priority insertions. If a future source directly observes such a fact, store it as a `chronology_events.queue_fact_text` assertion with evidence rather than silently populating derived state.

Known replay gaps are explicit `COVERAGE_GAP` events. Derived state that crosses a gap has `chronology_complete_through_state = false`; no forward filling is allowed across the gap.

## 10. Fuel-strategy handling

`fuel_strategy_class` is a confounder annotation, never a fuel-mass estimate:

- `STANDARD_SINGLE_ATTEMPT_CONTEXT`: chronology positively supports an ordinary non-consecutive attempt context; exact fuel remains unknown.
- `SUSPECTED_CONSECUTIVE_ATTEMPT_STRATEGY`: chronology suggests an immediate consecutive attempt without confirmed strategy evidence.
- `CONFIRMED_CONSECUTIVE_ATTEMPT_STRATEGY`: official reporting/interview explicitly confirms the consecutive-attempt fuel strategy or no-refuelling plan.
- `UNKNOWN_FUEL_STRATEGY`: chronology is insufficient even to establish ordinary versus consecutive context.

Anything beyond the default requires field-level evidence. Timing proximity alone can support only `SUSPECTED`, never `CONFIRMED` or exact quantity. Flag special cases, group them separately, repeat analyses with them excluded, and vary their combined fuel/tyre/engine/thermal effect in sensitivity analysis. Do not isolate a fuel effect from these simultaneous conditions in v1.

## 11. Row-level eligibility

`row_eligibility` is evaluated per entity, `analysis_target`, and ruleset version. Supported targets are `FOUR_LAP_PERFORMANCE`, `LAP_PERFORMANCE`, `WITHIN_CAR_COMPARISON`, `SECTION_ANALYSIS`, `CHRONOLOGY`, and `QUEUE_CALIBRATION`. Year policy limits possible roles; it never grants eligibility by itself.

| Target/result field | Deterministic v1 rule |
|---|---|
| `eligible_four_lap_target` | Attempt is `A_COMPLETE`; four official or validly reconstructed qualifying laps exist; four-lap result is computable/observed; no unresolved value conflict; not a fabricated completion. Withdrawal/disallowance does not erase performance but must remain a status/censoring field. |
| `eligible_lap_target` | Lap is complete with an observed or validated reconstructed time/speed and no unresolved conflict. Partial section evidence alone fails. |
| `eligible_section_analysis` | Section sequence/version and value/unit are known; section is official observed evidence; row remains nested under attempt/lap. |
| `eligible_within_car_comparison` | At least two identifiable attempts for the same `entry_key` have known per-car order and compatible performance measures; comparison type records completed versus censored/partial. |
| `eligible_chronology_analysis` | Event/attempt has at least approximate time, bounded interval, or usable ordering; required interval is not inside/crossing an unresolved coverage gap. |
| `eligible_queue_calibration` | Row contains a directly observed/reconstructed queue-related event or usable attempt/service timing. Inferred lane/queue labels alone fail. |
| `eligible_core_training` | Within the row's explicit `analysis_target`, the entity passes evidence checks, year policy permits core use, and no unresolved critical conflict remains. This is false for section rows as independent samples. |
| `supporting_only` | Evidence is useful for annotation, section recovery, descriptive context, or a year restricted to supporting use, but fails core-training policy. |
| `robustness_only` | Row is retained for a prespecified robustness analysis because of weaker chronology, reconstruction, status, or year policy; reason code is mandatory. |

Examples are enforced as written: an incomplete 2020 attempt is not a four-lap target; a valid 2022 attempt may be supporting/robustness eligible; a 2023 post-cutoff attempt is performance eligible but chronology ineligible; a 2024 section row cannot establish repeated-attempt coverage.

## 12. Canonical truth and derived state

Canonical tables preserve observed/reconstructed attempts, laps, sections, events, official status, normalized forecast snapshots and values, and provenance. `forecast_snapshots` holds provider/model/version, issue time, supported availability time or uncertainty, valid interval, spatial locator, and extraction metadata. `weather_forecasts` holds variable values beneath that unique snapshot. They are append-corrected through evidence/conflict records; raw values are not overwritten by derived values.

`decision_state_features` is rebuilt for an explicit `state_as_of_time` or ordering boundary. Its nullable `forecast_snapshot_id` references the unique key in `forecast_snapshots`. A snapshot is eligible only when its supported `availability_time_utc <= state_as_of_time_utc`; unknown availability cannot pass that join. Permitted fields include current best result, provisional rank, cutoff/margin, elapsed/remaining time, prior observed attempts, most recent known attempt, known leaderboard completeness, and the latest eligible forecast. Each deterministic field cites a rule version and input snapshot/hash.

It does not contain exact future wait, future insertions, or unobserved queue positions. Qualitative inferred queue context, if retained, is clearly classified `INFERRED_UNCERTAIN` and cannot become a supervised historical target. On disagreement, canonical lower-level records control and the derived table is regenerated.

## DATASET DESIGN FREEZE DECISION

`READY FOR PIPELINE IMPLEMENTATION`

The v1 canonical tables, derived-state boundary, attempt identity, partial-run rules, evidence linkage, chronology uncertainty, fuel annotation, row eligibility, and year restrictions are sufficiently defined. Pipeline implementation must encode these rules without expanding the research scope or treating inferred queue state as ground truth.
