# Indy 500 Day 1 Qualifying Historical Data Reconnaissance (2020–2024)

## Scope and decision rule

This audit asks whether the historical record can support (A) an attempt-level performance dataset and (B) a sequential decision simulator. It does not build either dataset or any model.

The source hierarchy used here is:

1. INDYCAR Official Results and Detailed Reports are the guaranteed performance and status backbone.
2. Public Timing71 recordings are supplementary chronology evidence. No conclusion depends on every legacy replay remaining available.
3. Official editorial accounts and the already-found 2024 live blog supply isolated time/action anchors.
4. NOAA HRRR is the primary historical decision-time forecast candidate. IEM-hosted NWS products and MOS are supplementary checks.

`ALL_ATTEMPTS` is used only when every attempt can be reconstructed with useful order or timestamps. An official PDF containing every attempt but sorted by speed is therefore `PARTIAL_CHRONOLOGY`, not `ALL_ATTEMPTS`.

## Direct answer

- **2 / 5 years realistically reach `ALL_ATTEMPTS + usable timestamps`: 2021 and 2024.** This is a realistic reconstruction judgment, not a claim that a row-level merged dataset has already been validated. Both have an official attempt inventory and a Timing71 recording spanning the scheduled session. Attempt times would be replay capture times and must be labelled as such.
- **0 / 5 years sufficiently support Lane / withdraw / requeue reconstruction for a sequential decision simulator.** Some isolated actions are documented, especially Power's 2021 withdrawal/priority-lane choice and VeeKay's 2024 forfeiture, but no year has systematic lane identity and queue-state history.

## Feasibility verdicts

### Gate A — Performance model: **FAIL**

The threshold is at least three years with all or near-all attempts, four-lap performance, usable timestamps, and status. Only 2021 and 2024 are realistic candidates. 2020 has an unrecorded 7 minute 15 second interval between two replay files; 2022 has no located Timing71 qualifying recording and the official report omits at least Sato's disallowed first run; 2023's replay stops about 58 minutes 38 seconds before the scheduled end.

### Gate B — Sequential decision simulator: **FAIL**

No year contains a systematic directly observed record of Lane 1/Lane 2, withdrawal time, queue entry, requeue choice, and subsequent attempt. Timing71 supplies current-qualifier, leaderboard, flag, and—especially in 2021—pit entry/exit observations, but does not expose lane or queue fields. Editorial/live reporting supplies only selected actions. The required three-year threshold is not approached.

## Year-by-year findings

### 2020

The official Results report has 59 rows and preserves repeated and non-final attempts. Forty-six rows contain four positive lap values; the remaining rows retain partial/zero-lap attempts and status labels such as Withdrawn, Waved Off, Retired, and Failed Attempt. Section Results add per-car lap/section detail, but neither report gives wall-clock time or global attempt order.

Timing71 has two public recordings: 14:54:55–18:35:15 UTC and 18:42:30–21:00:50 UTC. Together they bracket the scheduled session, but leave a **7 minute 15 second internal gap**. Any attempt or action in that gap is unknowable from the replay alone. Official editorial evidence gives isolated chronology (for example, Marco Andretti was reported out at about 1:30 p.m. ET), not a complete clock.

- Official attempt inventory: yes, 59 rows, treated as all reported Day 1 attempts.
- Lap 1–4: complete for 46 completed runs; explicit partial/zero values for the other 13.
- Timestamps/live leaderboard: partial due to the replay gap; capture timestamps are usable where recorded.
- Status: directly reported in the official Results PDF.
- Withdrawal/lane/requeue: withdrawal status is reported without exact time; lane and queue choices are unavailable; pit/out state is partial in the replay.
- Overall classification: `PARTIAL_CHRONOLOGY`, `OFFICIAL_REPORT`.

### 2021

