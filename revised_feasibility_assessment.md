# Revised Feasibility Assessment

## Decision

**Recommendation: `PROCEED WITH REDUCED SCOPE`.**

The clarified prototype is feasible as an uncertainty-aware comparison of two actions, provided it is framed as a probabilistic decision simulator rather than a replay of the true historical queue. Historical performance modelling and probabilistic simulation both receive `CONDITIONAL PASS`. Exact historical queue reconstruction remains `FAIL`.

Next-stage eligibility is conditional on a bounded data-validation stage showing that:

1. official attempt rows can be represented without treating partial laps or section rows as independent samples;
2. 2021 and 2024 Timing71 qualifier transitions can be reconciled to official attempts with documented timestamp uncertainty and unmatched cases left unknown;
3. weather features use forecasts available at the historical decision time;
4. queue behaviour is declared stochastic, with its weakly identified parameters subjected to sensitivity analysis; and
5. conclusions are reported as policy comparisons under stated assumptions, not as recovered historical counterfactual truth.

No model or ingestion pipeline is created in this assessment.

## Original strict gates remain unchanged

| Historical-reconstruction gate | Verdict | Reason |
|---|---|---|
| Gate A - performance model | **FAIL** | The original gate required at least three years with all/near-all attempts, Lap 1-4 performance, usable timestamps, and status. Only 2021 and 2024 realistically meet the combined requirement. 2020 has a 7m15s replay gap, 2022 has no located replay and an omitted disallowed attempt in Results, and 2023 lacks the final ~58m38s of replay. |
| Gate B - sequential decision simulator | **FAIL** | No three years, or even one full year, directly observe systematic withdrawal time, Lane 1/Lane 2 action, queue position, requeue chronology, next-attempt time, and live state together. |

These verdicts judge strict historical reconstruction. They are not relaxed or overwritten by the practical classifications below.

Failure of the strict gates does not invalidate the clarified prototype. It changes the estimand and the strength of claims: the prototype can estimate outcome distributions under explicitly assumed queue processes, but cannot claim to reproduce the exact choice set, queue state, or counterfactual wait faced by every historical entrant.

## Practical year classification

### 2020 - `CORE_PERFORMANCE_YEAR`, `PARTIAL_CHRONOLOGY_YEAR`

- **Attempts and performance:** The official Results report contains 59 reported attempts. Forty-six are completed four-lap runs; the other 13 retain partial/zero-lap columns and statuses. Section Results contain continuous per-car lap sequences, including repeated runs and partial later sequences.
- **Timestamp quality:** Timing71 covers most of the session in two files but has an internal 7m15s gap. Recorded events have usable capture timestamps; events in the gap remain unknown.
- **Repeated-attempt use:** Strong for within-car performance comparisons because repeated official attempts are retained. Weather alignment is usable only outside the replay gap or with broader time intervals.
- **Chronological-state use:** Partial. Recorded leaderboard/track state can support robustness checks, but a complete historical state path cannot be asserted.
- **Queue calibration:** Weak. Pit/out observations may inform coarse timing, but lane and queue entry are not observed.
- **Major exclusion:** Do not impute events inside the replay gap as if observed.

### 2021 - `CORE_PERFORMANCE_YEAR`, `CORE_CHRONOLOGY_YEAR`, `QUEUE_CALIBRATION_ONLY`

- **Attempts and performance:** The official report and recap support 59 attempts. Fifty-one completed all four laps; eight are partial/zero-lap rows. Section Results preserve repeated per-car sequences and partial runs.
- **Timestamp quality:** The Timing71 replay spans the scheduled session and provides qualifier, lap, leaderboard, flag, and pit-message state. Times are recorder/capture times, not official transponder event times. Row-level reconciliation remains required.
- **Repeated-attempt use:** Strongest year. Within-car comparisons are realistic, including Power's documented first attempt, withdrawal/priority-lane action, and later attempt.
- **Chronological-state use:** Core, subject to validation of deltas and stale/unmatched states.
- **Queue calibration:** Only coarse calibration is justified. Pit entry/exit is directly observed for some events, but queue position and lane entry are not.
- **Major exclusion:** Do not generalize Power's explicitly reported lane choice to unreported attempts.

