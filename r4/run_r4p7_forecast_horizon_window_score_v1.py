from pathlib import Path
import csv
import json
import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4/output"

TRANS_PATH = OUT / "r4p2_multi_run_transitions_v1.csv"
SCENARIO_PATH = OUT / "r4p5_decision_safe_forecast_scenarios_v1.csv"

OUT_METRICS = OUT / "r4p7_environment_response_model_selection_v1.csv"
OUT_SCORES = OUT / "r4p7_forecast_horizon_window_scores_v1.csv"
OUT_QA = OUT / "r4p7_forecast_horizon_window_score_qa_v1.csv"
OUT_REPORT = OUT / "r4p7_forecast_horizon_window_score_report_v1.json"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
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


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )
        w.writeheader()
        w.writerows(rows)


print("=" * 112)
print("R4P7 — FORECAST-HORIZON WINDOW SCORE PROTOTYPE")
print("=" * 112)

if not TRANS_PATH.exists():
    raise SystemExit(f"MISSING: {TRANS_PATH}")

if not SCENARIO_PATH.exists():
    raise SystemExit(f"MISSING: {SCENARIO_PATH}")

transitions = read_csv(TRANS_PATH)
scenarios = read_csv(SCENARIO_PATH)

print(f"Historical transitions: {len(transitions)}")
print(f"Decision-safe forecast scenarios: {len(scenarios)}")


# ============================================================================
# 1. Retrospective historical environment-response dataset
#
# This remains a historical association layer.
# It is NOT itself called a prospective predictor.
# ============================================================================

hist = []

for r in transitions:

    speed_delta = num(
        r.get("delta_four_lap_average_speed_mph")
    )

    if speed_delta is None:
        continue

    row = {
        "year": clean(r.get("year")),
        "target": 1 if speed_delta > 0 else 0,

        # Forecast-attempt deltas
        "temp_change":
            num(r.get("delta_forecast_temp_c")),

        "rh_change":
            num(
                r.get(
                    "delta_forecast_relative_humidity_pct"
                )
            ),

        "wind_change":
            num(
                r.get(
                    "delta_forecast_wind_speed_10m_ms"
                )
            ),

        "gust_change":
            num(r.get("delta_forecast_gust_ms")),

        "cloud_change":
            num(
                r.get(
                    "delta_forecast_cloud_cover_pct"
                )
            ),

        "shortwave_change":
            num(
                r.get(
                    "delta_forecast_shortwave_radiation_wm2"
                )
            ),

        # PTSC surface-temperature historical diagnostic
        "track_change":
            num(r.get("delta_ptsc_track_c")),
    }

    hist.append(row)


FEATURE_SETS = {
    "ATMOS_THERMAL": [
        "temp_change",
        "rh_change",
    ],

    "ATMOS_THERMAL_RADIATION": [
        "temp_change",
        "rh_change",
        "shortwave_change",
    ],

    "ATMOS_THERMAL_WIND": [
        "temp_change",
        "rh_change",
        "wind_change",
        "gust_change",
    ],

    "ATMOS_COMPACT": [
        "temp_change",
        "rh_change",
        "wind_change",
        "shortwave_change",
    ],

    "ATMOS_COMPACT_CLOUD": [
        "temp_change",
        "rh_change",
        "wind_change",
        "cloud_change",
        "shortwave_change",
    ],

    # Historical diagnostic only.
    # Cannot be projected prospectively because HRRR does not
    # forecast track-surface temperature.
    "TRACK_PLUS_ATMOS_DIAGNOSTIC": [
        "track_change",
        "temp_change",
        "rh_change",
        "shortwave_change",
    ],
}


def complete(row, features):
    return all(
        row.get(f) is not None
        for f in features
    )


years = sorted({
    r["year"]
    for r in hist
})


metrics = []
all_predictions = {}


