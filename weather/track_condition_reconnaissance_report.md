# Historical Track-Condition Evidence Reconnaissance

**Final status: `TRACK_CONDITION_RECONNAISSANCE_CORRECTED_AND_FROZEN`**

Phase 4A.5 covers only the five specified Indianapolis 500 Day 1 dates. This corrected review includes the retained PTSC-hosted `FirestoneTemperatures` workbook and its derived assets. The first Phase 4A.5 materialization omitted them; they were not intentionally excluded.

## Corrected verdict

- Recoverable numeric track/asphalt temperature is **FOUND_STRUCTURED in 5/5 years**, with **168 PTSC observations**: 2020 32, 2021 33, 2022 31, 2023 36, and 2024 36.
- An **INDYCAR-official structured track-temperature feed remains NOT_FOUND in 5/5 years**. The two official 2022 webpage anchors are editorial observations, not a structured feed.
- Structured time-indexed observed ambient temperature, humidity, wind, and barometer fields occur in **5/5 years** in PTSC. Coverage is not proven gap-free: each year has one gap over 30 minutes, and maximum gaps range from 45 to 75 minutes.
- PTSC wind, humidity, and barometer headers do not state units. One 2022 barometer value (`239.13`) remains raw while normalized pressure is missing under the existing quality rule.
- Tire thermal/pressure telemetry remains recoverable in **0/5 years**. PTSC surface sensors are not tire telemetry.
- Quantitative rubbering/track evolution and direct corner-level shade evidence remain recoverable in **0/5 years**.

## Source-authority separation

1. **INDYCAR/IMS official editorial pages** provide two numeric 2022 anchors and qualitative context. They do not provide a structured temperature feed.
2. **PTSC-hosted Firestone-named workbook** provides 168 structured observations. It is not labelled INDYCAR official. PTSC hosting and the filename are documented; local metadata does not independently authenticate authorship or the measurement operator.
3. **Secondary reporting** supplies the separate 2024 11:00 Firestone-engineer-attributed anchor.
4. **HRRR** remains a forecast layer. It is not observed track temperature and was not merged with PTSC.

## Structured PTSC coverage

| Year | Rows | Local first | Local last | Median interval | Maximum interval | Valid pressure |
|---:|---:|---|---|---:|---:|---:|
| 2020 | 32 | 2020-08-15 08:15:00-04:00 | 2020-08-15 16:50:00-04:00 | 15 min | 75 min | 32/32 |
| 2021 | 33 | 2021-05-22 08:45:00-04:00 | 2021-05-22 17:50:00-04:00 | 15 min | 75 min | 33/33 |
| 2022 | 31 | 2022-05-21 08:00:00-04:00 | 2022-05-21 16:15:00-04:00 | 15 min | 60 min | 30/31 |
| 2023 | 36 | 2023-05-20 08:15:00-04:00 | 2023-05-20 17:50:00-04:00 | 15 min | 75 min | 36/36 |
| 2024 | 36 | 2024-05-18 08:45:00-04:00 | 2024-05-18 17:52:00-04:00 | 15 min | 45 min | 36/36 |

These are target-date observations. Some begin before qualifying opened, so they are not all labelled as in-session attempt observations.

## Independent-anchor reconciliation

| Source | Time | Independent value | PTSC `track_f` | PTSC sensor average | PTSC track difference |
|---|---|---:|---:|---:|---:|
| INDYCAR official editorial | 2022-05-21 11:00 EDT | 85°F | 86°F | 85.625°F | +1.0°F |
| INDYCAR official editorial | 2022-05-21 12:30 EDT | 107°F | 105°F | 105.300°F | -2.0°F |
| Secondary, Firestone-engineer attribution | 2024-05-18 11:00 EDT | 94.6°F | 95°F | 94.950°F | +0.4°F |

All comparisons use exact local timestamps. No interpolation or forced agreement was applied. The 2022 official values remain 85°F and 107°F; the 2024 secondary value remains separately classified.

## Year coverage

| Year | Track temperature | Observed weather | Tire telemetry | Rubber/evolution | Shade/exposure |
|---:|---|---|---|---|---|
| 2020 | FOUND_STRUCTURED (32 PTSC rows) | FOUND_STRUCTURED (32 PTSC rows) | PARTIALLY_AVAILABLE | NOT_FOUND | NOT_FOUND |
| 2021 | FOUND_STRUCTURED (33 PTSC rows) | FOUND_STRUCTURED (33 PTSC rows) | PARTIALLY_AVAILABLE | NOT_FOUND | FOUND_QUALITATIVE_ONLY |
| 2022 | FOUND_STRUCTURED (31 PTSC rows) | FOUND_STRUCTURED (31 PTSC rows) | UNRESOLVED | NOT_FOUND | NOT_FOUND |
| 2023 | FOUND_STRUCTURED (36 PTSC rows) | FOUND_STRUCTURED (36 PTSC rows) | PARTIALLY_AVAILABLE | NOT_FOUND | FOUND_QUALITATIVE_ONLY |
| 2024 | FOUND_STRUCTURED (36 PTSC rows) | FOUND_STRUCTURED (36 PTSC rows) | PARTIALLY_AVAILABLE | NOT_FOUND | FOUND_QUALITATIVE_ONLY |

`FOUND_STRUCTURED` means machine-readable and time-indexed. It does not imply INDYCAR authority, gap-free continuity, uniform sampling, or attempt-level alignment. `NOT_FOUND` means not recoverable from the bounded evidence reviewed here; it does not prove the data never existed.

## Timing71 and tire findings

The retained Timing71 JSON scan found no target environmental or tire-thermal fields. Its `tyre-medium` marker supports tire-category context only. The missing 2022 replay remains unresolved. PTSC surface sensors remain track-condition measurements and are not used to infer tire thermal state.

## Scope controls

No canonical chronology, HRRR file, schema, model, simulator, queue timing, or earlier Pipeline Integrity Gate output was changed. No interpolation, observed-to-HRRR merge, rubber metric, or shade proxy was created.

## Outputs

- `weather/track_condition_evidence.csv` — 168 PTSC track observations plus retained official, IMS, and secondary observations.
- `weather/track_condition_coverage_audit.csv` — corrected coverage and PTSC interval/quality limits.
- `weather/track_temperature_anchor_reconciliation.csv` — exact-time comparison of independent anchors with PTSC.
- `weather/ptsc_source_block_verification.csv` — direct workbook date-block counts, including the excluded 2022 duplicate block.
- `weather/tire_telemetry_availability.csv` — tire assessment with PTSC surface sensors kept distinct.
- `weather/track_condition_source_catalog.csv` — source classes, provenance assets, and hashes.
- `weather/timing71_environment_field_audit.csv` — replay scan and explicit 2022 gap.
- `weather/track_condition_recon_qa.csv` — deterministic checks.
- `weather/track_condition_reconnaissance_freeze_manifest.csv` — frozen output inventory and SHA-256 hashes.
