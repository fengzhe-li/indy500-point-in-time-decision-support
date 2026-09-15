# FINAL_V3 System Specification

Precise technical reference. For narrative explanation see
`final_v3_architecture.md`; for scope/use see `FINAL_V3_MODEL_CARD.md`.

## Versioning

- Scientific core: `FINAL_V2` (frozen; see `docs/final_v2_system_specification.md` in the parent repo for its own spec)
- Application layer: `FINAL_V3` (this project, Phases 1-5)
- API version string: `4.0.0` (`api/main.py`) — kept from Phase 4; Phase 5 added routes without a breaking contract change

## Supported horizons

`[15, 30, 60, 90, 120]` minutes, exactly. Source of truth:
`config/v3_config.yaml` (`supported_horizons_min`,
`max_supported_horizon_min: 120`), read at runtime by
`app/query_service.py` and hard-coded as
`applicability_gate.CALIBRATED_ANCHOR_HORIZONS_MIN` (imported, not
re-declared, by `src/replay_engine.py` and `app/scenario_service.py`).

## Data contracts (see `src/schemas.py` for authoritative dataclasses)

- `ForecastVintage`, `DecisionSnapshot`, `FinalV2Output`, `ShadowPrediction`, `GuardResult`
- `ReplayEvent` (Phase 3), with closed vocabularies `REPLAY_EVENT_TYPES`, `ABSTENTION_REASON_CODES`, `REPLAY_CASE_CATEGORIES`

## Scenario input contract (Phase 5; `app/scenario_service.schema()`)

| Field | Type | Required | Note |
|---|---|---|---|
| `current_track_temp_c` | float | yes | |
| `current_ambient_temp_c` | float | yes | |
| `forecast_future_ambient_temp_c` | float | yes | USER-SUPPLIED HYPOTHETICAL FORECAST, applied uniformly at every horizon's target time |
| `decision_time` | ISO-8601 UTC string | no | defaults to current time |

Fixed, non-user-editable constants: site coordinates
(`LATITUDE_DEG=39.7950`, `LONGITUDE_DEG=-86.2348`), Monte Carlo
`RANDOM_SEED=20260914`, `N_MC=20000` — the same convention Phase 1-3 use.

## API contract

See `output/phase4_freeze/api_contract.json` (Phase 4 endpoints,
unchanged) plus the Phase 5 additions below.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/scenario/schema` | input contract + presets |
| POST | `/api/scenario/infer` | ephemeral hypothetical inference |
| GET | `/api/replay/cases/representative` | deterministic default-case selection |
| GET | `/api/system/readiness` | 200 `READY` / 503 `NOT_READY` |

## Frontend routes (in-memory tab state, no router library)

`outlook` (Pit-Wall Outlook) · `scenario` (Scenario Mode) · `replay`
(Historical Shadow Replay) · `evidence` (Evidence & Explanation) ·
`validation` (Validation & Abstention). See
`output/phase4_freeze/ui_route_manifest.json` for the Phase 4 baseline;
Phase 5 added the `scenario` route in the same manifest shape.

## Frozen scientific dependencies

Exactly 32 files, enumerated in
`output/qa/v2_pre_implementation_hashes.txt` (path + sha256), verified
against a pre-implementation baseline by
`scripts/run_v2_immutability_check.py` and again by
`app/health_service.check_v2_integrity()` at runtime. Total size ~1.3 MB.

## Container asset manifest

See `output/phase4_freeze/../FINAL_V3_FREEZE/FINAL_V3_CONTAINER_ASSET_MANIFEST.json`
(Phase 5 Step 18) for the exact list of frozen files the Docker image
requires, with purpose, hash, and read-only expectation for each.

## Test suite

101 tests total: 92 Python (`unittest discover -s v3_point_in_time/tests -p 'test_*.py'`) + 9 frontend (`npx vitest run` in `frontend/`).

## Reproducible environment

- Python: `v3_point_in_time/requirements.txt` (pinned)
- Frontend: `frontend/package.json` + `frontend/package-lock.json`
- Container: `docker-compose.yml`, `docker/Dockerfile.api`, `docker/Dockerfile.frontend`, `docker/nginx.conf`, `scripts/prepare_docker_context.sh`