The official Results report has 59 rows. INDYCAR's recap independently states that Dixon made the first run and 58 other attempts followed. Fifty-one rows contain four positive lap values; the others retain partial/zero-lap outcomes and statuses. The PDF footer mistakenly repeats 2020's Day 1/Pole Day dates, while its event/session header and official API identify May 22, 2021; the latter controls.

The Timing71 recording spans 15:54:57–22:00:54 UTC, covering the scheduled noon–5:50 p.m. ET session with margins at both ends. Its schema includes current qualifier, lap count, Lap 1–4 speeds, average speed, current rank, flags, full leaderboard snapshots, and pit entry/exit messages. A bounded check found the official Lap 4 value in same-car full snapshots for 50 of 51 completed rows; Marco Andretti's 39.2059 was not found in full snapshots. Deltas were not reconstructed, so this is a lower-bound presence check rather than a completeness proof.

Power's first run at 13:21 ET, withdrawal/priority-lane choice, and next run at 17:33 ET are documented editorially. The exact withdrawal instant is only bracketed before the later attempt. Lane choice is explicit for this isolated event, not for all decisions.

- Official attempt inventory: yes, 59.
- Lap 1–4: 51 completed four-lap rows plus explicit partial/zero values for eight.
- Timestamps/live leaderboard: realistically all/near-all from a full-span replay; exact row-level reconciliation remains to be performed.
- Status: official report plus replay state, with the report authoritative.
- Withdrawal/lane/requeue: partial, with one strong editorial action chain; pit movements are observed but do not prove queue/lane entry.
- Overall classification: `ALL_ATTEMPTS`, combining `OFFICIAL_REPORT` with `THIRD_PARTY_CAPTURE` chronology.

### 2022

The official Results report contains 44 rows, of which 40 have four positive lap values. It includes zero-lap Waved Off, No Attempt, and Incomplete rows, and a note that Newgarden's withdrawn times were reinstated. It is **not a complete inventory of executed attempts**: the official recap says Sato's 232.196 first attempt was disallowed and that he made a second attempt, while the report retains only the latter. The session was interrupted twice for a combined 2 hours 14 minutes and ended 60 minutes early.

No 2022 Day 1 Timing71 recording was found in the already-inspected public catalog/date query. No complete timestamp stream was otherwise discovered.

- Official attempt inventory: no; at least one executed/disallowed run is absent.
- Lap 1–4: available for the 40 completed rows retained by the report, but not for every executed attempt.
- Timestamps/live leaderboard: unavailable beyond isolated narrative times and conditions.
- Status: partial; the report preserves several statuses but not the omitted Sato run as a row.
- Withdrawal/lane/requeue: Newgarden withdrawal/reinstatement is known without a complete decision clock or lane/queue state.
- Overall classification: `PARTIAL_CHRONOLOGY`, `OFFICIAL_REPORT`.

### 2023

The official session exposes five reports. Critically, the original two-page Results PDF contains **84 attempt rows**, matching the official recap's total, while a later `MOD34` Results PDF contains only 34 final rows and the Overall Results report contains the final qualifiers. A consumer following only the visible/latest Results button could miss the 84-row file. Of its 84 rows, 69 have four positive laps; seven have three, seven have two, and one has one. Statuses include Withdrawn, Waved Off, Failed Attempt, Retired, On Bubble, and Bumped.

The Timing71 recording runs 14:57:18–20:51:22 UTC. The scheduled session extended to about 21:50 UTC, so the replay lacks the final **about 58 minutes 38 seconds**, a period containing late repeated attempts. Official articles provide selected anchors—Rosenqvist at 11:55 and 16:42 ET and the fact that five drivers made four attempts—but cannot restore every missing timestamp.

- Official attempt inventory: yes, 84, if the original Results PDF is used.
- Lap 1–4: all rows carry explicit four-column values, including zeros for incomplete laps; 69 completed all four laps.
- Timestamps/live leaderboard: partial; beginning covered, final ~58:38 missing.
- Status: directly reported.
- Withdrawal/lane/requeue: statuses are known, times and lane/queue actions are mostly unknown.
- Overall classification: `PARTIAL_CHRONOLOGY`, `OFFICIAL_REPORT`.

