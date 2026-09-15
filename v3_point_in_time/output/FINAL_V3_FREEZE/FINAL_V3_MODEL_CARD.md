# FINAL_V3 Model / System Card

## Purpose

Estimate a conditional physical-performance outlook,
`p(Δv | H=h)` for h in {15, 30, 60, 90, 120} minutes, at a historical or
hypothetical point-in-time decision moment, using only information that
would have been (or hypothetically is) available at that moment. The
system communicates *what the frozen physical model can say*, *how
confident it is*, and *whether the answer is scientifically supported*
-- not what a race strategist should do.

## Intended use

- Research and portfolio demonstration of leakage-controlled,
  evidence-aware probabilistic decision support built around an
  existing frozen scientific model.
- Historical shadow replay: inspecting what the frozen model could have
  said at real historical decision times, with full provenance.
- Hypothetical scenario exploration: running the same frozen model on
  user-supplied hypothetical current-state inputs for demonstration.

## Non-intended use

- **Not** a live race-strategy tool. No queue model, opportunity-timing
  model, or retain/withdraw recommendation exists anywhere in this
  system (by design, not by omission -- see
  `scientific_limitations.md` items 5-7).
- **Not** a validated general-purpose forecast-error benchmark. Formal
  historical-scoring support in this evidence base is 0 cases; one
  illustrative case exists and is clearly labelled as such.
- **Not** connected to a live IndyCar timing feed, and not affiliated
  with INDYCAR or Indianapolis Motor Speedway.
- **Not** intended for any regime (track, era, session format) outside
  the evidence this project actually holds.

## Scientific target

`E[Δv | H=h]`, `median[Δv | H=h]`, `P(improve | H=h)`, and 80%/90%
predictive intervals, for the five calibrated horizons only.

## Evidence base

41 real same-car qualifying-attempt transitions (2020-2024), real NOAA
HRRR forecast vintages, real observed track/ambient temperature
readings. See `output/qa/phase2_minimum_data_plan.md` and
`output/qa/phase2_existing_forecast_evidence_audit.md`.

## Model architecture

Frozen `FINAL_V2`: a fitted track-temperature model (`M2b_mean_solar`)
feeding a residual-bootstrap Monte Carlo performance-response core.
V3 imports the model's own pure functions unmodified
(`src/final_v2_adapter.py`) -- it does not reimplement or retrain any
part of it.

## Supported horizons

Exactly {15, 30, 60, 90, 120} minutes. No horizon above 120 minutes is
ever exposed for inference, in any mode.

## Point-in-time controls

A fail-closed leakage guard (`src/point_in_time_guard.py`) and a
strict `issue_time <= decision_time` forecast-selection rule
(`src/forecast_vintage_store.py`) ensure no historical inference uses
information that would not have been available at the modelled decision
time.

## Uncertainty

Monte Carlo predictive intervals (80%/90%) from the frozen bootstrap +
residual-pool simulation. A separate, frozen V2-D uncertainty-source
ablation is exposed as a **global, horizon-level diagnostic** (never a
per-prediction decomposition) showing empirical performance residual
dominates predictive-interval width at every horizon.

## Applicability / abstention

Every inference carries an explicit status: `SUPPORTED`, `CAUTION`,
`OUT_OF_SUPPORT`, or `INPUT_INSUFFICIENT`. Historical replay additionally
distinguishes **inference support** from **historical evaluation
support** and makes abstention a first-class, auditable event rather
than a silently dropped case (`src/replay_engine.py`,
`output/replay/replay_abstention_summary.csv`).

## Historical replay semantics

Time-ordered `ReplayEvent` records over all 41 real transitions: 9 with
full 5-horizon conditional-outlook support (historical scoring
correctly abstained, since their realised horizons exceed 120 minutes),
1 illustrative-only (car 60, 2021), 31 abstained for insufficient
timestamp. See `output/phase3_freeze/phase3_summary.txt`.

## Scenario semantics

A strictly isolated, ephemeral hypothetical-inference mode
(`app/scenario_service.py`, `POST /api/scenario/infer`). Every response
is labelled `HYPOTHETICAL_SCENARIO` / `NOT_HISTORICAL_EVIDENCE`, uses a
minimum scientifically-derived input contract, and is never written to
any historical store or counted in any validation metric.

## External evaluation

Any evaluation against data outside the 2020-2024 evidence base
(e.g. a later season) is external-regime evidence, not live-forecast
validation -- the model was never deployed to make a real-time decision
historically.

## Known limitations

See `scientific_limitations.md` in full.

## Reproducibility

- FINAL_V2's 32 frozen dependencies are byte-hash-verified against a
  pre-implementation baseline on every phase and before every freeze
  (`scripts/run_v2_immutability_check.py`).
- V3's adapter is verified to reproduce the frozen batch script's own
  output within Monte Carlo sampling tolerance, using an independent
  RNG stream (`scripts/run_v3_v2_behavioral_regression.py`).
- Scenario Mode uses a fixed seed/n_mc convention: identical hypothetical
  input always produces identical output
  (`tests/test_scenario.py::test_8_...`).

## Ethical / operational caveats

- This is a research prototype, not a production strategy system; it
  must not be presented or used as one.
- All historical timestamps and forecast vintages are real; no
  timestamp, forecast, or historical outcome anywhere in this project
  is fabricated.
- The illustrative car-60 case is retained and prominently labelled
  specifically so a large, unexplained model deviation is visible, not
  hidden.