### 2022 - `PARTIAL_PERFORMANCE_YEAR`

- **Attempts and performance:** Results has 44 rows and 40 completed four-lap rows, but omits Sato's disallowed first 232.196 attempt. The official Section Results do preserve two Sato attempt blocks; the first block contains four sectioned laps consistent with the disallowed run. This can recover its performance when cross-referenced to the official recap, but does not prove that no other executed attempt is absent.
- **Timestamp quality:** No located Timing71 replay; only sparse narrative anchors and interruption timing.
- **Repeated-attempt use:** Partial. Repeated section sequences exist, but global order and decision time are unavailable.
- **Chronological-state use:** Low. This year can contribute untimed performance/robustness information, not a full state path.
- **Queue calibration:** Not supported by the available evidence.
- **Major exclusion:** Treat the true executed-attempt total as unknown and do not use untimed rows for attempt-level decision-time weather matching.

### 2023 - `CORE_PERFORMANCE_YEAR`, `PARTIAL_CHRONOLOGY_YEAR`

- **Attempts and performance:** The original official Results PDF contains all 84 reported attempts. It has 69 four-lap, seven three-lap, seven two-lap, and one one-lap row. The later MOD34 file must not replace it. Section Results preserve repeated per-car sequences and partial runs.
- **Timestamp quality:** Timing71 covers the beginning and middle but ends about 58m38s before the scheduled close. Official reporting gives selected time anchors only.
- **Repeated-attempt use:** Strong for performance and status; partial for weather-aligned chronology.
- **Chronological-state use:** Partial because the missing final period contains important late repeated attempts.
- **Queue calibration:** Weak and restricted to the recorded interval; no lane identity or complete queue state.
- **Major exclusion:** Late-session attempts must not receive invented exact times or reconstructed leaderboard states.

### 2024 - `CORE_PERFORMANCE_YEAR`, `CORE_CHRONOLOGY_YEAR`, `QUEUE_CALIBRATION_ONLY`

- **Attempts and performance:** The official Results report has 74 attempts: 54 four-lap, ten three-lap, three two-lap, four one-lap, and three zero-lap rows.
- **Timestamp quality:** Timing71 spans the nominal session and can provide qualifier/leaderboard chronology. Some inspected fields are stale, so the replay must be reconciled to the official attempt backbone. The live blog adds selected timestamped action anchors.
- **Repeated-attempt use:** Strong from Results plus full-span chronology, pending row mapping.
- **Chronological-state use:** Core for modelling purposes, with capture-time and stale-state uncertainty explicitly represented.
- **Queue calibration:** Selected forfeiture and late-run events can inform coarse distributions only. Systematic lane, queue, and pit-return paths are unavailable.
- **Major exclusion:** The 2024 Section Results report represents only one selected four-lap set per car and does not recover all repeated/aborted attempts.

`LOW_UTILITY` is not assigned to any year: even 2022 contributes official performance and section evidence. `QUEUE_CALIBRATION_ONLY` is attached to 2021 and 2024 specifically to limit how their queue-related observations may be used; it does not negate their core performance/chronology roles.

## A. Performance modelling feasibility - `CONDITIONAL PASS`

### Usable years and sample structure

- **Core performance:** 2020, 2021, 2023, and 2024.
- **Core timestamp/weather alignment:** 2021 and 2024 after replay-to-report reconciliation.
- **Partial timestamp/weather alignment:** 2020 and 2023 outside their documented gaps.
- **Supporting/robustness performance:** 2022, including section-based recovery of Sato's disallowed first run, but without a complete clock.

The official reports contain 320 rows in total across the five years, while the 2022 report is known to omit at least one executed attempt. The audit identifies 260 completed four-lap report rows, with the remaining report rows carrying partial or zero-lap outcomes. These are rows, not independent observations: attempts are nested within car, driver, team, and year, and multiple rows often arise from the same decision process.

