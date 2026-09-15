# FINAL_V3 Scientific Limitations

These limitations are stated in full and not softened for presentation.
Every number below is read from a frozen QA/freeze artifact cited next
to it, not restated from memory.

1. **Evidence base.** FINAL_V2's reference evidence covers 41 same-car
   transitions identified in the project's own chronology reconstruction,
   spanning 2020-2024 (`output/qa/phase2_minimum_data_plan.md`). This is
   a small, specific dataset, not a large or continuously refreshed one.

2. **The point-in-time architecture is demonstrated, not just described.**
   Phases 1-3 show, in running, tested software, that the execution chain
   (historical forecast vintage -> point-in-time guard -> frozen
   FINAL_V2 -> immutable prediction) works end-to-end on genuine,
   non-fabricated evidence (`output/qa/phase3_qa_report.md`).

3. **Statistically meaningful point-in-time forecast validation is NOT
   established.** Of the 41 transitions, only 10 have a genuine,
   non-fabricated point-in-time candidate (all 2021); of those, formal
   historical-scoring support (an exact match to a calibrated anchor) is
   **0** (`output/qa/phase2_interpretation_addendum.md`).

4. **One 2021 case (car 60) is illustrative only.** It is retained and
   featured precisely because it demonstrates a genuine evidence/model
   boundary (a large observed deviation neither the forecast-based nor
   the realised-environment inference explains), never reinterpreted as
   validation evidence, and never counted in any aggregate metric
   (`output/phase3_freeze/phase3_summary.txt`).

5. **The opportunity process is not modelled.** This system never
   estimates `P(H=h)` -- whether or when a car will get another
   qualifying attempt. It answers a strictly conditional question:
   *if* another opportunity occurs at horizon h, what physical-performance
   change would be expected.

6. **Queue state is not modelled.** No representation of the qualifying
   queue, session time remaining, or attempt ordering exists anywhere in
   this codebase.

7. **Retain/withdraw strategy is not modelled.** No function in this
   project computes, compares, or recommends a strategic action. This is
   enforced structurally (`src/scoring.py`'s `FORBIDDEN_LABELS`,
   `tests/test_no_forbidden_outputs.py`, `tests/test_scenario.py`
   items 10-13) as well as documented.

8. **Scientific support ends at 120 minutes.** FINAL_V2's calibrated
   anchors are exactly {15, 30, 60, 90, 120} minutes
   (`config/v3_config.yaml`). No inference is ever issued above 120
   minutes, in any mode, including Scenario Mode
   (`tests/test_scenario.py::test_3_...`).

9. **The ambient coefficient is conditional, not causal.** FINAL_V2's
   `beta_ambient_temp` / `beta_delta_ambient_temp_c` terms describe a
   fitted statistical association within the observed regime, not a
   verified causal mechanism outside it.

10. **Regime transfer remains a limitation.** All evidence comes from
    Indianapolis Motor Speedway qualifying conditions in the years
    covered. Applying this system's outputs to a materially different
    track, session format, or climate regime is outside its evidence
    base and is not validated.

11. **External evaluation, where it exists in the parent research
    project, is external-regime evidence, not live-forecast validation.**
    Any 2025 or later comparison is a retrospective check against a
    different data regime, not a demonstration that the point-in-time
    forecast pipeline was deployed and scored live.

12. **Scenario Mode is hypothetical inference, not historical evidence.**
    Every Scenario Mode response is labelled `HYPOTHETICAL_SCENARIO` /
    `NOT_HISTORICAL_EVIDENCE`, is never written to any historical store,
    and never contributes to any validation metric (Phase 5 Step 2;
    `tests/test_scenario.py` items 4-7).
