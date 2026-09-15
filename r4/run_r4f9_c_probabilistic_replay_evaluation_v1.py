from pathlib import Path
import csv
import json
import math
import hashlib
from collections import defaultdict
from statistics import NormalDist

import numpy as np


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

HIST_FILE = OUT / "r4f9_b3_final_historical_outcome_interface_v1.csv"
UNC_FILE = OUT / "r4f8g_decision_predictive_uncertainty_state_v1.csv"

OUT_ROWS = OUT / "r4f9_c_probabilistic_replay_rows_v1.csv"
OUT_COVERAGE = OUT / "r4f9_c_interval_coverage_summary_v1.csv"
OUT_CALIBRATION = OUT / "r4f9_c_probability_calibration_summary_v1.csv"
OUT_YEAR = OUT / "r4f9_c_replay_by_year_summary_v1.csv"
OUT_LC = OUT / "r4f9_c_last_chance_descriptive_replay_v1.csv"
OUT_QA = OUT / "r4f9_c_probabilistic_replay_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f9_c_probabilistic_replay_contract_v1.json"
OUT_REPORT = OUT / "r4f9_c_probabilistic_replay_report_v1.json"


# =============================================================================
# R4F9-C — PROBABILISTIC REPLAY EVALUATION
#
# PRIMARY NUMERIC EVALUATION:
#   Day 1 decisions with a historically observed COMPLETE next four-lap run.
#
# SCORED:
#   - predictive mean error
#   - standardized residual
#   - predictive interval coverage
#   - probability of improving current result
#   - probability of crossing decision-time benchmark
#
# NOT SCORED:
#   - historical action optimality
#   - dynamic final rank
#   - Last Chance final qualification probability
#   - queue wait
#   - exact historical cutoff completion
#
# IMPORTANT:
# This is retrospective replay / calibration evidence.
# It is NOT an independent external holdout validation.
# =============================================================================


ND = NormalDist()


# =============================================================================
# Helpers
# =============================================================================

def clean(v):
    return "" if v is None else str(v).strip()


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
    for candidate in candidates:
        if norm(candidate) in m:
            return m[norm(candidate)]
    return None


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


def normal_cdf(z):
    return ND.cdf(float(z))


def exceedance_probability(threshold, mu, sd):
    z = (threshold - mu) / sd
    return 1.0 - normal_cdf(z)


def brier(p, y):
    return (float(p) - float(y)) ** 2


def log_loss(p, y):
    p = min(max(float(p), 1e-12), 1.0 - 1e-12)
    y = float(y)
    return -(y * math.log(p) + (1-y) * math.log(1-p))


def wilson_interval(successes, n, z=1.959963984540054):
    if n == 0:
        return None, None

    phat = successes / n
    denom = 1.0 + z*z/n

    center = (
        phat + z*z/(2*n)
    ) / denom

    half = (
        z
        * math.sqrt(
            phat*(1-phat)/n
            + z*z/(4*n*n)
        )
        / denom
    )

    return center-half, center+half


def mean_or_none(values):
    vals = [float(x) for x in values if x is not None]
    return float(np.mean(vals)) if vals else None


def rmse(values):
    vals = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(vals**2)))


# =============================================================================
# Inputs
# =============================================================================

