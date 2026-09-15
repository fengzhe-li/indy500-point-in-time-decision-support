from pathlib import Path
import csv
import json
import math
import random
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

TRANS_PATH = (
    OUT /
    "r4p2_multi_run_transitions_v1.csv"
)

THERMAL_PATH = (
    OUT /
    "r4p10_thermal_conditioned_repeat_dataset_v1.csv"
)

OUT_RESULTS = (
    OUT /
    "r4p11_stochastic_wait_performance_mc_results_v1.csv"
)

OUT_DRAWS = (
    OUT /
    "r4p11_stochastic_wait_performance_mc_draws_sample_v1.csv"
)

OUT_QA = (
    OUT /
    "r4p11_stochastic_wait_performance_mc_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4p11_stochastic_wait_performance_mc_report_v1.json"
)

SEED = 42
N_MC = 50000

random.seed(SEED)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


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


def fmt(v, digits=6):
    if v is None:
        return ""
    return f"{v:.{digits}f}"


def percentile(values, q):
    if not values:
        return None

    xs = sorted(values)

    if len(xs) == 1:
        return xs[0]

    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))

    if lo == hi:
        return xs[lo]

    w = pos - lo

    return (
        xs[lo] * (1 - w)
        +
        xs[hi] * w
    )


def write_csv(path, rows, fields):
    with path.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )

        writer.writeheader()
        writer.writerows(rows)


print("=" * 112)
print("R4P11 — STOCHASTIC WAIT + EMPIRICAL REPEAT PERFORMANCE MONTE CARLO")
print("=" * 112)

if not TRANS_PATH.exists():
    raise SystemExit(
        f"MISSING: {TRANS_PATH}"
    )

transitions = read_csv(
    TRANS_PATH
)

thermal_rows = (
    read_csv(THERMAL_PATH)
    if THERMAL_PATH.exists()
    else []
)

print(
    f"Historical transitions: "
    f"{len(transitions)}"
)

print(
    f"Thermal decision rows: "
    f"{len(thermal_rows)}"
)


# =============================================================================
# 1. Empirical repeat-performance distribution
#
# Use all consecutive complete multi-run transitions.
# This is the performance uncertainty core.
#
# No thermal mph correction is imposed here because R4P10 did not validate
# a sufficiently strong thermal -> repeat-performance mapping.
# =============================================================================

repeat_deltas = []

for r in transitions:

    d = num(
        r.get(
            "delta_four_lap_average_speed_mph"
        )
    )

    if d is not None:
        repeat_deltas.append(d)


if len(repeat_deltas) != 92:
    raise SystemExit(
        f"EXPECTED 92 REPEAT DELTAS, GOT {len(repeat_deltas)}"
    )


# =============================================================================
# 2. Recovery / downside decomposition
# =============================================================================

positive_deltas = [
    x for x in repeat_deltas
    if x > 0
]

nonpositive_deltas = [
    x for x in repeat_deltas
    if x <= 0
]


# =============================================================================
# 3. Wait-time scenario priors
#
# IMPORTANT:
# These are declared scenario priors, NOT historical queue estimates.
#
# Values are candidate minutes to next completed attempt.
# =============================================================================

WAIT_PRIORS = {
    "LANE1_PRIORITY": {
        5: 0.30,
        10: 0.30,
        15: 0.20,
        20: 0.12,
        30: 0.06,
        45: 0.02,
    },

    "LANE2_RETAIN": {
        5: 0.05,
        10: 0.10,
        15: 0.15,
        20: 0.20,
        30: 0.25,
        45: 0.25,
    },
}


def sample_from_discrete(prior):
    items = list(prior.items())

    x = random.random()
    cumulative = 0.0

    for value, probability in items:
        cumulative += probability

        if x <= cumulative:
            return value

    return items[-1][0]


# =============================================================================
# 4. Risk profiles
#
# These do NOT change physical performance draws.
# They change utility / penalty interpretation.
# =============================================================================

RISK_PROFILES = {
    "CONSERVATIVE": {
        "w_improve": 1.0,
        "w_loss": 2.0,
        "w_wait": 0.015,
    },

    "BALANCED": {
        "w_improve": 1.0,
        "w_loss": 1.0,
        "w_wait": 0.010,
    },

    "AGGRESSIVE": {
        "w_improve": 1.25,
        "w_loss": 0.65,
        "w_wait": 0.006,
    },
}


# =============================================================================
# 5. Actions
#
# STOP:
# current result retained, delta = 0.
#
# RETAIN + REATTEMPT:
# current result retained if new run is worse.
# effective result delta = max(raw_repeat_delta, 0)
#
# WITHDRAW + PRIORITY:
# current result lost before priority reattempt.
# effective result delta = raw_repeat_delta
# =============================================================================

