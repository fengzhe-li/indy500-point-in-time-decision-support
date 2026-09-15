# INDY 500 V3 — Point-in-Time Probabilistic Decision Support

**Project status: `FINAL_V3_FROZEN` — Phases 1-5 complete.**
Historical Shadow Replay + Conditional Physical Outlook.
*Independent research prototype — not affiliated with INDYCAR or Indianapolis Motor Speedway.*

This is a research decision-support prototype. It estimates conditional
physical-performance change, `p(Δv | H=h)`, for `h ∈ {15, 30, 60, 90, 120}`
minutes. **It does not recommend strategy, does not predict opportunity
timing, and is not connected to a live IndyCar timing feed.**

## What this project does

Given a decision timestamp and a physical state (track/ambient
temperature, and either a real historical forecast vintage or a
user-supplied hypothetical one), it answers exactly one question:
*"if another qualifying opportunity occurs at horizon h, what physical
performance change would the frozen scientific model expect, and how
confident is it?"* It never answers *whether* or *when* that opportunity
will occur, and it never recommends retaining or withdrawing an entry.

## Why the original strategy problem was reformulated

The parent research project's earlier work explored predicting
qualifying-attempt performance change. Estimating a full strategy
recommendation (when to make another attempt, whether to withdraw)
would require modelling the opportunity/queue process — `P(H=h)` — for
which this project's evidence base provides no defensible basis. Rather
than force that model, V3 deliberately narrows the scientific target to
the part that **is** well-supported by the frozen `FINAL_V2` physical
model: the conditional performance distribution *given* a horizon,
`p(Δv | H=h)`. Everything upstream of "if this happens" is left
unmodelled and explicitly labelled as such, everywhere in the system.

## FINAL_V2 summary (frozen scientific core)

A fitted track-temperature model (`M2b_mean_solar`) feeding a
residual-bootstrap Monte Carlo performance-response core, calibrated at
five horizons (15/30/60/90/120 min), with a 120-minute production
boundary. V3 never refits, retrains, or modifies any part of it — it
imports FINAL_V2's own pure functions unmodified
(`src/final_v2_adapter.py`). Full detail: `output/final_documentation/FINAL_V3_MODEL_CARD.md`.

## Architecture

```
FROZEN HISTORICAL EVIDENCE                 HYPOTHETICAL USER INPUT
            |                                          |
            v                                          v
     READ-ONLY API                          FROZEN SCIENTIFIC ENGINE
            |                                          |
            v                                          v
  Historical Shadow Replay /               EPHEMERAL SCENARIO OUTPUT
  Evidence & Explanation /                 (never written anywhere,
  Validation & Abstention                   never becomes evidence)
```

Full explanation, layer by layer, plus a Mermaid diagram:
`output/final_documentation/final_v3_architecture.md`.

```
v3_point_in_time/
    src/                    frozen-adapter, point-in-time guard, replay engine, scoring (Phases 1-3)
    app/                    read-only historical API services + isolated scenario_service.py (Phase 4-5)
    api/                    FastAPI app, routes, Pydantic models (Phase 4-5)
    frontend/               React + TypeScript + Vite application, 5 pages (Phase 4-5)
    tests/                  101 tests total (92 Python + 9 frontend)
    scripts/                CLIs, freeze scripts, Docker context prep, smoke test
    docker/                 Dockerfile.api, Dockerfile.frontend, nginx.conf
    ci/                     local GitHub Actions workflow definition (not pushed)
    config/v3_config.yaml   frozen artifact paths, MC settings, applicability thresholds
    output/
        qa/                 QA reports for every phase, immutability/regression reports
        replay/             Phase 3 replay events + case/abstention summaries
        phase2_freeze/ .. phase4_freeze/   per-phase freeze packages
        final_documentation/   architecture, model card, scientific limitations, system spec
        final_ui_preview/   Phase 5 final screenshots
        FINAL_V3_FREEZE/    the authoritative final freeze package
```

## V3 capabilities

- **Historical Shadow Replay** (Phase 3) — a time-ordered, auditable
  event sequence over all 41 real same-car transitions in the evidence
  base, separating *inference support* from *historical evaluation
  support* and making abstention a first-class, visible event rather
  than a dropped row.
- **Scenario Mode** (Phase 5) — an isolated, ephemeral hypothetical-inference
  mode. Runs the exact same frozen FINAL_V2 adapter on user-supplied
  hypothetical current-state input. Every response is labelled
  `HYPOTHETICAL_SCENARIO` / `NOT_HISTORICAL_EVIDENCE`, and is
  structurally prevented from ever entering historical storage or
  validation metrics (`POST /api/scenario/infer`, `GET /api/scenario/schema`).
- **Evidence-Aware Abstention** — a closed vocabulary of machine-readable
  reason codes (`INSUFFICIENT_ATTEMPT_TIMESTAMP`, `HORIZON_OUT_OF_SUPPORT`,
  `NON_ANCHOR_EVALUATION_NOT_APPROVED`, ...) surfaces everywhere the
  system declines to answer, both historically and hypothetically.
