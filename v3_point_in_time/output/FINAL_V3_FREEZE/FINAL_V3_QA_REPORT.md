# FINAL_V3 QA Report

| Check | Result |
|---|---|
| Scientific core frozen | **PASS** |
| V2 dependency immutability | **PASS** — 32/32 byte-identical |
| V3↔V2 behavioural regression | **PASS** — all 5 horizons within Monte Carlo sampling tolerance |
| Point-in-time leakage controls | **PASS** — `test_no_future_leakage.py`, `test_phase3_replay.py` (items 2-3), `test_api.py::test_14_...` |
| Historical API read-only | **PASS** — `test_phase5_final.py::test_17_...` (no write-mode file I/O in replay/provenance/query services) |
| Scenario API isolated | **PASS** — `test_phase5_final.py::test_18_...` (AST-level import check: only `scenario_service.py` imports scientific code) |
| Scenario/historical evidence separation | **PASS** — `test_scenario.py` items 6-7 (replay evidence and validation summary byte/value-identical before and after scenario calls) |
| Historical abstention auditability | **PASS** — all 31 excluded pre-candidates + all abstained scoring attempts remain in `replay_case_summary.csv` / API output |
| Illustrative case excluded from validation | **PASS** — `historical_scoring_formally_supported: 0`; car 60's `counts_toward_aggregate_validation: false` |
| Scenario scientific regression | **PASS** — `test_scenario.py::test_9_...`: Scenario API output equals direct `final_v2_adapter.infer()` output for identical inputs/seed/n_mc |
| Python tests | **92 / 92 PASS** |
| Frontend tests | **9 / 9 PASS** |
| Frontend build | **PASS** |
| API smoke test | **PASS** — `scripts/smoke_test.py`, 10/10 |
| Scenario smoke test | **PASS** — included in the same smoke test (schema load, valid inference, 5 horizons, `NOT_HISTORICAL_EVIDENCE`, no strategy language) |
| Docker build | **PASS** — both `v3_point_in_time-api` and `v3_point_in_time-frontend` images build successfully from the minimal (~3.6 MB) staged context |
| Docker runtime | **PASS** — `docker compose up`, both containers healthy; API and Scenario endpoints verified through the container and through the frontend's nginx reverse proxy |
| Health/readiness | **PASS** — `/api/system/readiness` reports `READY` with all three sub-checks (`final_v2_integrity`, `scenario_scientific_assets`, `historical_replay_evidence`) `PASS`; verified to report `NOT_READY`/503 when a check is forced to fail |
| Visual QA | **PASS** — 6 final screenshots captured against the running Docker stack, reviewed for clipping/overflow/labels/strategy-language/mode-distinction |
| Queue model introduced | **NO** |
| Opportunity-time model introduced | **NO** |
| Strategy recommendation introduced | **NO** |
| New scientific model introduced | **NO** |
| Historical evidence fabricated | **NO** |

## Total test count

**101 / 101** (92 Python via `unittest discover` + 9 frontend via `vitest run`).

## Container immutability finding (documented, not hidden)

An initial Docker implementation relied only on `chmod 444` for frozen
scientific assets. Runtime testing showed this does **not** actually
protect the files, because the containerized process runs as root by
default and root bypasses file-permission checks. This was caught by
directly attempting a write inside the running container during Phase 5
QA, not assumed safe. The fix, verified afterward: `read_only: true` +
a `tmpfs` `/tmp` mount in `docker-compose.yml` (kernel-level read-only
root filesystem, which does apply to root) plus running the container
process as a non-root user (`v3app`, uid 10001) for defense in depth.
Re-verified: a write attempt inside the corrected container now fails
with `Read-only file system`, and the historical host copies of the
frozen files were never touched at any point (only the container's
disposable writable layer was, and only before the fix).

## Design decisions requiring human approval (carried over / new)

1. (Phase 4, unchanged) No "type in a scenario" mode existed before
   Phase 5 for historical replay; Phase 5 added exactly that as a
   **separate, isolated** Scenario Mode rather than modifying historical
   replay endpoints, per Phase 5 Step 1's explicit instruction to
   preserve that architecture.
2. The default landing case (`2021_car4`) is selected by a documented,
   non-outcome-based rule (smallest total forecast target-time
   mismatch among the 9 eligible cases); see
   `app/replay_service.py::select_representative_case`. An alternative
   rule (e.g. most recent decision_time, or simple case-id ordering)
   would have been equally defensible — this one was chosen because it
   directly reflects data-quality completeness, the property Step 11
   asked to prioritize.