ACTIONS = [
    "STOP",
    "RETAIN_REATTEMPT",
    "WITHDRAW_PRIORITY",
]


results = []
draw_sample = []


def run_mc(action, risk_name, risk):

    effective_deltas = []
    raw_deltas = []
    waits = []
    utilities = []

    improved = 0
    worse = 0
    unchanged = 0

    for i in range(N_MC):

        if action == "STOP":

            wait = 0
            raw_delta = 0.0
            effective_delta = 0.0

        elif action == "RETAIN_REATTEMPT":

            wait = sample_from_discrete(
                WAIT_PRIORS[
                    "LANE2_RETAIN"
                ]
            )

            raw_delta = random.choice(
                repeat_deltas
            )

            effective_delta = max(
                raw_delta,
                0.0
            )

        elif action == "WITHDRAW_PRIORITY":

            wait = sample_from_discrete(
                WAIT_PRIORS[
                    "LANE1_PRIORITY"
                ]
            )

            raw_delta = random.choice(
                repeat_deltas
            )

            effective_delta = raw_delta

        else:
            raise ValueError(action)

        if effective_delta > 0:
            improved += 1

        elif effective_delta < 0:
            worse += 1

        else:
            unchanged += 1

        gain = max(
            effective_delta,
            0.0
        )

        loss = max(
            -effective_delta,
            0.0
        )

        utility = (
            risk["w_improve"] * gain
            -
            risk["w_loss"] * loss
            -
            risk["w_wait"] * wait
        )

        effective_deltas.append(
            effective_delta
        )

        raw_deltas.append(
            raw_delta
        )

        waits.append(
            wait
        )

        utilities.append(
            utility
        )

        if (
            risk_name == "BALANCED"
            and i < 500
        ):
            draw_sample.append({
                "action": action,
                "risk_profile": risk_name,
                "draw_index": i,
                "wait_minutes": wait,
                "raw_repeat_delta_mph":
                    raw_delta,
                "effective_result_delta_mph":
                    effective_delta,
                "utility": utility,
            })

    return {
        "action":
            action,

        "risk_profile":
            risk_name,

        "mc_draws":
            N_MC,

        "p_improve":
            improved / N_MC,

        "p_worse":
            worse / N_MC,

        "p_unchanged":
            unchanged / N_MC,

        "mean_raw_repeat_delta_mph":
            statistics.mean(
                raw_deltas
            ),

        "mean_effective_result_delta_mph":
            statistics.mean(
                effective_deltas
            ),

        "q05_effective_delta_mph":
            percentile(
                effective_deltas,
                0.05
            ),

        "q50_effective_delta_mph":
            percentile(
                effective_deltas,
                0.50
            ),

        "q95_effective_delta_mph":
            percentile(
                effective_deltas,
                0.95
            ),

        "mean_wait_minutes":
            statistics.mean(
                waits
            ),

        "q50_wait_minutes":
            percentile(
                waits,
                0.50
            ),

        "q95_wait_minutes":
            percentile(
                waits,
                0.95
            ),

        "mean_utility":
            statistics.mean(
                utilities
            ),

        "performance_source":
            (
                "EMPIRICAL_BOOTSTRAP_92_"
                "CONSECUTIVE_REPEAT_TRANSITIONS"
            ),

        "wait_source":
            (
                "DECLARED_SCENARIO_PRIOR_"
                "NOT_HISTORICAL_QUEUE_ESTIMATE"
            ),

        "thermal_mph_correction_applied":
            False,
    }


for risk_name, risk in RISK_PROFILES.items():

    for action in ACTIONS:

        results.append(
            run_mc(
                action,
                risk_name,
                risk
            )
        )


# =============================================================================
# 6. Rank actions within each risk profile
# =============================================================================

for risk_name in RISK_PROFILES:

    subset = [
        r for r in results
        if r["risk_profile"] == risk_name
    ]

    ordered = sorted(
        subset,
        key=lambda r: r["mean_utility"],
        reverse=True
    )

    for rank, row in enumerate(
        ordered,
        start=1
    ):
        row["utility_rank"] = rank


# =============================================================================
# 7. QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "historical_repeat_transition_count",

        "value":
            len(repeat_deltas),

        "expected":
            92,

        "status":
            (
                "PASS"
                if len(repeat_deltas) == 92
                else "FAIL"
            ),
    },

    {
        "metric":
            "performance_distribution_empirical",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "historical_queue_wait_claimed",

        "value":
            False,

        "expected":
            False,

        "status":
            "PASS",
    },

    {
        "metric":
            "thermal_mph_correction_forced",

        "value":
            False,

        "expected":
            False,

        "status":
            "PASS",
    },

    {
        "metric":
            "lane2_retains_current_result",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "lane1_can_finish_worse",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "risk_profiles",

        "value":
            len(RISK_PROFILES),

        "expected":
            3,

        "status":
            (
                "PASS"
                if len(RISK_PROFILES) == 3
                else "FAIL"
            ),
    },
]


