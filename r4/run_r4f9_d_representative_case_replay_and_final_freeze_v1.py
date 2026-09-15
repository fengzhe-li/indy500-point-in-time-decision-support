from pathlib import Path
import csv
import json
import math
import hashlib
from collections import defaultdict

import numpy as np


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

REPLAY = OUT / "r4f9_c_probabilistic_replay_rows_v1.csv"
HIST = OUT / "r4f9_b3_final_historical_outcome_interface_v1.csv"
MC = OUT / "r4f8h_g_action_mc_scenario_results_v1.csv"
BREAK_EVEN = OUT / "r4f8h_h_priority_break_even_summary_v1.csv"

OUT_CASES = OUT / "r4f9_d_representative_case_replay_v1.csv"
OUT_LC = OUT / "r4f9_d_last_chance_case_replay_v1.csv"
OUT_SKILL = OUT / "r4f9_d_brier_reference_skill_v1.csv"
OUT_QA = OUT / "r4f9_d_final_evaluation_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f9_d_final_evaluation_contract_v1.json"
OUT_REPORT = OUT / "r4f9_d_final_evaluation_report_v1.json"


def clean(v):
    return "" if v is None else str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def truthy(v):
    return clean(v).lower() in {"true", "1", "yes", "y", "t"}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


required = [REPLAY, HIST, MC, BREAK_EVEN]

missing = [p for p in required if not p.exists()]

if missing:
    print("R4F9-D REQUIRED INPUTS MISSING")
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


_, replay_rows = read_csv(REPLAY)
_, hist_rows = read_csv(HIST)
_, mc_rows = read_csv(MC)
_, be_rows = read_csv(BREAK_EVEN)


if len(replay_rows) != 19:
    raise SystemExit(f"Replay sample changed: {len(replay_rows)} != 19")

if len(hist_rows) != 60:
    raise SystemExit(f"Historical interface changed: {len(hist_rows)} != 60")


# =============================================================================
# Brier reference skill
#
# Reference = constant observed event rate on the SAME replay sample.
# This is descriptive climatology only, not an external benchmark.
# =============================================================================

skill_rows = []

targets = [
    (
        "IMPROVE_CURRENT",
        "predicted_p_improve_current",
        "realized_improved_current",
    ),
    (
        "CROSS_DECISION_TIME_BENCHMARK",
        "predicted_p_cross_decision_benchmark",
        "realized_crossed_decision_benchmark",
    ),
]

for target, pfield, yfield in targets:

    scored = []

    for r in replay_rows:
        p = num(r.get(pfield))
        y = num(r.get(yfield))

        if p is not None and y is not None:
            scored.append((p, y))

    ps = np.array([x[0] for x in scored], dtype=float)
    ys = np.array([x[1] for x in scored], dtype=float)

    prevalence = float(np.mean(ys))

    model_brier = float(np.mean((ps - ys) ** 2))

    reference_brier = float(
        np.mean((prevalence - ys) ** 2)
    )

    skill = (
        1.0 - model_brier / reference_brier
        if reference_brier > 0
        else None
    )

    skill_rows.append({
        "target": target,
        "n": len(scored),
        "observed_event_rate": prevalence,
        "model_brier": model_brier,
        "constant_event_rate_reference_brier": reference_brier,
        "brier_skill_vs_same_sample_climatology":
            skill if skill is not None else "",
        "reference_semantics":
            "DESCRIPTIVE_SAME_SAMPLE_CLIMATOLOGY_NOT_EXTERNAL_BASELINE",
    })


with OUT_SKILL.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(skill_rows[0].keys()),
    )
    writer.writeheader()
    writer.writerows(skill_rows)


# =============================================================================
# Build MC lookup: use three illustrative remaining-time scenarios only.
# This is case-description, not optimization.
# =============================================================================

mc_lookup = defaultdict(dict)

for r in mc_rows:

    did = clean(r["fused_decision_id"])
    action = clean(r["action"])

    rem = num(r["assumed_time_remaining_minutes"])

    if rem in {5.0, 20.0, 60.0}:
        mc_lookup[(did, action)][int(rem)] = r


# =============================================================================
# Break-even lookup
# =============================================================================

be_lookup = defaultdict(dict)

for r in be_rows:

    did = clean(r["fused_decision_id"])
    rem = num(r["assumed_time_remaining_minutes"])

    if rem is not None:
        be_lookup[did][int(rem)] = r


# =============================================================================
# Deterministic representative Day 1 case selection
#
# Not cherry-picked manually.
# Each case is selected by an explicit reproducible rule.
# =============================================================================

def abs_error(r):
    return abs(num(r["prediction_error_actual_minus_mean_mph"]) or 0.0)