Within-driver/within-car repeated-attempt modelling is realistic for the four core performance years. It is especially useful for differencing relatively stable car/team factors, but repeat attempts are endogenous: slower, bumped, or strategically exposed cars are more likely to run again, while fast first-run cars often stop. Any model must distinguish prediction from causal attribution.

### Limitations and selection risks

- Re-attempt selection depends on prior speed, rank, remaining time, perceived weather, and team confidence. A repeated-attempt subset is therefore not representative of all cars or all opportunities.
- Withdrawal and waved-off outcomes create informative censoring. Conditioning only on completed four-lap runs would discard downside events central to the decision.
- Missing exact timestamps in 2020, 2022, and late 2023 reduce their usefulness for precise weather matching; they do not make their performance rows unusable for baseline, hierarchical, or robustness analyses.
- Replay timestamps represent capture time and may lag the underlying event. Weather matching should use uncertainty windows when exact alignment cannot be validated.
- Section timing can describe where a partial run deteriorated, but cannot turn an aborted run into an observed valid four-lap average.
- Year-specific rules, track conditions, engine/team effects, and small repeated-attempt clusters limit transportability.

The verdict is conditional because the useful sample exists, but robust modelling depends on preserving outcome/status censoring, handling clustered repeated measures, and validating timestamp joins before using fine-grained weather effects.

## B. Exact historical queue reconstruction feasibility - `FAIL`

The available sources cannot recreate the true Lane 1, Lane 2, queue position, withdrawal state, requeue time, or future priority-lane insertions at each decision point.

Direct observations include selected editorial lane/withdrawal events, some Timing71 pit entry/exit messages, current-qualifier transitions, flags, and leaderboard snapshots. They do not establish where a car entered a physical queue, its position, which lane it selected, whether a pit movement was a requeue action, or which future cars would insert through the priority lane. Exact withdrawal instants are usually absent. Consequently, missing queue state cannot be back-filled from attempt timestamps without unsupported inference.

This verdict concerns observability of historical truth and remains separate from probabilistic simulation.

## C. Probabilistic sequential decision simulation feasibility - `CONDITIONAL PASS`

A useful simulator can compare the distribution of outcomes under:

- retain the current result and enter/use the non-priority queue; and
- withdraw the current result and enter/use the priority queue.

It must treat wait time, future priority insertions, interruptions, and next-attempt performance as random variables rather than known future values.

### Directly calibratable quantities

- Four-lap and lap-by-lap performance distributions from official Results.
- Partial-run/status frequencies in the official attempt reports.
- Per-car section and lap durations where Section Results retain them.
- Attempt arrival/order and evolving leaderboard over the covered 2021 and 2024 replays, after reconciliation.
- Partial arrival/state histories in the covered portions of 2020 and 2023.
- Flag/interruption periods where replay or official reporting records them.
- Historical decision-time HRRR forecasts, with NWS/IEM and MOS as supplementary checks.

### Weakly calibratable quantities

- Queue waiting-time distributions conditional on session phase.
- Rate and timing of future priority-lane insertions.
- Probability that pit exit/entry corresponds to a specific requeue decision.
- Withdrawal propensity by rank and remaining time.
- Dependence between team information, queue choice, weather expectation, and subsequent performance.

These quantities can be bounded or informed by the observed attempt process, but the data cannot uniquely identify the actual lane-specific mechanism.

### Explicit assumptions

- A declared service discipline for priority and non-priority queues.
- Stochastic arrival processes for new/repeated attempts and priority insertions.
- A service-time distribution incorporating four-lap runs, partial attempts, track clearing, and interruptions.
- A mapping from replay capture time to event-time intervals.
- A rule for how withdrawal removes the current qualifying protection and how failed/partial attempts affect state.
- No assumption that future queue length, weather, or competitor decisions are known to the historical decision-maker.

### Required sensitivity analysis

Vary priority-insertion intensity, lane service discipline, queue length at decision, service-time dispersion, yellow/red-flag downtime, replay timestamp lag, weather forecast error, performance residual variance, withdrawal downside, and correlations among competitor decisions. Results should be reported across plausible regimes, including adverse regimes for the chosen action.

