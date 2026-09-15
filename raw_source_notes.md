# Raw source notes

These notes record what was directly inspected during reconnaissance. They deliberately separate direct observations from reconstruction hypotheses.

## Official INDYCAR results backbone

The public results frontend calls:

- `GET /api/results/SeasonDropDown?id=b856a4f1-e85c-4fac-8c36-fd58d962227a`
- `GET /api/results/EventsSessionDetails?id={session_id}`

Day 1 session IDs are 5771 (2020), 5838 (2021), 6033 (2022), 6202 (2023), and 6382 (2024). Saved responses are in `evidence/official_session_YYYY.json`.

The JSON fields inspected include driver/entry IDs, `PositionFinish`, `ElapsedTime`, `SpeedAvg`, `QualLap1`–`QualLap4`, and `Status`. Interpretation safeguards:

- `PositionFinish` is the report rank, not attempt sequence.
- `ElapsedTime` is the four-lap duration, not a wall-clock timestamp.
- `modified_date` belongs to the published document and is not an event time.
- Later API rows for 2023/2024 are final standings; use the detailed PDF for repeated attempts.

### Report enumeration by year

- 2020: Results; Section Results; Top Section Times.
- 2021: Results; Section Results; Top Section Times.
- 2022: Results; Section Results; Top Section Times.
- 2023: Overall Results; original Results (84 rows); modified Results `MOD34` (34 rows); Section Results; Top Section Times.
- 2024: Results; Section Results; Top Section Times.

No Event Summary, Combined Results, Box Score, Lap Chart, Pit Stop Summary, or Leader Lap Summary was present in these Day 1 `SessionReports` arrays.

PDF row/lap checks:

| Year | Detailed rows | Positive-lap distribution | Interpretation |
|---|---:|---|---|
| 2020 | 59 | 46 rows with four positive laps | Remaining 13 are partial/zero-lap reported attempts |
| 2021 | 59 | 51 rows with four positive laps | Remaining 8 are partial/zero-lap reported attempts |
| 2022 | 44 | 40 rows with four positive laps | Four partial/zero rows; not all executed attempts because Sato's disallowed first run is absent |
| 2023 | 84 | 69×4 laps; 7×3; 7×2; 1×1 | Original PDF is the full reported inventory; MOD34 is not |
| 2024 | 74 | 54×4; 10×3; 3×2; 4×1; 3×0 | Full reported inventory |

The 2023 PDF's second page was rendered and visually checked; rows 83–84 show Grosjean and Newgarden Waved Off with partial lap values. This confirms that zeros in the detailed report represent incomplete laps rather than missing columns.

Section Results page counts were 34, 36, 33, 36, and 64 for 2020–2024. They provide per-car section details and relative pit-out/start-finish/pit-in durations, but no absolute clock or cross-car ordering. Top Section Times rank best sectors and are summaries.

## Timing71 legacy recordings

The public archive catalog responded anonymously at `https://archive.timing71.org/replays`. The documented `/download/{id}` route returned a server-side path error for the tested 2024 record, but the public object URL listed by the catalog was downloadable. No authentication or access control was bypassed.

Catalog records:

| Year | Replay ID | Nominal UTC interval | Known limitation |
|---|---|---|---|
| 2020 | `027333f0270d41118f6eeccb9ddd25e5` | 14:54:55–18:35:15 | first part |
| 2020 | `027333f0270d41118f6eeccb9ddd25e5:1` | 18:42:30–21:00:50 | 7m15s after first part ends |
| 2021 | `3a2e3c4a0453452f8a5ab50b967bf62b` | 15:54:57–22:00:54 | full scheduled span |
| 2022 | none found | — | unavailable in inspected catalog/date query |
| 2023 | `ceb845a6-cc87-48c3-838a-01e851f0b415` | 14:57:18–20:51:22 | final ~58m38s absent |
| 2024 | `4146f406-154f-4065-bd5f-10d0bd349b77` | 14:57:56–21:51:59 | full nominal span; some stale state |

Replay timestamps are recorder/capture timestamps. They are suitable for event ordering and approximate decision time after validation, but must not be described as official transponder timestamps.

The 2021 manifest names RaceControl as the source and declares a five-second poll interval. It defines current qualifier, lap count, four lap speeds, average speed, and rank. Full snapshots also carry leaderboard state and flags; messages include pit entry/exit. The archive contains full snapshots and intervening delta files.

The 2024 manifest declares the same qualifier data family. In inspected snapshots, pit count was not a useful route/queue signal and some qualifier fields remained stale. The saved files `timing71_2024_manifest.json`, first/last snapshots, and `recon_sample_checks.json` are representative evidence, not an extracted dataset.

One-off lower-bound checks searched full snapshots for the official fourth-lap value on the same car; deltas were not applied:

- 2021: 50 of 51 completed official rows observed; Marco Andretti 39.2059 not found in full snapshots.
- 2024: 53 of 54 observed; Colton Herta 38.8186 not found in full snapshots.

A match only proves the value appeared somewhere in a full snapshot. It does not by itself identify a unique attempt start or prove complete chronology.

## Official/editorial chronology anchors