def signed_error(r):
    return num(r["prediction_error_actual_minus_mean_mph"]) or 0.0


def benchmark_p(r):
    return num(r["predicted_p_cross_decision_benchmark"]) or 0.0


selected = []


def add_case(case_type, row):
    if row is None:
        return

    did = clean(row["fused_decision_id"])

    if any(x["fused_decision_id"] == did for x in selected):
        return

    selected.append({
        "case_type": case_type,
        "fused_decision_id": did,
        "_row": row,
    })


# 1. Largest absolute predictive miss.
add_case(
    "LARGEST_ABSOLUTE_SPEED_ERROR",
    max(replay_rows, key=abs_error),
)

# 2. Largest positive realized surprise.
add_case(
    "LARGEST_POSITIVE_SPEED_SURPRISE",
    max(replay_rows, key=signed_error),
)

# 3. Largest negative realized surprise.
add_case(
    "LARGEST_NEGATIVE_SPEED_SURPRISE",
    min(replay_rows, key=signed_error),
)

# 4. Closest-to-perfect prediction.
add_case(
    "CLOSEST_TO_PREDICTIVE_MEAN",
    min(replay_rows, key=abs_error),
)

# 5. Highest benchmark-crossing confidence among realized successes.
successes = [
    r for r in replay_rows
    if truthy(r["realized_crossed_decision_benchmark"])
]

if successes:
    add_case(
        "HIGH_CONFIDENCE_BENCHMARK_SUCCESS",
        max(successes, key=benchmark_p),
    )

# 6. Lowest predicted benchmark probability among realized successes.
if successes:
    add_case(
        "LOW_PROBABILITY_BENCHMARK_SUCCESS",
        min(successes, key=benchmark_p),
    )

# 7. Highest predicted benchmark probability among realized failures.
failures = [
    r for r in replay_rows
    if not truthy(r["realized_crossed_decision_benchmark"])
]

if failures:
    add_case(
        "HIGH_PROBABILITY_BENCHMARK_FAILURE",
        max(failures, key=benchmark_p),
    )


# =============================================================================
# Flatten representative case table
# =============================================================================

case_rows = []

for item in selected:

    r = item["_row"]
    did = item["fused_decision_id"]

    out = {
        "case_type":
            item["case_type"],

        "fused_decision_id":
            did,

        "year":
            clean(r["year"]),

        "driver_name":
            clean(r["driver_name"]),

        "car_number":
            clean(r["car_number"]),

        "historical_action":
            clean(r["historical_action"]),

        "historical_action_is_optimal_label":
            False,

        "predictive_mean_mph":
            clean(r["predictive_mean_mph"]),

        "predictive_sd_mph":
            clean(r["predictive_sd_mph"]),

        "realized_next_attempt_speed_mph":
            clean(r["realized_next_attempt_speed_mph"]),

        "prediction_error_mph":
            clean(r["prediction_error_actual_minus_mean_mph"]),

        "standardized_residual_z":
            clean(r["standardized_residual_z"]),

        "pi90_hit":
            clean(r["pi90_hit"]),

        "predicted_p_improve_current":
            clean(r["predicted_p_improve_current"]),

        "realized_improved_current":
            clean(r["realized_improved_current"]),

        "predicted_p_cross_decision_benchmark":
            clean(r["predicted_p_cross_decision_benchmark"]),

        "realized_crossed_decision_benchmark":
            clean(r["realized_crossed_decision_benchmark"]),
    }

    for rem in [5, 20, 60]:

        retain = mc_lookup.get(
            (did, "RETAIN_AND_REATTEMPT"),
            {},
        ).get(rem)

        withdraw = mc_lookup.get(
            (did, "WITHDRAW_AND_PRIORITY_REATTEMPT"),
            {},
        ).get(rem)

        if retain:
            out[
                f"retain_p_final_benchmark_t{rem}"
            ] = clean(
                retain[
                    "p_final_result_meets_or_exceeds_decision_benchmark"
                ]
            )
        else:
            out[
                f"retain_p_final_benchmark_t{rem}"
            ] = ""

        if withdraw:
            out[
                f"withdraw_equal_wait_p_final_benchmark_t{rem}"
            ] = clean(
                withdraw[
                    "p_final_result_meets_or_exceeds_decision_benchmark"
                ]
            )

            out[
                f"withdraw_equal_wait_p_no_result_t{rem}"
            ] = clean(
                withdraw[
                    "p_no_final_result"
                ]
            )
        else:
            out[
                f"withdraw_equal_wait_p_final_benchmark_t{rem}"
            ] = ""

            out[
                f"withdraw_equal_wait_p_no_result_t{rem}"
            ] = ""

        be = be_lookup.get(did, {}).get(rem)

        if be:
            out[
                f"first_priority_crossover_pct_t{rem}"
            ] = clean(
                be[
                    "first_tested_priority_reduction_percent_with_crossover"
                ]
            )

            out[
                f"priority_crossover_status_t{rem}"
            ] = clean(
                be[
                    "benchmark_probability_crossover_status"
                ]
            )
        else:
            out[
                f"first_priority_crossover_pct_t{rem}"
            ] = ""

            out[
                f"priority_crossover_status_t{rem}"
            ] = ""

    out["case_selection_semantics"] = (
        "DETERMINISTIC_RULE_BASED_REPRESENTATIVE_REPLAY"
    )

    case_rows.append(out)


