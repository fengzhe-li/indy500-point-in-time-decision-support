# R2A Official Lane / Queue / Live Leaderboard Resource Reconnaissance

**Final status:** `OFFICIAL_LANE_QUEUE_LIVE_RESOURCE_RECON_PARTIAL`

## Scope and result

This bounded resource audit used the rescued INDYCAR Results bundle and Day 1 API responses, the rescued current INDYCAR leaderboard application and JSON feeds, and the local Timing71 captures. It did not reconstruct queue, lane, leaderboard, cutoff, or chronology state and did not mutate canonical or frozen outputs.

The official Results API remains the confirmed historical source for 2020–2024 final result/status records and its `SessionReports` links. The recovered current first-party leaderboard architecture exposes polling JSON feeds for timing, track activity, schedules, configuration, and driver metadata. No confirmed historical selector was found for those live feeds. The single bounded test of `timingscoring-ris.json?sessionid=6382` returned current `EventSessionID=6736`, so that parameter did not recover the requested 2024 session.

## Frontend and endpoint findings

- `EventsSessionDetails?id=<EventsSessionID>` is requested on session selection and is not polled. It returns session metadata, final result records, and `SessionReports`.
- The current leaderboard application polls `tsconfig.json` and `timingscoring-ris.json` every 5 seconds; it polls track-activity and schedule feeds every 10 seconds; driver metadata is fetched on mount.
- The current request URLs use only a cache-busting timestamp. Session IDs appear in response objects, but no working historical request selector was confirmed.
- No SignalR route was found. `tsconfig.track_map` contains `wss_uri` and `wss_key`, but both are empty in the rescued current configuration. This supports architecture review only.
- No source-map reference or historical page/session route was observed in the rescued current application shell and chunks.
- No target lane, priority-lane, queue membership/order, requeue, cutoff/bump-line, or race-control message field was observed in the searched official structured responses.

## Report-type architecture

The Detailed, Summary, and Officiating labels are dynamic UI categories populated from the `SessionReports` array returned by `EventsSessionDetails`; they are not independent report endpoints in the recovered bundle. For the five Day 1 sessions, the arrays contain Results, Section Results, and Top Section Times, plus an Overall Results document and an additional Results variant in 2023. No additional Summary, Officiating, race-control, qualifying-order, or session-chronology document was found in the searched arrays. This is a scoped negative finding, not proof that such documents never existed.

The current schedule feed has a separate event-level `qualification_order` link field (including a current Indianapolis 500 qualifying-draw PDF), which confirms that this document class exists in the current first-party schedule architecture. No 2020–2024 Day 1 value was recovered in the searched local payloads, so it remains an archive target rather than historical evidence.

## Timing71 relationship

Timing71 remains `THIRD_PARTY_CAPTURE` and `ARCHITECTURAL_CLUE_ONLY`. The 2020 and 2021 manifests identify `http://racecontrol.indycar.com/` as the upstream source and specify 5-second polling; later captures expose `Current qualifier`, four lap-speed fields, average speed, and current rank. The captures do not preserve an exact upstream request endpoint or an official payload that can be promoted.

## Historical coverage

- 2020, 2021, 2023, and 2024 have partial contemporaneous leaderboard/rank/timestamp evidence only through the already held third-party Timing71 captures.
- 2022 has official historical final results/status plus current official live-feed architecture, but no historical live payload in the searched resources.
- All five years have partial withdrawal information through official final status fields, without event time. Lane, queue/order, contemporaneous cutoff, and race-control event coverage remain `NOT_FOUND_IN_SEARCHED_SOURCES` for all five years.

## Archive targets

The archive manifest limits any later lookup to exact high-value URLs already established by the official architecture: the former race-control page, current leaderboard application, live timing JSON, track-activity JSON, and configuration JSON, each paired with the known Day 1 date and `EventsSessionID`. R2A did not crawl those targets.

## QA

The QA table contains all eleven required zero assertions. It also compares 225 pre-R2A protected file hashes, validates registry statuses and target-year completeness, records the historical-session probe, and records the existing pipeline regression result (`30/30`, `PASS`). All R2A QA assertions pass when this report is generated.

The negative conclusion throughout is limited to **not found in the resources searched in this phase**.