2020 INDYCAR recap: <https://www.indycar.com/news/2020/08/08-15-indy-500-day-1-quals>. It reports Andretti made one attempt, Herta three, and Dixon four, with selected outcomes. A related official article places Andretti on track at about 1:30 p.m. ET. These are sparse anchors.

2021 INDYCAR recap: <https://www.indycar.com/News/2021/05/05-22-Day1-Qualifying>. It reports Dixon first followed by 58 other attempts. It places Power's first run at 1:21 p.m. ET and second at 5:33 p.m.; between them he withdrew the first time and used the priority/fast lane. The withdrawal instant is not stated. It reports Palou's crash at 3:35 p.m.

2022 IMS recap: <https://www.indianapolismotorspeedway.com/news-multimedia/news/2022/05/21/05-21-VeeKay-Leads-Day1Quals>. It states Sato's first 232.196 attempt was disallowed and a second attempt was required. It also reports two rain/lightning interruptions totalling 2h14m and an end 60 minutes early; the first 15 minutes had an 85°F track and the track was 107°F by 12:30 p.m. These facts show why the 44-row PDF is not a complete executed-attempt inventory.

2023 INDYCAR recap: <https://www.indycar.com/News/2023/05/05-20-FirstDayQuals>. It reports 84 attempts; Rosenqvist's first at 11:55 a.m. and second at 4:42 p.m.; and five drivers making four attempts. Those anchors do not fill the replay's missing final hour.

2024 INDYCAR recap: <https://www.indycar.com/News/2024/05/05-18-Quals-Day1>. It reports 74 attempts and selected chronology: VeeKay's crash at 11:14 a.m., later waved-off and completed runs, and Rahal's final attempt just before 5:50 p.m. The Crash.net live blog at <https://www.crash.net/indycar/live/indianapolis-500-qualifying-it-happened> has timestamped selected events and leaderboard snapshots; times display in BST. It reports VeeKay forfeiting 29th at 22:43 BST. It is supplementary third-party evidence.

## Official RaceControl/App timing

The public current feed `https://indycar.blob.core.windows.net/racecontrol/timingscoring-ris.json` was readable and contains current timing results and event/session identifiers. Other current feed names are referenced by the public browser client. No public historical query mechanism for the target sessions was established from the already-inspected interface. Therefore the official live endpoint is `UNAVAILABLE` for 2020–2024 historical coverage; this does not claim INDYCAR lacks a private archive.

## HH Timing / MyLaps RIS capability

HH Timing's published IndyCar documentation at <https://help.hhtiming.com/series-specific-info/indycar/> documents current-session history, lap and section timing, telemetry, per-car/per-lap export, raw messages, and replay/export capability. Access uses credentials supplied by INDYCAR, and no public historical captures were discovered. It is capability/schema evidence only and cannot satisfy either gate.

## Historical decision-time weather

Primary source: NOAA HRRR open archive, documented at <https://registry.opendata.aws/noaa-hrrr-pds/>. The archive is public, hourly, 3-km, and extends back to 2014. The following small `12z f03` GRIB index files were retrieved to verify actual object availability:

- `evidence/hrrr_20200815_f03.idx`
- `evidence/hrrr_20210522_f03.idx`
- `evidence/hrrr_20220521_f03.idx`
- `evidence/hrrr_20230520_f03.idx`
- `evidence/hrrr_20240518_f03.idx`

The indexes list fields needed for the research, including 2 m temperature/RH, 10 m U/V winds, surface pressure, accumulated precipitation, surface CAPE, total cloud cover, and downward shortwave radiation. An actual decision-time query must select the latest model cycle demonstrably available before the decision and a forecast hour whose valid time covers the decision. The `12z f03` files here are availability samples, not a prescription for every attempt.

Supplementary sources:

- IEM MOS API documentation: <https://mesonet.agron.iastate.edu/cgi-bin/request/mos.py?help>. `evidence/mos_2020_sample.csv` confirms runtime/valid-time fields and KIND temperature, dew point, cloud, wind, and precipitation/thunder guidance.
- IEM NWS text archive: <https://mesonet.agron.iastate.edu/nws/text.php>. `evidence/nws_2024_sample.txt` is an issued Indianapolis Area Forecast Discussion retrieved with a cutoff before the session.

Neither supplementary source replaces HRRR's gridded forecast. HRRR does not directly predict track surface temperature; that variable would require a separate physical/empirical treatment later.

## Final conservative classifications

- 2020: `PARTIAL_CHRONOLOGY` / `OFFICIAL_REPORT`.
- 2021: `ALL_ATTEMPTS` / `OFFICIAL_REPORT`, with Timing71 `RAW_EVENT_STREAM` / `THIRD_PARTY_CAPTURE` providing chronology.
- 2022: `PARTIAL_CHRONOLOGY` / `OFFICIAL_REPORT`.
- 2023: `PARTIAL_CHRONOLOGY` / `OFFICIAL_REPORT`.
- 2024: `ALL_ATTEMPTS` / `OFFICIAL_REPORT`, with Timing71 `RAW_EVENT_STREAM` / `THIRD_PARTY_CAPTURE` providing chronology.

The combined classification cites the official backbone as the controlling evidence. Timing71 classifications are separately recorded in `source_catalog.csv` so third-party captures are not represented as equivalent to official data.