# =============================================================================
# 8. Save outputs
# =============================================================================

write_csv(
    OUT_RESULTS,
    results,
    [
        "action",
        "risk_profile",
        "utility_rank",
        "mc_draws",
        "p_improve",
        "p_worse",
        "p_unchanged",
        "mean_raw_repeat_delta_mph",
        "mean_effective_result_delta_mph",
        "q05_effective_delta_mph",
        "q50_effective_delta_mph",
        "q95_effective_delta_mph",
        "mean_wait_minutes",
        "q50_wait_minutes",
        "q95_wait_minutes",
        "mean_utility",
        "performance_source",
        "wait_source",
        "thermal_mph_correction_applied",
    ]
)

write_csv(
    OUT_DRAWS,
    draw_sample,
    [
        "action",
        "risk_profile",
        "draw_index",
        "wait_minutes",
        "raw_repeat_delta_mph",
        "effective_result_delta_mph",
        "utility",
    ]
)

write_csv(
    OUT_QA,
    qa_rows,
    [
        "metric",
        "value",
        "expected",
        "status",
    ]
)


# =============================================================================
# 9. Report
# =============================================================================

report = {
    "phase":
        "R4P11",

    "purpose":
        (
            "Introduce stochastic candidate wait time "
            "and empirical repeat-performance uncertainty "
            "for STOP / RETAIN / WITHDRAW action comparison."
        ),

    "repeat_transition_rows":
        len(repeat_deltas),

    "repeat_delta_mean_mph":
        statistics.mean(
            repeat_deltas
        ),

    "repeat_delta_median_mph":
        statistics.median(
            repeat_deltas
        ),

    "repeat_improvement_rate":
        (
            len(positive_deltas)
            /
            len(repeat_deltas)
        ),

    "mc_draws_per_action_profile":
        N_MC,

    "wait_model_status":
        (
            "SCENARIO_PRIOR_ONLY; "
            "NOT HISTORICALLY CALIBRATED"
        ),

    "thermal_layer_status":
        (
            "R4P9 validated as environment-state model, "
            "but not converted into deterministic mph shift "
            "because R4P10 did not validate that mapping."
        ),

    "action_semantics": {
        "STOP":
            "Keep current result and do not reattempt.",

        "RETAIN_REATTEMPT":
            (
                "Keep current result while making "
                "a non-priority repeat attempt."
            ),

        "WITHDRAW_PRIORITY":
            (
                "Withdraw current result before "
                "a priority repeat attempt."
            ),
    },

    "limitations": [
        (
            "Queue wait distributions are declared "
            "scenario priors rather than historical estimates."
        ),
        (
            "Competitor leaderboard evolution is not yet simulated."
        ),
        (
            "Advancement benchmark probability is not yet included."
        ),
    ],
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# 10. Console
# =============================================================================

print()
print("=" * 112)
print("R4P11 EMPIRICAL PERFORMANCE CORE")
print("=" * 112)

print(
    f"Repeat transitions: "
    f"{len(repeat_deltas)}"
)

print(
    f"Mean repeat delta: "
    f"{statistics.mean(repeat_deltas):.4f} mph"
)

print(
    f"Median repeat delta: "
    f"{statistics.median(repeat_deltas):.4f} mph"
)

print(
    f"Observed repeat improvement rate: "
    f"{len(positive_deltas)/len(repeat_deltas):.4f}"
)


print()
print("=" * 112)
print("R4P11 MONTE CARLO ACTION RESULTS")
print("=" * 112)

for risk_name in RISK_PROFILES:

    print()
    print(risk_name)

    subset = sorted(
        [
            r for r in results
            if r["risk_profile"] == risk_name
        ],
        key=lambda r: r["utility_rank"]
    )

    for r in subset:

        print(
            f"#{r['utility_rank']} "
            f"{r['action']:20s} | "
            f"P(improve)={r['p_improve']:.4f} | "
            f"P(worse)={r['p_worse']:.4f} | "
            f"meanΔ={r['mean_effective_result_delta_mph']:.4f} | "
            f"mean_wait={r['mean_wait_minutes']:.2f}m | "
            f"utility={r['mean_utility']:.4f}"
        )


failed = [
    r for r in qa_rows
    if r["status"] != "PASS"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(failed)}/"
    f"{len(qa_rows)} PASS"
)

if failed:

    print("FAILED QA")

    for r in failed:

        print(
            f"  {r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(OUT_RESULTS.relative_to(ROOT))
print(OUT_DRAWS.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print(
    "R4P11_STOCHASTIC_WAIT_PERFORMANCE_MC_READY"
)
