# Phase 4 QA Report

| Check | Result |
|---|---|
| Phase 1-3 regression tests | **PASS** — all 46 retained tests re-run unmodified |
| API tests | **PASS** — 17/17 (`tests/test_api.py`: 14 required items + 3 extra 404/error-handling checks) |
| Frontend tests | **PASS** — 7/7 (`frontend/src/App.test.tsx`, vitest + React Testing Library) |
| Full test total | **70 / 70 PASS** (63 Python via `unittest discover` + 7 frontend via `vitest run`) |
| V2 immutability | **PASS** — 32/32 frozen dependencies byte-identical, re-checked after all Phase 4 work |
| V3↔V2 behavioural regression | **PASS** — re-run after all Phase 4 work |
| Future-information leakage | **PASS** — `test_14_no_future_information_leakage_in_replay_api_state` confirms decision-time events never carry `observed_delta_v` and always precede the later `FUTURE_ATTEMPT_OBSERVED`/`PREDICTION_SCORED` events for the same case |
| Frontend scientific recomputation | **NO** — `app/replay_service.py`'s module docstring documents the design choice; the frontend only calls `services/api.ts`, which only does `fetch()` against the FastAPI routes; no `final_v2_adapter`, `shadow_engine`, MC, or physics code is imported anywhere under `frontend/` (verified by inspection — there is no Python runtime in the browser bundle to begin with) |
| Queue model introduced | **NO** |
| Strategy recommendation introduced | **NO** |
| New scientific model introduced | **NO** |
| Illustrative case correctly labelled | **PASS** — `ILLUSTRATIVE ONLY — NOT AGGREGATE VALIDATION EVIDENCE` banner on the replay page; `counts_toward_aggregate_validation: false` visible on both the outlook and evidence pages; verified by test 8 |
| Abstention visible | **PASS** — abstention reason breakdown bar chart + full case table on the Validation page; abstained events remain navigable (not hidden) on the replay timeline |
| Historical scoring vs inference support distinguished | **PASS** — rendered as two separate labelled rows everywhere a prediction is shown (Applicability panel, Evidence page header); verified by API test 17-equivalent (`test_17_historical_scoring_support_is_distinct_from_inference_support` in Phase 3 suite) and frontend test 7 |
| One-command start | **PASS** — `scripts/run_v3_app.sh` starts both `uvicorn` and `npm run dev`, verified manually (both processes started, health-checked, and screenshotted, then stopped) |
| Offline historical demo | **PASS** — the API never makes an outbound network call; every route reads local files under `output/replay/`, `output/qa/`, `output/phase3_freeze/`, and `config/v3_config.yaml` |
| Visual QA | **PASS** — 4 screenshots captured via headless Chrome (`playwright-core` driving the system-installed Google Chrome), saved to `output/ui_preview/`; reviewed for overflow, clipping, and label legibility |

## What was and was not built

Built: a FastAPI backend (`api/`, `app/`) that is a strict read-only projection of Phase 3's frozen `output/replay/*` and `output/qa/*` files, and a React + TypeScript + Vite frontend (`frontend/`) with four pages matching the specification's four required views. No React framework beyond React itself, no Next.js, no chart-library dependency (the outlook curve and abstention bars are hand-written SVG, kept intentionally simple).

Not built (per the specification's explicit exclusions): no queue model, no opportunity-time model, no retain/withdraw recommendation anywhere in the API or UI, no authentication, no database (the "database" is the existing frozen CSV/JSONL files), no production deployment, no Phase 5.

## Design decisions requiring human approval

1. **The API never calls `final_v2_adapter`/`shadow_engine`/Monte Carlo code at request time** — it only reads Phase 3's already-frozen `output/replay/replay_events.jsonl` and derives every response from it. This means the "Pit-Wall Outlook" page can only show outlooks for the 10 real historical cases Phase 3 already replayed, not an arbitrary hypothetical current-state input a user might type in. This was a deliberate choice to make it structurally impossible for the application layer to diverge from Phase 3's frozen, tested evidence — but it also means Phase 4 does not offer a "type in your own scenario" mode. If that capability is wanted, it would need a new, explicitly-scoped endpoint that calls the frozen adapter live (still without refitting anything), which was not built here without your sign-off.
2. **`app/replay_service.py`'s `lru_cache` keys on file mtime**, so the API picks up a re-run of `scripts/run_phase3_replay.py` without a server restart during local development. This is a convenience for iterative local use, not a caching strategy meant for any deployed setting (none is planned).
3. **The default case shown on first load is `2021_car60`** (the illustrative case), chosen because it is the only case with a full narrative arc (outlook → later attempt → scoring). This surfaces the illustrative-only case first, which is intentional for demonstrating the full UI, but means a first-time user's first impression is the *least* generalizable case; the illustrative banner is prominent specifically to offset this.
