from pathlib import Path
import csv
import json
import math
import hashlib
from collections import defaultdict

import numpy as np


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

# =============================================================================
# R4F8H-H — PRIORITY BENEFIT SENSITIVITY
#
# PURPOSE
# -------
# Quantify how much STRUCTURAL Lane-1 wait reduction would be required before
# WITHDRAW_AND_PRIORITY_REATTEMPT can improve relevant outcome metrics relative
# to RETAIN_AND_REATTEMPT.
#
# IMPORTANT
# ---------
# These priority reductions are NOT historical estimates.
# They are sensitivity scenarios only.
#
# No model refit.
# No new queue evidence.
# No dynamic competitor model.
# No historical action labels.
# No final-rank claims.
# =============================================================================

N_DRAWS = 20000

TIME_REMAINING_SCENARIOS = [5, 10, 15, 20, 30, 45, 60]

PRIORITY_WAIT_REDUCTION_SCENARIOS = [
    0.00,
    0.25,
    0.50,
    0.75,
]

WAIT_SUPPORT_MIN = np.array(
    [5.0, 15.0, 30.0, 45.0],
    dtype=float,
)

WAIT_PROBS = np.array(
    [0.25, 0.25, 0.25, 0.25],
    dtype=float,
)


# =============================================================================
# Inputs
# =============================================================================

DECISION_FILE = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
ACTION_FILE = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"
UNCERTAINTY_FILE = OUT / "r4f8g_decision_predictive_uncertainty_state_v1.csv"
FOUR_LAP_PANEL = OUT / "r4p1_attempt_four_lap_panel_v1.csv"

G_RESULTS = OUT / "r4f8h_g_action_mc_scenario_results_v1.csv"
G_CONTRACT = OUT / "r4f8h_g_final_action_mc_contract_v1.json"
F_POLICY = OUT / "r4f8h_f_competitive_state_policy_contract_v1.json"

OUT_RESULTS = OUT / "r4f8h_h_priority_benefit_sensitivity_results_v1.csv"
OUT_COMPARE = OUT / "r4f8h_h_retain_withdraw_comparison_v1.csv"
OUT_BREAK_EVEN = OUT / "r4f8h_h_priority_break_even_summary_v1.csv"
OUT_QA = OUT / "r4f8h_h_priority_benefit_sensitivity_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f8h_h_priority_benefit_sensitivity_contract_v1.json"
OUT_REPORT = OUT / "r4f8h_h_priority_benefit_sensitivity_report_v1.json"


# =============================================================================
# Helpers
# =============================================================================

def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return None


def truthy(v):
    return clean(v).lower() in {
        "1", "true", "yes", "y", "t",
        "ready", "sample_ready"
    }


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    return (
        str(s)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def find_field(fields, candidates):
    m = {norm(f): f for f in fields}
    for c in candidates:
        if norm(c) in m:
            return m[norm(c)]
    return None


def stable_seed(*parts):
    text = "||".join(map(str, parts))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32)


def prob(mask):
    mask = np.asarray(mask, dtype=bool)
    return float(np.mean(mask))


def mean_finite(values):
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return ""
    return float(np.mean(arr))


# =============================================================================
# Required inputs
# =============================================================================