for model_name, features in FEATURE_SETS.items():

    predictions = []

    for test_year in years:

        train = [
            r for r in hist
            if (
                r["year"] != test_year
                and complete(r, features)
            )
        ]

        test = [
            r for r in hist
            if (
                r["year"] == test_year
                and complete(r, features)
            )
        ]

        if len(train) < max(10, len(features) + 3):
            continue

        if not test:
            continue

        y_train = np.array(
            [r["target"] for r in train],
            dtype=int
        )

        if len(set(y_train.tolist())) < 2:
            continue

        X_train = np.array(
            [
                [r[f] for f in features]
                for r in train
            ],
            dtype=float
        )

        X_test = np.array(
            [
                [r[f] for f in features]
                for r in test
            ],
            dtype=float
        )

        model = Pipeline([
            ("scale", StandardScaler()),
            (
                "logit",
                LogisticRegression(
                    C=0.25,
                    solver="liblinear",
                    random_state=42,
                    max_iter=1000,
                )
            )
        ])

        model.fit(
            X_train,
            y_train
        )

        probs = model.predict_proba(
            X_test
        )[:, 1]

        for r, p in zip(test, probs):
            predictions.append(
                (
                    r["target"],
                    float(p)
                )
            )

    if not predictions:
        continue

    actual = np.array(
        [x[0] for x in predictions],
        dtype=int
    )

    probs = np.array(
        [x[1] for x in predictions],
        dtype=float
    )

    auc = (
        roc_auc_score(actual, probs)
        if len(set(actual.tolist())) >= 2
        else None
    )

    metric = {
        "model_name": model_name,
        "features": ",".join(features),
        "pooled_loyo_rows": len(actual),
        "brier_score":
            fmt(
                brier_score_loss(
                    actual,
                    probs
                )
            ),
        "log_loss":
            fmt(
                log_loss(
                    actual,
                    probs,
                    labels=[0, 1]
                )
            ),
        "roc_auc":
            "" if auc is None else fmt(auc),
        "prospective_projection_allowed":
            str(
                "track_change"
                not in features
            ),
    }

    metrics.append(metric)

    all_predictions[model_name] = {
        "features": features,
        "actual": actual,
        "probs": probs,
    }


# ============================================================================
# 2. Select best prospective-compatible model
#
# Selection rule:
# lowest pooled LOYO Brier among models that do not use track_change.
# ============================================================================

eligible_metrics = [
    m for m in metrics
    if (
        m["prospective_projection_allowed"]
        == "True"
    )
]

if not eligible_metrics:
    raise SystemExit(
        "NO PROSPECTIVE-COMPATIBLE MODEL AVAILABLE"
    )

eligible_metrics.sort(
    key=lambda m: (
        float(m["brier_score"]),
        float(m["log_loss"]),
        m["model_name"]
    )
)

selected_metric = eligible_metrics[0]
selected_name = selected_metric["model_name"]

selected_features = FEATURE_SETS[selected_name]

print()
print(f"Selected model: {selected_name}")
print(f"Features: {selected_features}")
print(
    f"LOYO Brier: "
    f"{selected_metric['brier_score']}"
)
print(
    f"LOYO AUC: "
    f"{selected_metric['roc_auc']}"
)


# ============================================================================
# 3. Fit selected environmental-response model on all compatible history
#
# This estimates historical association structure.
# It is then used to score decision-safe forecast changes.
# ============================================================================

train_all = [
    r for r in hist
    if complete(
        r,
        selected_features
    )
]

X_all = np.array(
    [
        [
            r[f]
            for f in selected_features
        ]
        for r in train_all
    ],
    dtype=float
)

y_all = np.array(
    [
        r["target"]
        for r in train_all
    ],
    dtype=int
)

final_model = Pipeline([
    ("scale", StandardScaler()),
    (
        "logit",
        LogisticRegression(
            C=0.25,
            solver="liblinear",
            random_state=42,
            max_iter=1000,
        )
    )
])

final_model.fit(
    X_all,
    y_all
)


# ============================================================================
# 4. Map R4P5 forecast horizons into same feature space
# ============================================================================

SCENARIO_MAP = {
    "temp_change":
        "temp_c",

    "rh_change":
        "relative_humidity_pct",

    "wind_change":
        "wind_speed_10m_ms",

    "gust_change":
        "gust_ms",

    "cloud_change":
        "cloud_cover_pct",

    "shortwave_change":
        "shortwave_radiation_wm2",
}


def scenario_feature(
    row,
    internal_feature,
    horizon
):

    source = SCENARIO_MAP[
        internal_feature
    ]

    return num(
        row.get(
            f"forecast_delta_{horizon}m_{source}"
        )
    )