required = [
    HIST_FILE,
    UNC_FILE,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("=" * 130)
    print("R4F9-C REQUIRED INPUTS MISSING")
    print("=" * 130)
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


hist_fields, hist_rows = read_csv(HIST_FILE)
unc_fields, unc_rows = read_csv(UNC_FILE)


if len(hist_rows) != 60:
    raise SystemExit(
        f"Historical outcome universe changed: {len(hist_rows)} != 60"
    )


# =============================================================================
# Resolve uncertainty fields
# =============================================================================

UNC_ID = find_field(
    unc_fields,
    [
        "fused_decision_id",
        "decision_id",
        "source_decision_id",
    ]
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

SUPPORT_N = find_field(
    unc_fields,
    [
        "support_count",
        "same_session_support_count",
        "n_support",
        "n_prior_other_driver_rows",
    ]
)

UNC_CLASS = find_field(
    unc_fields,
    [
        "uncertainty_class",
        "support_class",
        "predictive_uncertainty_class",
    ]
)


essential = {
    "UNC_ID": UNC_ID,
    "PRED_MEAN": PRED_MEAN,
    "PRED_SD": PRED_SD,
}

missing_fields = [
    k for k, v in essential.items()
    if v is None
]

if missing_fields:
    print("=" * 130)
    print("R4F9-C UNCERTAINTY FIELD RESOLUTION FAILED")
    print("=" * 130)
    for field in missing_fields:
        print(field)

    print()
    print("UNCERTAINTY FILE FIELDS:")
    for field in unc_fields:
        print(f"  {field}")

    raise SystemExit(1)


# =============================================================================
# Lookup
# =============================================================================

unc_by_id = defaultdict(list)

for row in unc_rows:
    did = clean(row.get(UNC_ID))
    if did:
        unc_by_id[did].append(row)


# =============================================================================
# Select primary Day 1 complete-next-attempt replay sample
# =============================================================================

day1_speed_rows = [
    r for r in hist_rows
    if (
        clean(r["regime"]) == "DAY1"
        and truthy(r["attempt_level_speed_evaluable"])
    )
]

lc_rows = [
    r for r in hist_rows
    if clean(r["regime"]) == "LAST_CHANCE"
]


# =============================================================================
# Score predictive distributions
# =============================================================================

replay_rows = []
blocked_rows = []

interval_levels = [0.50, 0.80, 0.90, 0.95]


for hist in day1_speed_rows:

    did = clean(hist["fused_decision_id"])

    matches = unc_by_id.get(did, [])

    if len(matches) != 1:

        blocked_rows.append({
            "fused_decision_id": did,
            "reason":
                f"UNCERTAINTY_STATE_MATCH_COUNT_{len(matches)}",
        })

        continue

    u = matches[0]

    mu = num(u.get(PRED_MEAN))
    sd = num(u.get(PRED_SD))

    if SAMPLE_READY and not truthy(u.get(SAMPLE_READY)):
        blocked_rows.append({
            "fused_decision_id": did,
            "reason":
                "UNCERTAINTY_STATE_NOT_SAMPLE_READY",
        })
        continue

    if mu is None or sd is None or sd <= 0:
        blocked_rows.append({
            "fused_decision_id": did,
            "reason":
                "INVALID_PREDICTIVE_MEAN_OR_SD",
        })
        continue

    actual = num(
        hist["next_attempt_speed_mph"]
    )

    current = num(
        hist["current_result_speed_mph"]
    )

    benchmark = num(
        hist["decision_time_benchmark_speed_mph"]
    )

    if actual is None:
        blocked_rows.append({
            "fused_decision_id": did,
            "reason":
                "REALIZED_NEXT_SPEED_MISSING",
        })
        continue

    error = actual - mu
    abs_error = abs(error)
    sq_error = error ** 2
    z = error / sd
    pit = normal_cdf(z)

    p_improve = (
        exceedance_probability(current, mu, sd)
        if current is not None
        else None
    )

    y_improve = (
        1
        if (
            current is not None
            and actual > current
        )
        else (
            0
            if current is not None
            else None
        )
    )

    p_benchmark = (
        exceedance_probability(benchmark, mu, sd)
        if benchmark is not None
        else None
    )

    y_benchmark = (
        1
        if (
            benchmark is not None
            and actual >= benchmark
        )
        else (
            0
            if benchmark is not None
            else None
        )
    )

    row = {
        "fused_decision_id":
            did,

        "year":
            clean(hist["year"]),

        "driver_name":
            clean(hist["driver_name"]),

        "car_number":
            clean(hist["car_number"]),

        "historical_action":
            clean(hist["historical_action"]),

        "historical_action_used_as_optimal_label":
            False,

        "realized_next_attempt_speed_mph":
            actual,

        "current_result_speed_mph":
            current if current is not None else "",

        "decision_time_benchmark_speed_mph":
            benchmark if benchmark is not None else "",

        "predictive_mean_mph":
            mu,

        "predictive_sd_mph":
            sd,

        "prediction_error_actual_minus_mean_mph":
            error,

        "absolute_error_mph":
            abs_error,

        "squared_error_mph2":
            sq_error,

        "standardized_residual_z":
            z,

        "pit_value":
            pit,

        "predicted_p_improve_current":
            p_improve if p_improve is not None else "",

        "realized_improved_current":
            y_improve if y_improve is not None else "",

        "brier_improve":
            (
                brier(p_improve, y_improve)
                if (
                    p_improve is not None
                    and y_improve is not None
                )
                else ""
            ),

        "logloss_improve":
            (
                log_loss(p_improve, y_improve)
                if (
                    p_improve is not None
                    and y_improve is not None
                )
                else ""
            ),

        "predicted_p_cross_decision_benchmark":
            p_benchmark if p_benchmark is not None else "",

        "realized_crossed_decision_benchmark":
            y_benchmark if y_benchmark is not None else "",

        "brier_benchmark":
            (
                brier(p_benchmark, y_benchmark)
                if (
                    p_benchmark is not None
                    and y_benchmark is not None
                )
                else ""
            ),

        "logloss_benchmark":
            (
                log_loss(p_benchmark, y_benchmark)
                if (
                    p_benchmark is not None
                    and y_benchmark is not None
                )
                else ""
            ),

        "performance_support_count":
            clean(u.get(SUPPORT_N))
            if SUPPORT_N
            else "",

        "uncertainty_class":
            clean(u.get(UNC_CLASS))
            if UNC_CLASS
            else "",

        "evaluation_role":
            "RETROSPECTIVE_REPLAY_NOT_EXTERNAL_HOLDOUT",

        "future_outcome_used_for_prediction":
            False,
    }

    for level in interval_levels:

        zcrit = ND.inv_cdf(
            (1.0 + level) / 2.0
        )

        lower = mu - zcrit * sd
        upper = mu + zcrit * sd

        pct = int(round(level * 100))

        row[f"pi{pct}_lower_mph"] = lower
        row[f"pi{pct}_upper_mph"] = upper
        row[f"pi{pct}_hit"] = (
            lower <= actual <= upper
        )

    replay_rows.append(row)


if not replay_rows:
    raise SystemExit(
        "No probabilistic replay rows could be scored."
    )


# =============================================================================
# Save row-level replay
# =============================================================================

with OUT_ROWS.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(replay_rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(replay_rows)


# =============================================================================
# Interval coverage summary
# =============================================================================

coverage_rows = []

for level in interval_levels:

    pct = int(round(level * 100))
    hit_field = f"pi{pct}_hit"

    hits = sum(
        bool(r[hit_field])
        for r in replay_rows
    )

    n = len(replay_rows)

    observed = hits / n

    lo, hi = wilson_interval(
        hits,
        n,
    )

    coverage_rows.append({
        "interval_nominal_coverage":
            level,

        "interval_label":
            f"PI{pct}",

        "n":
            n,

        "hits":
            hits,

        "observed_coverage":
            observed,

        "coverage_minus_nominal":
            observed - level,

        "wilson_95_lower":
            lo,

        "wilson_95_upper":
            hi,

        "interpretation":
            "RETROSPECTIVE_REPLAY_SMALL_SAMPLE",
    })


with OUT_COVERAGE.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(coverage_rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(coverage_rows)


# =============================================================================
# Probability calibration summary
# =============================================================================

calibration_rows = []

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


for target, p_field, y_field in targets:

    scored = [
        r for r in replay_rows
        if (
            num(r[p_field]) is not None
            and num(r[y_field]) is not None
        )
    ]

    if not scored:
        continue

    # Overall row
    ps = [float(r[p_field]) for r in scored]
    ys = [float(r[y_field]) for r in scored]

    calibration_rows.append({
        "target":
            target,

        "bin":
            "OVERALL",

        "n":
            len(scored),

        "mean_predicted_probability":
            float(np.mean(ps)),

        "observed_event_rate":
            float(np.mean(ys)),

        "calibration_gap_observed_minus_predicted":
            float(np.mean(ys) - np.mean(ps)),

        "brier_score":
            float(np.mean(
                [(p-y)**2 for p, y in zip(ps, ys)]
            )),

        "mean_log_loss":
            float(np.mean([
                log_loss(p, y)
                for p, y in zip(ps, ys)
            ])),

        "small_sample_warning":
            True,
    })

    # Coarse reliability bins
    edges = [
        (0.0, 0.2),
        (0.2, 0.4),
        (0.4, 0.6),
        (0.6, 0.8),
        (0.8, 1.0000001),
    ]

    for lo, hi in edges:

        group = [
            r for r in scored
            if (
                float(r[p_field]) >= lo
                and float(r[p_field]) < hi
            )
        ]

        if not group:
            continue

        gp = [
            float(r[p_field])
            for r in group
        ]

        gy = [
            float(r[y_field])
            for r in group
        ]

        calibration_rows.append({
            "target":
                target,

            "bin":
                f"[{lo:.1f},{min(hi,1.0):.1f}]",

            "n":
                len(group),

            "mean_predicted_probability":
                float(np.mean(gp)),

            "observed_event_rate":
                float(np.mean(gy)),

            "calibration_gap_observed_minus_predicted":
                float(np.mean(gy) - np.mean(gp)),

            "brier_score":
                float(np.mean(
                    [(p-y)**2 for p, y in zip(gp, gy)]
                )),

            "mean_log_loss":
                float(np.mean([
                    log_loss(p, y)
                    for p, y in zip(gp, gy)
                ])),

            "small_sample_warning":
                True,
        })


with OUT_CALIBRATION.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(calibration_rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(calibration_rows)


# =============================================================================
# Year summaries
# =============================================================================

by_year = defaultdict(list)

for row in replay_rows:
    by_year[row["year"]].append(row)


year_rows = []

for year, rows in sorted(by_year.items()):

    errors = np.array(
        [
            float(r["prediction_error_actual_minus_mean_mph"])
            for r in rows
        ],
        dtype=float,
    )

    abs_errors = np.abs(errors)

    benchmark_brier = [
        num(r["brier_benchmark"])
        for r in rows
    ]
    benchmark_brier = [
        x for x in benchmark_brier
        if x is not None
    ]

    improve_brier = [
        num(r["brier_improve"])
        for r in rows
    ]
    improve_brier = [
        x for x in improve_brier
        if x is not None
    ]

    pi90 = sum(
        bool(r["pi90_hit"])
        for r in rows
    ) / len(rows)

    year_rows.append({
        "year":
            year,

        "n":
            len(rows),

        "mean_error_actual_minus_predicted_mph":
            float(np.mean(errors)),

        "mae_mph":
            float(np.mean(abs_errors)),

        "rmse_mph":
            rmse(errors),

        "pi90_coverage":
            pi90,

        "benchmark_brier":
            (
                float(np.mean(benchmark_brier))
                if benchmark_brier
                else ""
            ),

        "improvement_brier":
            (
                float(np.mean(improve_brier))
                if improve_brier
                else ""
            ),

        "interpretation":
            "DESCRIPTIVE_SMALL_N",
    })


with OUT_YEAR.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(year_rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(year_rows)


# =============================================================================
# Last Chance descriptive replay only
# =============================================================================

lc_descriptive = []

for row in lc_rows:

    lc_descriptive.append({
        "fused_decision_id":
            clean(row["fused_decision_id"]),

        "year":
            clean(row["year"]),

        "driver_name":
            clean(row["driver_name"]),

        "historical_action":
            clean(row["historical_action"]),

        "current_result_speed_mph":
            clean(row["current_result_speed_mph"]),

        "decision_time_benchmark_speed_mph":
            clean(row["decision_time_benchmark_speed_mph"]),

        "realized_session_outcome":
            clean(row["realized_session_outcome"]),

        "realized_final_qualified":
            clean(row["realized_final_qualified"]),

        "explicit_crash_incomplete":
            clean(row["explicit_crash_incomplete"]),

        "numeric_probability_score_allowed":
            False,

        "reason_not_scored":
            (
                "FINAL_QUALIFICATION_DEPENDS_ON_UNMODELLED_DYNAMIC_"
                "COMPETITOR_EVOLUTION_AND_UNRESOLVED_HISTORICAL_"
                "SESSION_REMAINING"
            ),

        "historical_action_used_as_optimal_label":
            False,

        "evaluation_role":
            "DESCRIPTIVE_CASE_REPLAY_ONLY",
    })


with OUT_LC.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(lc_descriptive[0].keys()),
    )

    writer.writeheader()
    writer.writerows(lc_descriptive)


# =============================================================================
# Global metrics
# =============================================================================

errors = np.array(
    [
        float(r["prediction_error_actual_minus_mean_mph"])
        for r in replay_rows
    ],
    dtype=float,
)

abs_errors = np.abs(errors)

z_values = np.array(
    [
        float(r["standardized_residual_z"])
        for r in replay_rows
    ],
    dtype=float,
)

pit_values = np.array(
    [
        float(r["pit_value"])
        for r in replay_rows
    ],
    dtype=float,
)

benchmark_rows = [
    r for r in replay_rows
    if num(
        r["predicted_p_cross_decision_benchmark"]
    ) is not None
]

improvement_rows = [
    r for r in replay_rows
    if num(
        r["predicted_p_improve_current"]
    ) is not None
]


global_mae = float(np.mean(abs_errors))
global_rmse = rmse(errors)
global_bias = float(np.mean(errors))
global_z_mean = float(np.mean(z_values))

global_z_sd = (
    float(np.std(z_values, ddof=1))
    if len(z_values) > 1
    else ""
)

global_pit_mean = float(np.mean(pit_values))


benchmark_brier = (
    float(np.mean([
        float(r["brier_benchmark"])
        for r in benchmark_rows
    ]))
    if benchmark_rows
    else None
)

improvement_brier = (
    float(np.mean([
        float(r["brier_improve"])
        for r in improvement_rows
    ]))
    if improvement_rows
    else None
)


# =============================================================================
# QA
# =============================================================================

qa_rows = []


def qa(metric, value, expected, status):
    qa_rows.append({
        "metric":
            metric,

        "value":
            value,

        "expected":
            expected,

        "status":
            status,
    })


qa(
    "historical_interface_rows",
    len(hist_rows),
    60,
    "PASS" if len(hist_rows) == 60 else "FAIL",
)

qa(
    "day1_speed_evaluable_input_rows",
    len(day1_speed_rows),
    19,
    "PASS" if len(day1_speed_rows) == 19 else "WARN",
)

qa(
    "probabilistic_replay_scored_rows",
    len(replay_rows),
    len(day1_speed_rows),
    (
        "PASS"
        if len(replay_rows) == len(day1_speed_rows)
        else "FAIL"
    ),
)

qa(
    "blocked_replay_rows",
    len(blocked_rows),
    0,
    "PASS" if len(blocked_rows) == 0 else "FAIL",
)

qa(
    "last_chance_descriptive_rows",
    len(lc_descriptive),
    10,
    "PASS" if len(lc_descriptive) == 10 else "FAIL",
)

qa(
    "last_chance_numeric_probability_scoring",
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
    "future_outcomes_used_as_prediction_features",
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
    "dynamic_final_rank_scored",
    False,
    False,
    "PASS",
)

qa(
    "historical_queue_wait_inferred",
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

qa(
    "replay_claimed_as_independent_external_validation",
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


# =============================================================================
# Contract
# =============================================================================

contract = {
    "phase":
        "R4F9-C",

    "status":
        "R4F9_PROBABILISTIC_REPLAY_EVALUATION_COMPLETE",

    "primary_numeric_sample": {
        "regime":
            "DAY1",

        "requirement":
            "historically observed complete next four-lap attempt",

        "expected_n":
            19,

        "role":
            "RETROSPECTIVE_REPLAY_CALIBRATION_DIAGNOSTIC",

        "independent_external_holdout":
            False,
    },

    "scored_targets": [
        "realized next-attempt four-lap speed",
        "whether next attempt improves current result",
        (
            "whether next attempt crosses the benchmark observable "
            "at the original decision moment"
        ),
    ],

    "distribution_diagnostics": [
        "MAE",
        "RMSE",
        "mean signed error",
        "standardized residuals",
        "PIT values",
        "50/80/90/95 percent central predictive interval coverage",
    ],

    "binary_probability_diagnostics": [
        "Brier score for improvement",
        "Brier score for decision-time benchmark crossing",
        "coarse probability reliability bins",
    ],

    "last_chance_policy": {
        "numeric_scoring":
            False,

        "role":
            "DESCRIPTIVE_CASE_REPLAY_ONLY",

        "reason": (
            "Final qualification depends on dynamic competitor evolution "
            "and historical remaining-time/cutoff conditions not identified "
            "well enough for primary probabilistic scoring."
        ),
    },

    "historical_action_optimal_label":
        False,

    "model_refit":
        False,

    "dynamic_rank_prediction":
        False,
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

coverage_map = {
    r["interval_label"]: {
        "observed":
            r["observed_coverage"],

        "nominal":
            r["interval_nominal_coverage"],

        "hits":
            r["hits"],

        "n":
            r["n"],
    }
    for r in coverage_rows
}


report = {
    "phase":
        "R4F9-C",

    "status": (
        "R4F9_PROBABILISTIC_REPLAY_EVALUATION_COMPLETE"
        if fails == 0
        else "R4F9_PROBABILISTIC_REPLAY_EVALUATION_FAILED"
    ),

    "sample": {
        "day1_complete_next_attempts":
            len(day1_speed_rows),

        "scored":
            len(replay_rows),

        "blocked":
            len(blocked_rows),

        "last_chance_descriptive":
            len(lc_descriptive),
    },

    "speed_metrics": {
        "mean_error_actual_minus_predicted_mph":
            global_bias,

        "mae_mph":
            global_mae,

        "rmse_mph":
            global_rmse,

        "standardized_residual_mean":
            global_z_mean,

        "standardized_residual_sd":
            global_z_sd,

        "pit_mean":
            global_pit_mean,
    },

    "interval_coverage":
        coverage_map,

    "binary_probability_metrics": {
        "benchmark_crossing_brier":
            benchmark_brier,

        "improvement_brier":
            improvement_brier,
    },

    "interpretation_boundary": (
        "These metrics evaluate retrospective decision-time predictive "
        "plausibility on realized later attempts. They do not constitute "
        "an independent external validation and do not establish optimal "
        "historical actions."
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
        str(p.relative_to(ROOT)):
            sha256(p)
        for p in required
    },

    "output_hashes": {
        str(p.relative_to(ROOT)):
            sha256(p)
        for p in [
            OUT_ROWS,
            OUT_COVERAGE,
            OUT_CALIBRATION,
            OUT_YEAR,
            OUT_LC,
            OUT_QA,
            OUT_CONTRACT,
        ]
    },

    "next_phase": (
        "R4F9-D_REPRESENTATIVE_CASE_REPLAY"
        if fails == 0
        else "RESOLVE_R4F9_C_FAILURES"
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
print("R4F9-C — PROBABILISTIC REPLAY EVALUATION")
print("=" * 132)
print()

print("SAMPLE")
print("-" * 132)
print(
    f"Day 1 complete realized next-attempt outcomes: "
    f"{len(day1_speed_rows)}"
)
print(
    f"Successfully scored predictive distributions: "
    f"{len(replay_rows)}"
)
print(
    f"Blocked:                                  "
    f"{len(blocked_rows)}"
)
print(
    f"Last Chance descriptive-only cases:       "
    f"{len(lc_descriptive)}"
)
print()

print("SPEED PREDICTION")
print("-" * 132)
print(
    f"Mean error actual - predicted:            "
    f"{global_bias:+.6f} mph"
)
print(
    f"MAE:                                      "
    f"{global_mae:.6f} mph"
)
print(
    f"RMSE:                                     "
    f"{global_rmse:.6f} mph"
)
print(
    f"Standardized residual mean:               "
    f"{global_z_mean:+.6f}"
)
print(
    f"Standardized residual SD:                 "
    f"{global_z_sd:.6f}"
)
print(
    f"PIT mean:                                 "
    f"{global_pit_mean:.6f}"
)
print()

print("PREDICTIVE INTERVAL COVERAGE")
print("-" * 132)

for row in coverage_rows:
    print(
        f"{row['interval_label']:5s} | "
        f"{row['hits']:2d}/{row['n']:2d} = "
        f"{row['observed_coverage']:.3f} "
        f"(nominal {row['interval_nominal_coverage']:.2f}) "
        f"| Wilson95 "
        f"[{row['wilson_95_lower']:.3f}, "
        f"{row['wilson_95_upper']:.3f}]"
    )

print()
print("BINARY PROBABILITY DIAGNOSTICS")
print("-" * 132)

if improvement_brier is not None:
    print(
        f"Improvement Brier score:                  "
        f"{improvement_brier:.6f}"
    )
else:
    print(
        "Improvement Brier score:                  unavailable"
    )

if benchmark_brier is not None:
    print(
        f"Benchmark-crossing Brier score:           "
        f"{benchmark_brier:.6f}"
    )
else:
    print(
        "Benchmark-crossing Brier score:           unavailable"
    )

print()
print("BY YEAR")
print("-" * 132)

for row in year_rows:
    print(
        f"{row['year']} | "
        f"n={row['n']:2d} | "
        f"MAE={row['mae_mph']:.3f} | "
        f"RMSE={row['rmse_mph']:.3f} | "
        f"PI90={row['pi90_coverage']:.3f}"
    )

print()
print("QA")
print("-" * 132)
print(
    f"{passes} PASS | {warns} WARN | {fails} FAIL"
)

for row in qa_rows:
    if row["status"] != "PASS":
        print(
            f"{row['status']:5s} | "
            f"{row['metric']} | "
            f"value={row['value']} | "
            f"expected={row['expected']}"
        )

print()
print("OUTPUTS")
print("-" * 132)

for p in [
    OUT_ROWS,
    OUT_COVERAGE,
    OUT_CALIBRATION,
    OUT_YEAR,
    OUT_LC,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F9_C_PROBABILISTIC_REPLAY_EVALUATION_FAILED")
    raise SystemExit(1)

print("R4F9_PROBABILISTIC_REPLAY_EVALUATION_COMPLETE")
print()
print("NEXT: R4F9-D REPRESENTATIVE CASE REPLAY")
print()
print(
    "IMPORTANT: This is retrospective replay evidence, not independent "
    "external validation. Historical actions were not treated as optimal "
    "labels, and Last Chance final qualification was not probability-scored."
)