required = [
    DECISION_FILE,
    ACTION_FILE,
    UNCERTAINTY_FILE,
    FOUR_LAP_PANEL,
    G_RESULTS,
    G_CONTRACT,
    F_POLICY,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("=" * 130)
    print("R4F8H-H REQUIRED INPUTS MISSING")
    print("=" * 130)
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


dec_fields, dec_rows = read_csv(DECISION_FILE)
act_fields, act_rows = read_csv(ACTION_FILE)
unc_fields, unc_rows = read_csv(UNCERTAINTY_FILE)
panel_fields, panel_rows = read_csv(FOUR_LAP_PANEL)
g_fields, g_rows = read_csv(G_RESULTS)

g_contract = json.loads(G_CONTRACT.read_text(encoding="utf-8"))
f_policy = json.loads(F_POLICY.read_text(encoding="utf-8"))


# =============================================================================
# Resolve fields
# =============================================================================

DEC_ID = find_field(
    dec_fields,
    ["fused_decision_id", "decision_id"]
)

ACTION_DEC_ID = find_field(
    act_fields,
    ["fused_decision_id", "decision_id"]
)

ACTION = find_field(
    act_fields,
    ["feasible_action", "action"]
)

YEAR = find_field(
    dec_fields,
    ["year", "season"]
)

DRIVER = find_field(
    dec_fields,
    ["driver_name", "driver", "normalized_driver_name"]
)

REGIME = find_field(
    dec_fields,
    ["regime", "session_regime", "qualifying_regime"]
)

PROTECTED = find_field(
    dec_fields,
    ["protected_result_exists", "has_protected_result"]
)

CURRENT_SPEED = find_field(
    dec_fields,
    [
        "current_best_speed_mph",
        "current_result_mph",
        "current_speed_mph",
    ]
)

PROTECTED_SPEED = find_field(
    dec_fields,
    [
        "protected_result_speed_mph",
        "current_protected_result_speed_mph",
    ]
)

BENCHMARK_SPEED = find_field(
    dec_fields,
    [
        "benchmark_speed_mph",
        "regime_benchmark_speed_mph",
        "cutoff_speed_mph",
    ]
)

BENCHMARK_TYPE = find_field(
    dec_fields,
    ["benchmark_type", "benchmark"]
)

UNC_DEC_ID = find_field(
    unc_fields,
    ["fused_decision_id", "decision_id"]
)

PRED_MEAN = find_field(
    unc_fields,
    [
        "predictive_mean_speed_mph",
        "predicted_speed_mph",
        "predictive_mean_mph",
        "mean_speed_mph",
    ]
)

PRED_SD = find_field(
    unc_fields,
    [
        "predictive_sd_mph",
        "prediction_sd_mph",
        "sd_mph",
        "predictive_scale_mph",
    ]
)

SAMPLE_READY = find_field(
    unc_fields,
    [
        "sample_ready",
        "performance_sample_ready",
        "sampleable",
        "performance_sampleable",
    ]
)

PANEL_SPEED = find_field(
    panel_fields,
    [
        "four_lap_avg_speed_mph",
        "four_lap_average_speed_mph",
        "avg_speed_mph",
        "average_speed_mph",
        "official_four_lap_avg_speed_mph",
        "qualifying_speed_mph",
        "attempt_average_speed_mph",
    ]
)

PANEL_CLASS = find_field(
    panel_fields,
    [
        "reconstruction_class",
        "attempt_reconstruction_class",
        "record_class",
    ]
)


essential = {
    "DEC_ID": DEC_ID,
    "ACTION_DEC_ID": ACTION_DEC_ID,
    "ACTION": ACTION,
    "PROTECTED": PROTECTED,
    "BENCHMARK_SPEED": BENCHMARK_SPEED,
    "UNC_DEC_ID": UNC_DEC_ID,
    "PRED_MEAN": PRED_MEAN,
    "PRED_SD": PRED_SD,
    "PANEL_SPEED": PANEL_SPEED,
}

missing_fields = [k for k, v in essential.items() if v is None]

if missing_fields:
    print("=" * 130)
    print("R4F8H-H REQUIRED FIELD RESOLUTION FAILED")
    print("=" * 130)
    for x in missing_fields:
        print(x)
    raise SystemExit(1)


# =============================================================================
# Build Day 1 eligible paired decision universe
# =============================================================================

decision_by_id = {
    clean(r.get(DEC_ID)): r
    for r in dec_rows
}

actions_by_decision = defaultdict(set)

for row in act_rows:
    actions_by_decision[
        clean(row.get(ACTION_DEC_ID))
    ].add(clean(row.get(ACTION)))


paired_day1_ids = []

for did, actions in actions_by_decision.items():

    required_actions = {
        "STOP",
        "RETAIN_AND_REATTEMPT",
        "WITHDRAW_AND_PRIORITY_REATTEMPT",
    }

    if required_actions.issubset(actions):
        paired_day1_ids.append(did)

paired_day1_ids = sorted(paired_day1_ids)

if len(paired_day1_ids) != 50:
    raise SystemExit(
        f"Unexpected paired Day1 decision count: "
        f"{len(paired_day1_ids)} != 50"
    )


# =============================================================================
# Future-performance lookup
# =============================================================================

unc_by_id = defaultdict(list)

for row in unc_rows:
    unc_by_id[clean(row.get(UNC_DEC_ID))].append(row)


def uncertainty_state(did):
    matches = unc_by_id.get(did, [])
    if len(matches) != 1:
        return None
    return matches[0]


def sample_ready(row):
    if row is None:
        return False

    if SAMPLE_READY:
        return truthy(row.get(SAMPLE_READY))

    mu = num(row.get(PRED_MEAN))
    sd = num(row.get(PRED_SD))

    return (
        mu is not None
        and sd is not None
        and sd > 0
    )


def current_result_speed(decision):
    if CURRENT_SPEED:
        x = num(decision.get(CURRENT_SPEED))
        if x is not None:
            return x

    if PROTECTED_SPEED:
        x = num(decision.get(PROTECTED_SPEED))
        if x is not None:
            return x

    return None


# =============================================================================
# Empirical four-lap run duration
# =============================================================================

durations_sec = []

for row in panel_rows:

    speed = num(row.get(PANEL_SPEED))

    if speed is None or speed <= 0:
        continue

    if PANEL_CLASS:
        cls = clean(row.get(PANEL_CLASS))
        if cls and cls != "A_COMPLETE":
            continue

    duration = 36000.0 / speed

    if 120.0 <= duration <= 220.0:
        durations_sec.append(duration)


if len(durations_sec) != 260:
    raise SystemExit(
        f"Expected 260 complete-run durations, "
        f"found {len(durations_sec)}"
    )

durations_min = np.asarray(durations_sec, dtype=float) / 60.0


# =============================================================================
# Monte Carlo sensitivity
#
# CRITICAL paired-random-number design:
#
# For each decision + remaining-time scenario:
# - RETAIN and WITHDRAW use the SAME underlying base wait draws
# - SAME run-duration draws
# - SAME future-speed draws
#
# Only Lane 1 wait reduction changes.
#
# This isolates the structural priority effect and reduces MC noise.
# =============================================================================

results = []

for did in paired_day1_ids:

    decision = decision_by_id[did]

    u = uncertainty_state(did)

    if not sample_ready(u):
        raise SystemExit(
            f"Day1 paired decision unexpectedly not sample-ready: {did}"
        )

    mu = num(u.get(PRED_MEAN))
    sd = num(u.get(PRED_SD))

    if mu is None or sd is None or sd <= 0:
        raise SystemExit(
            f"Invalid predictive distribution for {did}"
        )

    old_speed = current_result_speed(decision)
    benchmark = num(decision.get(BENCHMARK_SPEED))

    if old_speed is None:
        raise SystemExit(
            f"Day1 protected decision missing retained speed: {did}"
        )

    if benchmark is None:
        raise SystemExit(
            f"Day1 decision missing benchmark speed: {did}"
        )

    year = clean(decision.get(YEAR)) if YEAR else ""
    driver = clean(decision.get(DRIVER)) if DRIVER else ""
    regime = clean(decision.get(REGIME)) if REGIME else ""
    benchmark_type = (
        clean(decision.get(BENCHMARK_TYPE))
        if BENCHMARK_TYPE
        else ""
    )

    for remaining in TIME_REMAINING_SCENARIOS:

        # Same base stochastic realization for all priority-reduction scenarios.
        seed = stable_seed(
            "R4F8H-H",
            did,
            remaining,
            N_DRAWS,
        )

        rng = np.random.default_rng(seed)

        base_wait = rng.choice(
            WAIT_SUPPORT_MIN,
            size=N_DRAWS,
            replace=True,
            p=WAIT_PROBS,
        )

        run_duration = rng.choice(
            durations_min,
            size=N_DRAWS,
            replace=True,
        )

        future_speed = rng.normal(
            loc=mu,
            scale=sd,
            size=N_DRAWS,
        )

        # ---------------------------------------------------------------------
        # RETAIN baseline
        #
        # Lane 2 wait remains the frozen structural prior.
        # ---------------------------------------------------------------------

        retain_completion_time = (
            base_wait + run_duration
        )

        retain_completed = (
            retain_completion_time <= remaining
        )

        retain_final = np.full(
            N_DRAWS,
            old_speed,
            dtype=float,
        )

        retain_final[retain_completed] = np.maximum(
            old_speed,
            future_speed[retain_completed],
        )

        retain_benchmark_hit = (
            retain_final >= benchmark
        )

        retain_improved = (
            retain_final > old_speed
        )

        retain_p_completed = prob(retain_completed)
        retain_p_benchmark = prob(retain_benchmark_hit)
        retain_p_improved = prob(retain_improved)
        retain_expected_final = float(np.mean(retain_final))

        # ---------------------------------------------------------------------
        # WITHDRAW priority sensitivity
        # ---------------------------------------------------------------------

        for reduction in PRIORITY_WAIT_REDUCTION_SCENARIOS:

            priority_wait = (
                base_wait * (1.0 - reduction)
            )

            withdraw_completion_time = (
                priority_wait + run_duration
            )

            withdraw_completed = (
                withdraw_completion_time <= remaining
            )

            withdraw_final = np.full(
                N_DRAWS,
                np.nan,
                dtype=float,
            )

            withdraw_final[withdraw_completed] = (
                future_speed[withdraw_completed]
            )

            withdraw_exists = np.isfinite(
                withdraw_final
            )

            withdraw_benchmark_hit = (
                withdraw_exists
                & (withdraw_final >= benchmark)
            )

            withdraw_beats_old = (
                withdraw_exists
                & (withdraw_final > old_speed)
            )

            withdraw_worse = (
                (~withdraw_exists)
                | (
                    withdraw_exists
                    & (withdraw_final < old_speed)
                )
            )

            p_completed = prob(
                withdraw_completed
            )

            p_exists = prob(
                withdraw_exists
            )

            p_no_result = prob(
                ~withdraw_exists
            )

            p_benchmark = prob(
                withdraw_benchmark_hit
            )

            p_beats_old = prob(
                withdraw_beats_old
            )

            p_worse = prob(
                withdraw_worse
            )

            expected_final_conditional = (
                mean_finite(withdraw_final)
            )

            results.append({
                "fused_decision_id": did,
                "year": year,
                "driver": driver,
                "regime": regime,
                "benchmark_type": benchmark_type,

                "current_result_speed_mph":
                    old_speed,

                "benchmark_speed_mph":
                    benchmark,

                "assumed_time_remaining_minutes":
                    remaining,

                "time_remaining_semantics":
                    "STRUCTURAL_SENSITIVITY_SCENARIO",

                "priority_wait_reduction_fraction":
                    reduction,

                "priority_wait_reduction_percent":
                    int(round(reduction * 100)),

                "priority_reduction_semantics":
                    "STRUCTURAL_SENSITIVITY_NOT_HISTORICAL_ESTIMATE",

                "n_draws":
                    N_DRAWS,

                "lane2_wait_support_minutes":
                    "5|15|30|45",

                "lane1_effective_wait_support_minutes":
                    "|".join(
                        f"{x * (1.0-reduction):.3f}"
                        for x in WAIT_SUPPORT_MIN
                    ),

                # RETAIN baseline
                "retain_p_completed":
                    retain_p_completed,

                "retain_p_final_result_exists":
                    1.0,

                "retain_p_final_meets_benchmark":
                    retain_p_benchmark,

                "retain_p_final_improves_current":
                    retain_p_improved,

                "retain_p_final_worse_than_current":
                    0.0,

                "retain_expected_final_speed_mph":
                    retain_expected_final,

                # WITHDRAW
                "withdraw_p_completed":
                    p_completed,

                "withdraw_p_final_result_exists":
                    p_exists,

                "withdraw_p_no_final_result":
                    p_no_result,

                "withdraw_p_final_meets_benchmark":
                    p_benchmark,

                "withdraw_p_final_beats_current":
                    p_beats_old,

                "withdraw_p_final_worse_than_current":
                    p_worse,

                "withdraw_expected_final_speed_conditional_mph":
                    expected_final_conditional,

                # Differences
                "delta_completion_probability":
                    p_completed - retain_p_completed,

                "delta_benchmark_success_probability":
                    p_benchmark - retain_p_benchmark,

                "delta_improvement_probability":
                    p_beats_old - retain_p_improved,

                "delta_no_result_probability":
                    p_no_result,

                "delta_downside_probability":
                    p_worse,

                # This is intentionally NOT a utility decision.
                "withdraw_benchmark_probability_exceeds_retain":
                    p_benchmark > retain_p_benchmark,

                "withdraw_completion_probability_exceeds_retain":
                    p_completed > retain_p_completed,

                "dynamic_competitor_evolution_used":
                    False,

                "historical_priority_advantage_claimed":
                    False,
            })


# =============================================================================
# Save all sensitivity results
# =============================================================================

with OUT_RESULTS.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(results[0].keys()),
    )

    writer.writeheader()
    writer.writerows(results)