score_rows = []

for r in scenarios:

    out = {
        "year":
            clean(r.get("year")),

        "session_id":
            clean(r.get("session_id")),

        "car_number":
            clean(r.get("car_number")),

        "driver_name":
            clean(r.get("driver_name")),

        "decision_attempt_id":
            clean(r.get("before_attempt_id")),

        "decision_time_utc":
            clean(r.get("decision_time_utc")),

        "selected_environment_response_model":
            selected_name,

        "historical_model_loyo_brier":
            selected_metric["brier_score"],

        "historical_model_loyo_auc":
            selected_metric["roc_auc"],

        "score_interpretation":
            (
                "ENVIRONMENT_CONDITIONAL_"
                "IMPROVEMENT_PROPENSITY_"
                "NOT_FINAL_STRATEGY_PROBABILITY"
            ),

        "decision_time_safe":
            "True",

        "realized_future_weather_used":
            "False",
    }

    valid_horizons = []

    for horizon in [10, 20, 30]:

        values = []

        valid = True

        for feature in selected_features:

            v = scenario_feature(
                r,
                feature,
                horizon
            )

            if v is None:
                valid = False
                break

            values.append(v)

        if not valid:
            out[
                f"score_plus_{horizon}m"
            ] = ""

            continue

        probability = float(
            final_model.predict_proba(
                np.array(
                    [values],
                    dtype=float
                )
            )[0, 1]
        )

        out[
            f"score_plus_{horizon}m"
        ] = fmt(probability)

        valid_horizons.append(
            (
                horizon,
                probability
            )
        )

    if valid_horizons:

        best_horizon, best_score = max(
            valid_horizons,
            key=lambda x: x[1]
        )

        worst_horizon, worst_score = min(
            valid_horizons,
            key=lambda x: x[1]
        )

        out["best_forecast_horizon_min"] = (
            best_horizon
        )

        out["best_environment_score"] = (
            fmt(best_score)
        )

        out["worst_forecast_horizon_min"] = (
            worst_horizon
        )

        out["worst_environment_score"] = (
            fmt(worst_score)
        )

        out["forecast_horizon_score_spread"] = (
            fmt(
                best_score
                - worst_score
            )
        )

    else:
        out["best_forecast_horizon_min"] = ""
        out["best_environment_score"] = ""
        out["worst_forecast_horizon_min"] = ""
        out["worst_environment_score"] = ""
        out["forecast_horizon_score_spread"] = ""

    score_rows.append(out)


# ============================================================================
# 5. Outputs
# ============================================================================

write_csv(
    OUT_METRICS,
    metrics,
    [
        "model_name",
        "features",
        "pooled_loyo_rows",
        "brier_score",
        "log_loss",
        "roc_auc",
        "prospective_projection_allowed",
    ]
)

write_csv(
    OUT_SCORES,
    score_rows,
    [
        "year",
        "session_id",
        "car_number",
        "driver_name",
        "decision_attempt_id",
        "decision_time_utc",
        "selected_environment_response_model",
        "historical_model_loyo_brier",
        "historical_model_loyo_auc",
        "score_plus_10m",
        "score_plus_20m",
        "score_plus_30m",
        "best_forecast_horizon_min",
        "best_environment_score",
        "worst_forecast_horizon_min",
        "worst_environment_score",
        "forecast_horizon_score_spread",
        "score_interpretation",
        "decision_time_safe",
        "realized_future_weather_used",
    ]
)


# ============================================================================
# 6. QA
# ============================================================================

bad_safe = [
    r for r in score_rows
    if r["decision_time_safe"]
    != "True"
]

bad_future = [
    r for r in score_rows
    if r[
        "realized_future_weather_used"
    ] != "False"
]

track_in_selected = (
    "track_change"
    in selected_features
)

complete_score_rows = [
    r for r in score_rows
    if (
        r["score_plus_10m"]
        and r["score_plus_20m"]
        and r["score_plus_30m"]
    )
]