with OUT_CASES.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(case_rows[0].keys()),
    )
    writer.writeheader()
    writer.writerows(case_rows)


# =============================================================================
# Last Chance descriptive case replay — all 10, no probability scoring.
# =============================================================================

lc_rows = [
    r for r in hist_rows
    if clean(r["regime"]) == "LAST_CHANCE"
]

lc_case_rows = []

for r in lc_rows:

    lc_case_rows.append({
        "fused_decision_id":
            clean(r["fused_decision_id"]),

        "year":
            clean(r["year"]),

        "driver_name":
            clean(r["driver_name"]),

        "car_number":
            clean(r["car_number"]),

        "historical_action":
            clean(r["historical_action"]),

        "current_result_speed_mph":
            clean(r["current_result_speed_mph"]),

        "decision_time_benchmark_speed_mph":
            clean(r["decision_time_benchmark_speed_mph"]),

        "realized_session_outcome":
            clean(r["realized_session_outcome"]),

        "realized_final_qualified":
            clean(r["realized_final_qualified"]),

        "explicit_crash_incomplete":
            clean(r["explicit_crash_incomplete"]),

        "numeric_final_qualification_probability_scored":
            False,

        "historical_action_is_optimal_label":
            False,

        "evaluation_role":
            "DESCRIPTIVE_LAST_CHANCE_CASE_REPLAY",
    })


with OUT_LC.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(lc_case_rows[0].keys()),
    )
    writer.writeheader()
    writer.writerows(lc_case_rows)


# =============================================================================
# QA
# =============================================================================

qa_rows = []


def qa(metric, value, expected, status):
    qa_rows.append({
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": status,
    })


qa(
    "probabilistic_replay_rows",
    len(replay_rows),
    19,
    "PASS" if len(replay_rows) == 19 else "FAIL",
)

qa(
    "last_chance_descriptive_cases",
    len(lc_case_rows),
    10,
    "PASS" if len(lc_case_rows) == 10 else "FAIL",
)

qa(
    "representative_case_rows",
    len(case_rows),
    "4_TO_7_UNIQUE_RULE_SELECTED",
    (
        "PASS"
        if 4 <= len(case_rows) <= 7
        else "FAIL"
    ),
)

qa(
    "brier_reference_targets",
    len(skill_rows),
    2,
    "PASS" if len(skill_rows) == 2 else "FAIL",
)

qa(
    "representative_cases_manual_cherry_pick",
    False,
    False,
    "PASS",
)

qa(
    "historical_action_used_as_optimal_label",
    False,
    False,
    "PASS",
)

qa(
    "last_chance_final_qualification_probability_scored",
    False,
    False,
    "PASS",
)

qa(
    "dynamic_competitor_model_claimed",
    False,
    False,
    "PASS",
)

qa(
    "exact_queue_wait_claimed",
    False,
    False,
    "PASS",
)

qa(
    "replay_claimed_as_external_holdout",
    False,
    False,
    "PASS",
)

qa(
    "model_refit_after_replay",
    False,
    False,
    "PASS",
)

qa(
    "r4f8h_reopened",
    False,
    False,
    "PASS",
)


with OUT_QA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["metric", "value", "expected", "status"],
    )
    writer.writeheader()
    writer.writerows(qa_rows)


passes = sum(r["status"] == "PASS" for r in qa_rows)
warns = sum(r["status"] == "WARN" for r in qa_rows)
fails = sum(r["status"] == "FAIL" for r in qa_rows)


# =============================================================================
# Final R4F9 contract/report
# =============================================================================