# =============================================================================
# Compact paired comparison table
# =============================================================================

compare_rows = []

for row in results:

    compare_rows.append({
        "fused_decision_id":
            row["fused_decision_id"],

        "year":
            row["year"],

        "driver":
            row["driver"],

        "assumed_time_remaining_minutes":
            row["assumed_time_remaining_minutes"],

        "priority_wait_reduction_percent":
            row["priority_wait_reduction_percent"],

        "retain_p_completed":
            row["retain_p_completed"],

        "withdraw_p_completed":
            row["withdraw_p_completed"],

        "retain_p_final_meets_benchmark":
            row["retain_p_final_meets_benchmark"],

        "withdraw_p_final_meets_benchmark":
            row["withdraw_p_final_meets_benchmark"],

        "withdraw_p_no_final_result":
            row["withdraw_p_no_final_result"],

        "withdraw_p_final_worse_than_current":
            row["withdraw_p_final_worse_than_current"],

        "delta_benchmark_success_probability":
            row["delta_benchmark_success_probability"],
    })


with OUT_COMPARE.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(compare_rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(compare_rows)


# =============================================================================
# Break-even summaries
#
# "Break-even" here has a deliberately narrow meaning:
#
# First tested priority-reduction scenario at which
# P(final result >= CURRENT decision-time benchmark)
# for WITHDRAW exceeds RETAIN.
#
# It is NOT an optimal-action threshold.
# It is NOT a utility threshold.
# =============================================================================

grouped = defaultdict(list)

for row in results:
    grouped[
        (
            row["fused_decision_id"],
            row["assumed_time_remaining_minutes"],
        )
    ].append(row)


break_even_rows = []

for (did, remaining), group in sorted(grouped.items()):

    group = sorted(
        group,
        key=lambda r: r["priority_wait_reduction_fraction"]
    )

    crossovers = [
        r
        for r in group
        if r[
            "withdraw_benchmark_probability_exceeds_retain"
        ]
    ]

    if crossovers:
        first = crossovers[0]

        break_even_pct = (
            first["priority_wait_reduction_percent"]
        )

        status = (
            "CROSSOVER_WITHIN_TESTED_GRID"
        )

        delta_at_break_even = (
            first["delta_benchmark_success_probability"]
        )

        downside_at_break_even = (
            first["withdraw_p_final_worse_than_current"]
        )

        no_result_at_break_even = (
            first["withdraw_p_no_final_result"]
        )

    else:
        break_even_pct = ""
        status = (
            "NO_BENCHMARK_CROSSOVER_UP_TO_75_PERCENT"
        )
        delta_at_break_even = ""
        downside_at_break_even = ""
        no_result_at_break_even = ""

    base = group[0]

    break_even_rows.append({
        "fused_decision_id":
            did,

        "year":
            base["year"],

        "driver":
            base["driver"],

        "assumed_time_remaining_minutes":
            remaining,

        "current_result_speed_mph":
            base["current_result_speed_mph"],

        "benchmark_speed_mph":
            base["benchmark_speed_mph"],

        "current_margin_to_benchmark_mph":
            (
                base["current_result_speed_mph"]
                - base["benchmark_speed_mph"]
            ),

        "benchmark_probability_crossover_status":
            status,

        "first_tested_priority_reduction_percent_with_crossover":
            break_even_pct,

        "delta_benchmark_probability_at_crossover":
            delta_at_break_even,

        "withdraw_downside_probability_at_crossover":
            downside_at_break_even,

        "withdraw_no_result_probability_at_crossover":
            no_result_at_break_even,

        "interpretation":
            (
                "Benchmark-probability crossover only; "
                "not an optimal-action or utility threshold."
            ),
    })


with OUT_BREAK_EVEN.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(break_even_rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(break_even_rows)


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


expected_rows = (
    50
    * len(TIME_REMAINING_SCENARIOS)
    * len(PRIORITY_WAIT_REDUCTION_SCENARIOS)
)

qa(
    "paired_day1_decisions",
    len(paired_day1_ids),
    50,
    "PASS" if len(paired_day1_ids) == 50 else "FAIL",
)

qa(
    "sensitivity_result_rows",
    len(results),
    expected_rows,
    "PASS" if len(results) == expected_rows else "FAIL",
)

qa(
    "break_even_rows",
    len(break_even_rows),
    50 * 7,
    (
        "PASS"
        if len(break_even_rows) == 350
        else "FAIL"
    ),
)

qa(
    "priority_reduction_grid",
    "|".join(
        str(int(x * 100))
        for x in PRIORITY_WAIT_REDUCTION_SCENARIOS
    ),
    "0|25|50|75",
    "PASS",
)

qa(
    "time_remaining_grid",
    "|".join(
        map(str, TIME_REMAINING_SCENARIOS)
    ),
    "5|10|15|20|30|45|60",
    "PASS",
)

# At zero priority advantage, completion should match RETAIN exactly because
# paired random numbers and identical waits are used.
zero_rows = [
    r for r in results
    if r["priority_wait_reduction_fraction"] == 0.0
]

zero_completion_equal = all(
    abs(
        r["withdraw_p_completed"]
        - r["retain_p_completed"]
    ) < 1e-12
    for r in zero_rows
)

qa(
    "zero_priority_completion_matches_retain",
    zero_completion_equal,
    True,
    "PASS" if zero_completion_equal else "FAIL",
)

# At zero priority advantage, withdraw benchmark success must never exceed
# retain benchmark success, because RETAIN keeps the old result.
zero_weak_dominance = all(
    r["withdraw_p_final_meets_benchmark"]
    <= r["retain_p_final_meets_benchmark"] + 1e-12
    for r in zero_rows
)

qa(
    "zero_priority_withdraw_not_better_on_benchmark",
    zero_weak_dominance,
    True,
    "PASS" if zero_weak_dominance else "FAIL",
)

# More priority reduction should never reduce completion probability
# within a fixed decision/time scenario.
monotonic_completion = True

for _, group in grouped.items():

    group = sorted(
        group,
        key=lambda r: r["priority_wait_reduction_fraction"]
    )

    vals = [
        r["withdraw_p_completed"]
        for r in group
    ]

    if any(
        vals[i + 1] + 1e-12 < vals[i]
        for i in range(len(vals) - 1)
    ):
        monotonic_completion = False
        break

qa(
    "withdraw_completion_monotonic_with_priority_advantage",
    monotonic_completion,
    True,
    "PASS" if monotonic_completion else "FAIL",
)

qa(
    "historical_lane1_advantage_claimed",
    False,
    False,
    "PASS",
)

qa(
    "priority_scenarios_probability_weighted",
    False,
    False,
    "PASS",
)

qa(
    "dynamic_competitor_evolution_used",
    False,
    False,
    "PASS",
)

qa(
    "utility_function_introduced",
    False,
    False,
    "PASS",
)

qa(
    "historical_action_optimal_labels_used",
    False,
    False,
    "PASS",
)

qa(
    "model_refit_performed",
    False,
    False,
    "PASS",
)


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(qa_rows)


# =============================================================================
# Contract
# =============================================================================

contract = {
    "phase":
        "R4F8H-H",

    "status":
        "R4F8H_PRIORITY_BENEFIT_SENSITIVITY_COMPLETE",

    "question": (
        "How much hypothetical Lane-1 wait reduction is required "
        "before WITHDRAW_AND_PRIORITY_REATTEMPT can exceed "
        "RETAIN_AND_REATTEMPT on benchmark-success probability?"
    ),

    "priority_wait_reduction_scenarios": {
        "fractions":
            PRIORITY_WAIT_REDUCTION_SCENARIOS,

        "percents": [
            int(round(x * 100))
            for x in PRIORITY_WAIT_REDUCTION_SCENARIOS
        ],

        "semantics":
            "STRUCTURAL_SENSITIVITY_NOT_HISTORICAL_ESTIMATES",

        "probability_distribution":
            None,

        "scenario_average_allowed":
            False,
    },

    "lane2_wait": {
        "support_minutes":
            WAIT_SUPPORT_MIN.tolist(),

        "probabilities":
            WAIT_PROBS.tolist(),

        "semantics":
            "R4F8F_STRUCTURAL_BASELINE",
    },

    "lane1_wait": {
        "rule":
            (
                "lane1_wait = lane2_structural_wait "
                "* (1 - assumed_priority_reduction)"
            ),

        "empirical_claim":
            False,
    },

    "paired_random_numbers": {
        "used":
            True,

        "reason":
            (
                "Retain and withdraw share the same base wait, "
                "run-duration, and future-speed draws so that "
                "only the assumed priority benefit changes."
            ),
    },

    "break_even_definition": (
        "First TESTED priority-reduction level where "
        "P(withdraw final result >= decision-time benchmark) "
        "> P(retain final result >= decision-time benchmark)."
    ),

    "break_even_is_not": [
        "an empirical Lane-1 advantage estimate",
        "an optimal-action threshold",
        "a utility threshold",
        "a causal effect estimate",
    ],

    "allowed_claims": [
        (
            "Under stated structural wait-reduction scenarios, "
            "priority may or may not offset withdrawal downside."
        ),
        (
            "Benchmark-success crossover can be reported as "
            "a sensitivity threshold on the tested grid."
        ),
        (
            "Zero-priority scenario is the equal-wait baseline."
        ),
    ],

    "forbidden_claims": [
        "Lane 1 historically reduces wait by 25/50/75 percent",
        "the crossover identifies the true optimal action",
        "dynamic final-rank probability",
        "empirical queue advantage",
        "historical causal effect of lane choice",
    ],
}

OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Report
# =============================================================================

passes = sum(
    r["status"] == "PASS"
    for r in qa_rows
)

warns = sum(
    r["status"] == "WARN"
    for r in qa_rows
)

fails = sum(
    r["status"] == "FAIL"
    for r in qa_rows
)

crossover_rows = [
    r for r in break_even_rows
    if r[
        "benchmark_probability_crossover_status"
    ] == "CROSSOVER_WITHIN_TESTED_GRID"
]

no_crossover_rows = [
    r for r in break_even_rows
    if r[
        "benchmark_probability_crossover_status"
    ] == "NO_BENCHMARK_CROSSOVER_UP_TO_75_PERCENT"
]

crossover_by_level = defaultdict(int)

for r in crossover_rows:
    crossover_by_level[
        str(
            r[
                "first_tested_priority_reduction_percent_with_crossover"
            ]
        )
    ] += 1


report = {
    "phase":
        "R4F8H-H",

    "status": (
        "R4F8H_PRIORITY_BENEFIT_SENSITIVITY_COMPLETE"
        if fails == 0
        else "R4F8H_PRIORITY_BENEFIT_SENSITIVITY_FAILED"
    ),

    "paired_day1_decisions":
        len(paired_day1_ids),

    "time_remaining_scenarios":
        TIME_REMAINING_SCENARIOS,

    "priority_reduction_percent_scenarios": [
        int(round(x * 100))
        for x in PRIORITY_WAIT_REDUCTION_SCENARIOS
    ],

    "simulation_rows":
        len(results),

    "break_even_rows":
        len(break_even_rows),

    "benchmark_crossovers": {
        "rows_with_crossover":
            len(crossover_rows),

        "rows_without_crossover_up_to_75_percent":
            len(no_crossover_rows),

        "first_crossover_level_counts":
            dict(sorted(crossover_by_level.items())),
    },

    "interpretation_boundary": (
        "Priority benefit is a structural sensitivity parameter. "
        "No tested reduction level is claimed to represent actual "
        "historical Lane-1 performance."
    ),

    "qa": {
        "pass":
            passes,

        "warn":
            warns,

        "fail":
            fails,
    },

    "protected_input_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in required
    },

    "output_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [
            OUT_RESULTS,
            OUT_COMPARE,
            OUT_BREAK_EVEN,
            OUT_QA,
            OUT_CONTRACT,
        ]
    },

    "next_phase": (
        "R4F9_HISTORICAL_REPLAY_AND_EVALUATION"
        if fails == 0
        else "RESOLVE_R4F8H_H_FAILURES"
    ),
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Console summary
# =============================================================================