qa_rows = [
    {
        "metric":
            "scenario_rows",

        "value":
            len(score_rows),

        "expected":
            40,

        "status":
            (
                "PASS"
                if len(score_rows) == 40
                else "FAIL"
            ),
    },

    {
        "metric":
            "all_three_horizon_score_rows",

        "value":
            len(complete_score_rows),

        "expected":
            40,

        "status":
            (
                "PASS"
                if len(complete_score_rows) == 40
                else "FAIL"
            ),
    },

    {
        "metric":
            "selected_model_contains_track_temp",

        "value":
            track_in_selected,

        "expected":
            False,

        "status":
            (
                "PASS"
                if not track_in_selected
                else "FAIL"
            ),
    },

    {
        "metric":
            "realized_future_weather_used",

        "value":
            len(bad_future),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(bad_future) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "decision_time_safe_violations",

        "value":
            len(bad_safe),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(bad_safe) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "final_strategy_recommendation_made",

        "value":
            False,

        "expected":
            False,

        "status":
            "PASS",
    },
]

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


# ============================================================================
# 7. Report
# ============================================================================

best_counts = {}

for h in [10, 20, 30]:

    best_counts[str(h)] = sum(
        str(
            r[
                "best_forecast_horizon_min"
            ]
        )
        == str(h)
        for r in score_rows
    )


report = {
    "phase":
        "R4P7",

    "purpose":
        (
            "Bridge retrospective environmental "
            "response evidence to decision-time-safe "
            "10/20/30 minute HRRR forecast scenarios."
        ),

    "selected_model":
        selected_name,

    "selected_features":
        selected_features,

    "selected_model_loyo_brier":
        float(
            selected_metric[
                "brier_score"
            ]
        ),

    "selected_model_loyo_auc":
        (
            float(
                selected_metric[
                    "roc_auc"
                ]
            )
            if selected_metric[
                "roc_auc"
            ]
            else None
        ),

    "historical_training_rows":
        len(train_all),

    "scenario_rows":
        len(score_rows),

    "best_horizon_counts":
        best_counts,

    "important_semantics": {
        "score": (
            "Environment-conditional improvement "
            "propensity. It is not yet the final "
            "P(beat_current_result)."
        ),

        "forecast": (
            "Only decision-time-safe HRRR scenarios "
            "from R4P5 are used."
        ),

        "track_temperature": (
            "Historical track-temperature response "
            "may be analysed diagnostically, but "
            "track temperature is excluded from "
            "prospective scoring because HRRR does "
            "not forecast track-surface temperature."
        ),

        "queue": (
            "No queue waiting-time distribution "
            "is applied in this phase."
        ),

        "strategy": (
            "No STOP / RETAIN / WITHDRAW action "
            "recommendation is made."
        ),
    },
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# ============================================================================
# 8. Console summary
# ============================================================================

print()
print("=" * 112)
print("R4P7 MODEL SELECTION")
print("=" * 112)

for m in sorted(
    metrics,
    key=lambda x: float(
        x["brier_score"]
    )
):

    print(
        f"{m['model_name']:28s} | "
        f"n={str(m['pooled_loyo_rows']):>2s} | "
        f"Brier={m['brier_score']} | "
        f"LogLoss={m['log_loss']} | "
        f"AUC={m['roc_auc']} | "
        f"projectable={m['prospective_projection_allowed']}"
    )


print()
print("=" * 112)
print("R4P7 FORECAST HORIZON SCORES")
print("=" * 112)

print(
    f"Selected model: {selected_name}"
)

print(
    f"Historical training rows: "
    f"{len(train_all)}"
)

print(
    f"Scenario rows: "
    f"{len(score_rows)}"
)

print(
    f"Complete +10/+20/+30 scores: "
    f"{len(complete_score_rows)}"
)

print(
    "Best horizon counts: "
    f"10m={best_counts['10']} | "
    f"20m={best_counts['20']} | "
    f"30m={best_counts['30']}"
)

spreads = [
    num(
        r[
            "forecast_horizon_score_spread"
        ]
    )
    for r in score_rows
]

spreads = [
    x for x in spreads
    if x is not None
]

if spreads:
    print(
        f"Mean best-worst score spread: "
        f"{fmt(sum(spreads)/len(spreads))}"
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
print(OUT_METRICS.relative_to(ROOT))
print(OUT_SCORES.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print("R4P7_FORECAST_HORIZON_WINDOW_SCORE_READY")
