# Phase 2 Interpretation Addendum (written during Phase 3)

This addendum does not delete, modify, or falsify any Phase 2 output
(`output/qa/phase2_qa_report.md`, `output/phase2_freeze/`,
`output/evaluation/phase2_case_table.csv` and everything else Phase 2
produced remain exactly as frozen). It records a human decision that
narrows how one Phase 2 result may be *interpreted and used going
forward*, made at the start of Phase 3.

## Human decision, recorded verbatim in effect

The 2021 car 60 case (realised horizon ≈ 64.1 min, evaluated at the
nearest calibrated anchor of 60 min, ≈ 4.1-minute mismatch) is approved
**only** as:

```
ILLUSTRATIVE_POINT_IN_TIME_SHADOW_CASE
```

It is **not** approved as:

```
POINT_IN_TIME_EXTERNAL_VALIDATION
```

and must **not** contribute to any headline aggregate validation metric,
now or in any later phase, unless a separate, explicit human decision
changes this.

## Restated Phase 2 scientific conclusion

- Phase 2 **architecture validation: PASS**. The execution chain
  (historical forecast vintage → point-in-time guard → frozen
  FINAL_V2 → immutable prediction) was demonstrated end-to-end on real,
  non-fabricated evidence, with correct provenance, no future-information
  leakage, and reproducible hashing.
- Phase 2 **statistical point-in-time forecast validation of FINAL_V2:
  NOT ESTABLISHED.** This is an evidence/identifiability boundary, not
  an implementation failure: of the 10 genuine point-in-time candidate
  cases found in the entire available dataset (all 2021), only one has
  a realised horizon anywhere near a calibrated anchor, and that one
  requires a 4.1-minute anchor substitution to evaluate at all.

## Numbers, for reference (all read from frozen Phase 2 outputs, not recomputed here)

| Quantity | Value | Source |
|---|---|---|
| Genuine point-in-time candidate cases | 10 | `phase2_minimum_data_plan.md` |
| Formally supported aggregate-validation cases (exact anchor match) | **0** | this addendum's clarification |
| Illustrative shadow case | 1 (2021, car 60) | `phase2_qa_report.md` |
| Illustrative realised horizon | ≈ 64.1 min | `phase2_case_table.csv` (`realised_horizon_minutes`) |
| Nearest calibrated anchor | 60 min | `phase2_case_table.csv` (`target_horizon_minutes`) |
| Mismatch | ≈ 4.1 min | 64.13 − 60 |

## What changes in Phase 3 as a result

Phase 3's `src/replay_engine.py` encodes this decision structurally, not
just in prose: `historical_scoring_support()` treats an exact match to a
calibrated anchor (15/30/60/90/120 min) as the only *general* rule for
formal historical-scoring support, and looks the 2021/car 60 exception
up from a single named, explicit table
(`ILLUSTRATIVE_APPROVED_CASES`) rather than deriving it from a
generic distance/tolerance threshold that could silently apply to other
cases. Every Phase 3 output that reports this case labels it
`ILLUSTRATIVE_ONLY` / `NON_ANCHOR_EVALUATION_NOT_APPROVED` and carries
`counts_toward_aggregate_validation: false`.

This is the authoritative interpretation layer for the car 60 case from
this point forward.