### 2024

The official Results report has 74 attempt rows, matching the official recap. Fifty-four rows have four positive laps; ten have three, three have two, four have one, and three have zero. These rows retain Waved Off, Failed Attempt, Bumped, Retired, Withdrawn, and On Bubble states. Section Results add detailed per-car sectors but no wall clock.

The Timing71 recording spans 14:57:56–21:51:59 UTC, covering the nominal 11 a.m.–5:50 p.m. ET session. It includes full/delta snapshots and current-qualifier fields. A bounded full-snapshot check found the official Lap 4 value for 53 of 54 completed rows; Herta's 38.8186 was not found in full snapshots. The capture's current-qualifier/lap fields can be stale, so replay state must be reconciled with the official report rather than accepted as ground truth. The already-found live blog supplies useful late-session timestamps and directly reports VeeKay forfeiting 29th at 22:43 BST before another run; it is third-party evidence.

- Official attempt inventory: yes, 74.
- Lap 1–4: all rows have explicit columns; 54 completed all four laps.
- Timestamps/live leaderboard: realistically all/near-all from the full-span replay, subject to reconciliation and capture-time uncertainty.
- Status: directly reported.
- Withdrawal/lane/requeue: selected forfeiture/late-run events are timed; systematic lane identity, queue entry, and pit return are unavailable.
- Overall classification: `ALL_ATTEMPTS`, combining `OFFICIAL_REPORT` with `THIRD_PARTY_CAPTURE` chronology.

## Official report inventory

For 2020, 2021, 2022, and 2024, the official API enumerates Results, Section Results, and Top Section Times. For 2023 it additionally enumerates Overall Results and two separate Results documents (84-row original and 34-row MOD34). No Day 1 Event Summary, Combined Results, Box Score, Lap Chart, Pit Stop Summary, or Leader Lap Summary was exposed in these session records.

The official JSON mirrors result rows and supplies session IDs, driver/entry IDs, four lap values, total time, average speed, and status. `PositionFinish` is report rank, not chronological attempt order; `ElapsedTime` is four-lap duration, not time of day; `modified_date` is publication metadata, not attempt time.

Section Results are valuable for performance reconstruction: 34 pages (2020), 36 (2021), 33 (2022), 36 (2023), and 64 (2024). They are per-car cumulative/section reports and do not establish global chronology. Top Section Times are ranked best-section summaries and are `SUMMARY_ONLY`.

## Weather feasibility

Historical decision-time weather is feasible independently of the replay question. The public NOAA HRRR archive covers data since 2014 and is the primary candidate. Small index files were verified for all five qualifying dates; the sampled surface forecast contains 2 m temperature and humidity, 10 m U/V wind, surface pressure, total cloud cover, downward shortwave radiation, accumulated precipitation, and surface CAPE. Retrieve only cycles that were available before each decision and use positive forecast lead times; S3 object metadata is not proof of original release time.

HRRR does not directly forecast track temperature and deterministic precipitation/CAPE is not a calibrated storm probability. IEM-hosted issued NWS Area Forecast Discussions and MOS at KIND are supplementary context/cross-validation. The saved 2020 MOS sample includes runtime and forecast-valid time, temperature, dew point, cloud, wind, and precipitation/thunder probability fields; the saved 2024 AFD is an issued NWS text product. Weather sources are not used to upgrade qualifying chronology classifications.

## Remaining gaps and stopping point

The feasibility decision no longer depends on broader searching. The unresolved work is bounded reconciliation, not reconnaissance: apply Timing71 deltas for 2021 and 2024, map replay qualifier transitions to the official attempt rows, quantify capture-time uncertainty, and retain unmatched rows as unknown. That work belongs to a future ingestion/validation phase. Modelling should remain paused because Gate A and Gate B both fail under the specified thresholds.
