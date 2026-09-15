# V3 Phase 1 — Scientific QA Report

| Check | Result |
|---|---|
| V2 frozen assets unchanged | **PASS** — see `v2_immutability_report.txt`; 32/32 frozen dependencies byte-identical before and after implementation |
| Point-in-time leakage guard | **PASS** — `test_no_future_leakage.py` (4 tests): forecast issued +1s after decision_time rejected, forecast issued exactly at decision_time allowed, a future-known track observation cannot enter a snapshot (snapshot construction itself is refused), forecast store never selects a post-decision issue_time |
| Forecast vintage selection | **PASS** — `test_forecast_selection.py` (4 tests): prefers most recent eligible issue_time, breaks ties on closest valid_time, returns None when nothing is eligible, loads real HRRR vintages without modifying the source file |
| 15/30/60/90/120 support | **PASS** — `test_horizon_support.py`: all five calibrated anchors return `SUPPORTED` from both the applicability gate and a real adapter call; also demonstrated live in the Step 12 CLI run |
| >120 production inference blocked | **PASS** — `test_horizon_support.py::test_4_h150...`: applicability gate returns `OUT_OF_SUPPORT` for h=150, and the adapter independently raises `KeyError` (defense in depth) since no frozen coefficients exist for that horizon |
| Synthetic data excluded from scientific evaluation | **PASS** — all `SYNTHETIC_TEST_FIXTURE`-sourced data lives only in `tests/fixtures.py` / `tests/test_*.py` and is never referenced by `scripts/run_phase1_demo.py`, which uses only the two real frozen sources (`future_track_samples_with_solar_v1.csv`, `hrrr_ims_2020_2024_features.csv`) |
| Queue model introduced | **NO** — `test_no_forbidden_outputs.py::test_9`: no schema field named anything queue-related; source-scan of `src/*.py` for queue-wait / `P(H=...)` patterns finds none outside documentation of the prohibition itself |
| Strategy recommendation introduced | **NO** — `test_no_forbidden_outputs.py::test_10`: no retain/withdraw/recommend field anywhere; `scoring.py` actively rejects forbidden strategy labels (`assert_no_forbidden_labels`), tested directly |
| FINAL_V2 refitted | **NO** — `final_v2_adapter.py` never calls `LinearRegression().fit()` or any estimator-fitting routine; it only reads already-frozen, already-hashed coefficient/residual/bootstrap files and reuses two pure frozen helper functions unmodified (imported by file path from the original scripts) |
| New high-capacity model introduced | **NO** — no XGBoost/neural-network/transformer/Bayesian-neural-network/LLM/agent code anywhere in `v3_point_in_time/` (grep-verifiable: the only estimator import anywhere in the V3 tree is the frozen script's own already-fitted `LinearRegression`, loaded solely to exist as the module the pure helper functions are imported from — it is never invoked with new data) |

## Test suite result

```
python3 -m unittest discover -s v3_point_in_time/tests -p 'test_*.py'
Ran 19 tests in 0.018s
OK
```

19/19 pass: the 10 mandatory proofs plus 9 additional tests covering forecast-selection tie-breaking, real-HRRR loading non-mutation, all-five-anchors support, the zero-minute boundary, and shadow-prediction append-only enforcement.

## Frozen-artifact reuse, not reimplementation

- Frozen M2b track-model coefficients, frozen track-residual pool, frozen performance bootstrap draws, and frozen performance-residual pool are all read as plain data from their existing, already-hashed CSV files.
- `symmetrized_draws_from_values`, `summarize_draws` (Monte Carlo mechanics) and `solar_elevation_deg` (astronomical geometry) are imported and called **unmodified** from the original frozen scripts via `importlib`, not retyped.
- The only new arithmetic in `final_v2_adapter.py` is applying already-fitted coefficients to a new input (`intercept + Σ beta·x`) — unavoidable and explicitly not a refit.

## Known, disclosed limitations (not hidden)

1. Point-in-time guard checks forecast `issue_time` against the nominal HRRR cycle time; real publication latency beyond the nominal cycle is not quantified anywhere in this project (see `historical_forecast_gap_report.md` §"Coverage limits", item 3). This is reported, not assumed to be zero.
2. HRRR's hourly valid-time grid does not exactly match V2's 15/30/60/90/120-minute horizons; every forecast selection records its `valid_time_error_minutes` rather than silently rounding.
3. No numeric historical-support boundary exists yet for arbitrary current track/ambient input values (as opposed to the scenario-trajectory check V2-E already performed); the applicability gate reports this as a documented gap rather than inventing a threshold (`existing_system_inventory.md` §7).