Useful decision support is still possible: the simulator can answer whether an action is robustly preferred, preferred only under short-wait assumptions, or dominated once downside risk is included. It cannot claim that a simulated wait distribution is the exact queue the driver historically faced. The conditional verdict depends on presenting conclusions in this assumption-aware form.

## Official section-data recovery assessment

The public file name in all five session inventories is **Section Results**; the PDF's internal report title is **Section Data Report**.

| Year | Section report exists | Repeated attempts represented | Partial qualifying laps preserved | Can help recover missing complete-lap performance | Exact official file name |
|---|---|---|---|---|---|
| 2020 | yes | yes | yes | partial | `indycar-sectionresults-quals-day1.pdf` |
| 2021 | yes | yes | yes | partial | `indycar-sectionresults-quals-day1.pdf` |
| 2022 | yes | yes | no | yes | `indycar-sectionresults-quals-day1.pdf` |
| 2023 | yes | yes | yes | partial | `indycar-sectionresults-quals-day1.pdf` |
| 2024 | yes | no | no | no | `indycar-sectionresults-quals-day1.pdf` |

For 2020-2023, the reports use continuous per-car lap numbering across multiple track outings. Numbers beyond the first five show repeated attempts. Truncated later qualifying groups preserve partial-run information in 2020, 2021, and 2023. In 2022, the reported zero-lap waved-off/incomplete cases do not leave qualifying-section observations in this report, so partial-lap preservation is marked `no`. The 2022 Sato page is nevertheless especially useful: it contains two complete attempt groups, and its first four laps recover section/lap performance corresponding to the disallowed run omitted as a Results row. The `yes` recovery classification for 2022 is limited to this known case and is not a claim that every potentially omitted attempt is recoverable.

The 2024 format is materially different. Each car is split over two pages because the section table is wider; the two pages complete the same Lap 1-5 record. For cars known to have repeated attempts, the report still shows only one selected four-lap group plus pit/return information. It therefore does not preserve the repeated or waved-off attempt inventory. A few incomplete cooldown/pit-return sectors do not count as preserved partial qualifying attempts.

For every year, section rows are components of an attempt, not independent training samples. Section data can recover observed portions of a partial run or, in the special 2022 case, performance omitted from the main result table. It cannot manufacture the unobserved remainder of an aborted attempt or convert it into a valid four-lap qualifying result.

## Fuel-load confounding - `MODERATE_MANAGEABLE_CONFOUNDER`

Standard qualifying attempts are short four-lap runs, so plausible fuel variation is narrower than in long race stints. The official section reports also show compact attempt blocks separated by pit/return activity. This limits, but does not eliminate, fuel variation. Teams may carry extra fuel for an immediate additional attempt, and exact fuel mass is not observed in the available data.

The likely direction of bias is that a heavier first run depresses speed, while a consecutive later run may benefit from lower fuel mass. A naive before/after comparison could attribute that improvement to weather, driver learning, or queue strategy. The opposite can also occur because the later run may face worse tyres, engine/thermal state, or track temperature. These factors are simultaneous and prevent exact fuel attribution.

Fuel load therefore adds structured noise and can confound the size of within-car effects, but it does not by itself destroy the research question. The central decision comparison concerns outcome distributions under two queue/withdrawal actions, not identification of a pure causal fuel coefficient.

Special consecutive-attempt cases should be flagged when chronology or reporting supports them. The preferred treatment is to group them as a distinct run-context category and vary their assumed fuel/thermal effect in sensitivity analysis. Analyses should also be repeated with such cases excluded. They should not be assigned an inferred fuel mass, and they should not automatically be pooled with ordinary pit-separated re-attempts.

## Final research scope

Proceed with official Results as the performance/status backbone. Use 2020, 2021, 2023, and 2024 for core performance work; use 2021 and 2024 as the primary chronology/weather-aligned years; use the observed portions of 2020 and 2023 for robustness; and use 2022 as supporting untimed performance/section evidence.

The prototype is eligible to advance only as a probabilistic, uncertainty-aware decision-support study. Exact historical queue replay, exact historical counterfactual claims, inferred lane labels, and inferred fuel mass remain outside the defensible scope.