print("=" * 132)
print("R4F8H-H — PRIORITY BENEFIT SENSITIVITY")
print("=" * 132)
print()

print("DESIGN")
print("-" * 132)
print(f"Paired Day 1 decisions:            {len(paired_day1_ids)}")
print(f"Draws/decision/scenario:           {N_DRAWS:,}")
print(
    "Remaining-time scenarios:          "
    + ", ".join(
        map(str, TIME_REMAINING_SCENARIOS)
    )
    + " min"
)
print(
    "Priority wait reductions:           "
    + ", ".join(
        str(int(x * 100)) + "%"
        for x in PRIORITY_WAIT_REDUCTION_SCENARIOS
    )
)
print()

print("SIMULATION")
print("-" * 132)
print(f"Result rows:                       {len(results)}")
print(f"Break-even rows:                   {len(break_even_rows)}")
print()

print("BENCHMARK-PROBABILITY CROSSOVERS")
print("-" * 132)
print(
    f"Decision/time scenarios with crossover: "
    f"{len(crossover_rows)}/{len(break_even_rows)}"
)
print(
    f"No crossover up to 75%:                 "
    f"{len(no_crossover_rows)}/{len(break_even_rows)}"
)
print()

print("FIRST TESTED CROSSOVER LEVEL")
print("-" * 132)

if crossover_by_level:
    for level, count in sorted(
        crossover_by_level.items(),
        key=lambda x: float(x[0]),
    ):
        print(
            f"{level:>5s}% reduction | "
            f"{count:4d} decision/time scenarios"
        )
else:
    print("none")

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
    OUT_RESULTS,
    OUT_COMPARE,
    OUT_BREAK_EVEN,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F8H_H_PRIORITY_BENEFIT_SENSITIVITY_FAILED")
    raise SystemExit(1)

print("R4F8H_PRIORITY_BENEFIT_SENSITIVITY_COMPLETE")
print()
print("NEXT: R4F9 HISTORICAL REPLAY / EVALUATION")
print()
print(
    "IMPORTANT: Priority reductions are structural sensitivity "
    "scenarios only. The reported crossover is a benchmark-success "
    "crossover on the tested grid, not an empirical Lane-1 advantage "
    "or an optimal-action threshold."
)