- **Featured diagnostic case** — the 2021 car-60 case (a large,
  unexplained observed performance deviation) is retained and
  prominently labelled `ILLUSTRATIVE ONLY — NOT AGGREGATE VALIDATION
  EVIDENCE`, precisely because it demonstrates a genuine evidence/model
  boundary. The default landing case is a different, non-illustrative
  case, chosen by a documented, non-outcome-based rule
  (`app/replay_service.py::select_representative_case`).

## Application screenshots

`output/final_ui_preview/`: `01_pit_wall_outlook.png`,
`02_scenario_mode.png`, `03_historical_replay.png`,
`04_evidence_explanation.png`, `05_validation_abstention.png`,
`06_featured_diagnostic_case.png` (captured against the containerized
application). Earlier Phase 4 screenshots remain at `output/ui_preview/`.

## Quick start (local dev)

```bash
pip install -r v3_point_in_time/requirements.txt
cd v3_point_in_time/frontend && npm install && cd ../..

./v3_point_in_time/scripts/run_v3_app.sh
```

- Backend API: **http://127.0.0.1:8000** (interactive docs at `/docs`)
- Frontend app: **http://127.0.0.1:5173**

No environment variables and no internet connection are required after
`pip`/`npm install` — everything reads local, already-frozen files.

## Quick start (Docker)

```bash
cd v3_point_in_time
./scripts/prepare_docker_context.sh   # stages a minimal (~3.6 MB) build context
docker compose up --build
```

- Backend API: **http://localhost:8000**
- Frontend app (served by nginx, proxying `/api` to the backend): **http://localhost:8080**

The API container's root filesystem is mounted read-only
(`docker-compose.yml`, `read_only: true` + tmpfs `/tmp`) and runs as a
non-root user — frozen scientific assets cannot be modified at runtime,
verified directly (see `output/qa/final_v3_qa_report.md`).

## Tests

```bash
# from the repository root -- 92 Python tests (scientific + API + Phase 5)
python3 -m unittest discover -s v3_point_in_time/tests -p 'test_*.py' -v

# 9 frontend tests
cd v3_point_in_time/frontend && npx vitest run

# end-to-end smoke test (health, readiness, historical + scenario paths)
python3 v3_point_in_time/scripts/smoke_test.py

# scientific protection checks
python3 v3_point_in_time/scripts/run_v2_immutability_check.py
python3 v3_point_in_time/scripts/run_v3_v2_behavioral_regression.py
```

## Scientific boundaries

The system estimates `p(Δv | H=h)`. It does **not** estimate `P(H=h)`,
does **not** predict queue waiting time, does **not** recommend
RETAIN/WITHDRAW, and does **not** calculate an optimal waiting time —
in either historical replay or Scenario Mode. Full, unsoftened
limitations: `output/final_documentation/scientific_limitations.md`.

## Where to find more detail

| Topic | File |
|---|---|
| Full architecture + diagram | `output/final_documentation/final_v3_architecture.md` |
| System / model card | `output/final_documentation/FINAL_V3_MODEL_CARD.md` |
| Technical specification | `output/final_documentation/FINAL_V3_SYSTEM_SPECIFICATION.md` |
| Scientific limitations (unsoftened) | `output/final_documentation/scientific_limitations.md` |
| Final QA matrix | `output/qa/final_v3_qa_report.md` |
| Per-phase QA reports | `output/qa/phase{1,2,3,4}_qa_report.md` |
| Phase 2 illustrative-case interpretation | `output/qa/phase2_interpretation_addendum.md` |
| FINAL_V3 freeze package | `output/FINAL_V3_FREEZE/` |

## What this project deliberately does not do

- Does not refit FINAL_V2, or modify any frozen coefficient, calibration, or residual file.
- Does not expand calibrated horizons (15/30/60/90/120 min only) or extrapolate above 120 minutes, in any mode.
- Does not estimate `P(H=h)` (opportunity/queue timing) or recommend RETAIN/WITHDRAW.
- Does not calculate an optimal waiting time.
- Does not train or call any high-capacity model (no XGBoost/neural network/transformer/LLM/agent).
- Does not download new forecast archives or reconstruct new historical timestamps, in any phase.
- Does not build an authentication system, user accounts, billing, or a general-purpose database — the "database" is the existing frozen CSV/JSONL files.
- Does not let the frontend, or the historical API, recompute, reinterpret, or duplicate any FINAL_V2 calculation. Only `app/scenario_service.py` is permitted to call scientific inference code, and it does so unmodified.
- Does not let a hypothetical Scenario Mode output enter historical replay storage, Phase 2/3 evidence, or any validation metric.
- Does not treat the illustrative 2021 car-60 case as external validation, in any output, in any phase.

## Project status

**`FINAL_V3_FROZEN`.** See `output/FINAL_V3_FREEZE/FINAL_V3_SUMMARY.txt`
and `FINAL_V3_FREEZE_MANIFEST.json` for the authoritative freeze record.
No Phase 6 is planned.