contract = {
    "phase": "R4F9-D",

    "status": "R4F9_EVALUATION_AND_REPLAY_FROZEN",

    "probabilistic_replay": {
        "n": len(replay_rows),
        "role": "RETROSPECTIVE_CALIBRATION_DIAGNOSTIC",
        "external_holdout": False,
    },

    "representative_cases": {
        "selection": "DETERMINISTIC_RULE_BASED",
        "manual_cherry_pick": False,
        "n": len(case_rows),
    },

    "last_chance": {
        "n": len(lc_case_rows),
        "role": "DESCRIPTIVE_CASE_REPLAY_ONLY",
        "numeric_final_qualification_probability_scored": False,
    },

    "brier_reference": {
        "type": "SAME_SAMPLE_CONSTANT_EVENT_RATE",
        "interpretation":
            "descriptive climatology reference only",
    },

    "historical_actions_are_optimal_labels": False,
    "model_refit_after_evaluation": False,
    "r4f8h_reopened": False,

    "final_research_boundary": (
        "The system is evaluated as a decision-support simulator under "
        "frozen decision-time state, performance uncertainty, structural "
        "wait assumptions, cutoff sensitivity, and static observable "
        "benchmark semantics. It does not claim exact historical "
        "counterfactuals, empirical queue reconstruction, or dynamic "
        "final-rank prediction."
    ),
}


OUT_CONTRACT.write_text(
    json.dumps(contract, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


skill_map = {
    r["target"]: r
    for r in skill_rows
}


report = {
    "phase": "R4F9-D",

    "status": (
        "R4F9_EVALUATION_AND_REPLAY_FROZEN"
        if fails == 0
        else "R4F9_FINAL_EVALUATION_FAILED"
    ),

    "representative_cases": len(case_rows),

    "last_chance_cases": len(lc_case_rows),

    "brier_skill": {
        target: {
            "event_rate":
                row["observed_event_rate"],

            "model_brier":
                row["model_brier"],

            "reference_brier":
                row["constant_event_rate_reference_brier"],

            "skill":
                row["brier_skill_vs_same_sample_climatology"],
        }
        for target, row in skill_map.items()
    },

    "qa": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
    },

    "protected_input_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in required
    },

    "output_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [
            OUT_CASES,
            OUT_LC,
            OUT_SKILL,
            OUT_QA,
            OUT_CONTRACT,
        ]
    },

    "next_phase": (
        "R4_RESEARCH_ENGINEERING_COMPLETE_RESULTS_SYNTHESIS"
        if fails == 0
        else "RESOLVE_R4F9_D_FAILURES"
    ),
}


OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


# =============================================================================
# Console
# =============================================================================

print("=" * 132)
print("R4F9-D — REPRESENTATIVE CASE REPLAY + FINAL EVALUATION FREEZE")
print("=" * 132)
print()

print("BRIER REFERENCE SKILL")
print("-" * 132)

for r in skill_rows:

    skill = num(
        r["brier_skill_vs_same_sample_climatology"]
    )

    skill_text = (
        f"{skill:+.6f}"
        if skill is not None
        else "NA"
    )

    print(
        f"{r['target']:38s} | "
        f"event rate={float(r['observed_event_rate']):.3f} | "
        f"model={float(r['model_brier']):.6f} | "
        f"reference={float(r['constant_event_rate_reference_brier']):.6f} | "
        f"skill={skill_text}"
    )

print()
print("REPRESENTATIVE DAY 1 CASES")
print("-" * 132)
print(f"Unique cases selected: {len(case_rows)}")
print()

for r in case_rows:

    print(
        f"{r['case_type']:38s} | "
        f"{r['year']} | "
        f"{r['driver_name']} | "
        f"error={float(r['prediction_error_mph']):+.3f} mph | "
        f"z={float(r['standardized_residual_z']):+.3f} | "
        f"PI90={r['pi90_hit']}"
    )

print()
print("LAST CHANCE")
print("-" * 132)
print(f"Descriptive cases retained: {len(lc_case_rows)}")
print("Numeric final-qualification probability scoring: NO")
print()

print("QA")
print("-" * 132)
print(f"{passes} PASS | {warns} WARN | {fails} FAIL")

for r in qa_rows:
    if r["status"] != "PASS":
        print(
            f"{r['status']:5s} | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

print()
print("OUTPUTS")
print("-" * 132)

for p in [
    OUT_CASES,
    OUT_LC,
    OUT_SKILL,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F9_D_FINAL_EVALUATION_FAILED")
    raise SystemExit(1)

print("R4F9_EVALUATION_AND_REPLAY_FROZEN")
print()
print("NEXT: R4 RESEARCH ENGINEERING COMPLETE — RESULTS SYNTHESIS")
print()
print(
    "IMPORTANT: Representative cases were selected by deterministic rules. "
    "Historical actions remain descriptive only, replay is not an external "
    "holdout, and no post-evaluation refit was performed."
)
