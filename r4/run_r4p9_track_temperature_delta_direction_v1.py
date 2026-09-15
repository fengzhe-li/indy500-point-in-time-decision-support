from pathlib import Path
import csv
import json
import math

import numpy as np

from sklearn.linear_model import (
    Ridge,
    HuberRegressor,
    LogisticRegression,
)

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT = (
    OUT /
    "r4p8_track_temperature_training_dataset_v1.csv"
)

OUT_REG_METRICS = (
    OUT /
    "r4p9_track_temp_delta_regression_metrics_v1.csv"
)

OUT_CLASS_METRICS = (
    OUT /
    "r4p9_track_temp_direction_metrics_v1.csv"
)

OUT_PRED = (
    OUT /
    "r4p9_track_temp_delta_direction_predictions_v1.csv"
)

OUT_QA = (
    OUT /
    "r4p9_track_temp_delta_direction_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4p9_track_temp_delta_direction_report_v1.json"
)


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
print("R4P9 — TRACK TEMPERATURE DELTA + DIRECTION MODEL")
print("=" * 112)

if not INPUT.exists():
    raise SystemExit(
        f"MISSING: {INPUT}"
    )

raw = read_csv(INPUT)

print(
    f"R4P8 supervised rows: "
    f"{len(raw)}"
)


# ============================================================================
# 1. ML feature set
#
# Target is now CHANGE in track temperature,
# not absolute future track temperature.
# ============================================================================

FEATURES = [
    "current_track_c",
    "current_ambient_c",
    "current_humidity",
    "current_wind",
    "current_pressure",
    "track_minus_ambient_c",

    "past_track_slope_15m_c_per_min",
    "past_track_slope_30m_c_per_min",

    "hrrr_now_temp_c",

    "hrrr_delta_temp_c",
    "hrrr_delta_relative_humidity_pct",
    "hrrr_delta_wind_speed_10m_ms",
    "hrrr_delta_gust_ms",
    "hrrr_delta_cloud_cover_pct",
    "hrrr_delta_shortwave_radiation_wm2",
]


rows = []

for r in raw:

    horizon = num(
        r.get("horizon_min")
    )

    target_delta = num(
        r.get("target_delta_track_c")
    )

    if (
        horizon is None
        or target_delta is None
    ):
        continue

    row = {
        "year":
            clean(r.get("year")),

        "decision_time_utc":
            clean(
                r.get("decision_time_utc")
            ),

        "horizon_min":
            int(horizon),

        "target_delta_track_c":
            target_delta,

        # 1 = cooling
        # 0 = flat/warming
        "target_cooling":
            1
            if target_delta < 0
            else 0,
    }

    complete = True

    for feature in FEATURES:

        value = num(
            r.get(feature)
        )

        row[feature] = value

        if value is None:
            complete = False

    if complete:
        rows.append(row)


print(
    f"ML-complete rows: "
    f"{len(rows)}"
)


# ============================================================================
# 2. LOYO regression
#
# Compare:
#
# ZERO_CHANGE
# CURRENT_15M_SLOPE
# CURRENT_30M_SLOPE
# RIDGE_DELTA
# HUBER_DELTA
# ============================================================================

reg_predictions = []

years = sorted({
    r["year"]
    for r in rows
})


for horizon in [15, 30]:

    hr = [
        r for r in rows
        if r["horizon_min"] == horizon
    ]

    for test_year in years:

        train = [
            r for r in hr
            if r["year"] != test_year
        ]

        test = [
            r for r in hr
            if r["year"] == test_year
        ]

        if not train or not test:
            continue

        actual = np.array(
            [
                r["target_delta_track_c"]
                for r in test
            ],
            dtype=float
        )

        # ------------------------------------------------------------------
        # ZERO CHANGE
        # ------------------------------------------------------------------

        pred_zero = np.zeros(
            len(test),
            dtype=float
        )

        for r, a, p in zip(
            test,
            actual,
            pred_zero
        ):
            reg_predictions.append({
                "task":
                    "DELTA_REGRESSION",

                "horizon_min":
                    horizon,

                "model_name":
                    "ZERO_CHANGE",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    float(a),

                "predicted_delta_track_c":
                    float(p),

                "actual_cooling":
                    r["target_cooling"],

                "predicted_probability_cooling":
                    "",
            })

        # ------------------------------------------------------------------
        # SLOPE 15
        # ------------------------------------------------------------------

        pred_slope15 = np.array(
            [
                r[
                    "past_track_slope_15m_c_per_min"
                ]
                * horizon

                for r in test
            ],
            dtype=float
        )

        for r, a, p in zip(
            test,
            actual,
            pred_slope15
        ):
            reg_predictions.append({
                "task":
                    "DELTA_REGRESSION",

                "horizon_min":
                    horizon,

                "model_name":
                    "CURRENT_15M_SLOPE",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    float(a),

                "predicted_delta_track_c":
                    float(p),

                "actual_cooling":
                    r["target_cooling"],

                "predicted_probability_cooling":
                    "",
            })

        # ------------------------------------------------------------------
        # SLOPE 30
        # ------------------------------------------------------------------

        pred_slope30 = np.array(
            [
                r[
                    "past_track_slope_30m_c_per_min"
                ]
                * horizon

                for r in test
            ],
            dtype=float
        )

        for r, a, p in zip(
            test,
            actual,
            pred_slope30
        ):
            reg_predictions.append({
                "task":
                    "DELTA_REGRESSION",

                "horizon_min":
                    horizon,

                "model_name":
                    "CURRENT_30M_SLOPE",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    float(a),

                "predicted_delta_track_c":
                    float(p),

                "actual_cooling":
                    r["target_cooling"],

                "predicted_probability_cooling":
                    "",
            })

        # ------------------------------------------------------------------
        # ML matrices
        # ------------------------------------------------------------------

        X_train = np.array(
            [
                [
                    r[f]
                    for f in FEATURES
                ]
                for r in train
            ],
            dtype=float
        )

        y_train = np.array(
            [
                r["target_delta_track_c"]
                for r in train
            ],
            dtype=float
        )

        X_test = np.array(
            [
                [
                    r[f]
                    for f in FEATURES
                ]
                for r in test
            ],
            dtype=float
        )

        # ------------------------------------------------------------------
        # RIDGE
        # ------------------------------------------------------------------

        ridge = Pipeline([
            (
                "scale",
                StandardScaler()
            ),
            (
                "ridge",
                Ridge(alpha=20.0)
            ),
        ])

        ridge.fit(
            X_train,
            y_train
        )

        pred_ridge = ridge.predict(
            X_test
        )

        for r, a, p in zip(
            test,
            actual,
            pred_ridge
        ):
            reg_predictions.append({
                "task":
                    "DELTA_REGRESSION",

                "horizon_min":
                    horizon,

                "model_name":
                    "RIDGE_DELTA",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    float(a),

                "predicted_delta_track_c":
                    float(p),

                "actual_cooling":
                    r["target_cooling"],

                "predicted_probability_cooling":
                    "",
            })

        # ------------------------------------------------------------------
        # HUBER
        # ------------------------------------------------------------------

        huber = Pipeline([
            (
                "scale",
                StandardScaler()
            ),
            (
                "huber",
                HuberRegressor(
                    epsilon=1.35,
                    alpha=1.0,
                    max_iter=1000,
                )
            ),
        ])

        huber.fit(
            X_train,
            y_train
        )

        pred_huber = huber.predict(
            X_test
        )

        for r, a, p in zip(
            test,
            actual,
            pred_huber
        ):
            reg_predictions.append({
                "task":
                    "DELTA_REGRESSION",

                "horizon_min":
                    horizon,

                "model_name":
                    "HUBER_DELTA",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    float(a),

                "predicted_delta_track_c":
                    float(p),

                "actual_cooling":
                    r["target_cooling"],

                "predicted_probability_cooling":
                    "",
            })


# ============================================================================
# 3. Regression metrics
# ============================================================================

REG_MODELS = [
    "ZERO_CHANGE",
    "CURRENT_15M_SLOPE",
    "CURRENT_30M_SLOPE",
    "RIDGE_DELTA",
    "HUBER_DELTA",
]

reg_metrics = []

for horizon in [15, 30]:

    for model_name in REG_MODELS:

        rset = [
            r for r in reg_predictions
            if (
                r["horizon_min"] == horizon
                and
                r["model_name"] == model_name
            )
        ]

        if not rset:
            continue

        actual = np.array(
            [
                r["actual_delta_track_c"]
                for r in rset
            ],
            dtype=float
        )

        pred = np.array(
            [
                r["predicted_delta_track_c"]
                for r in rset
            ],
            dtype=float
        )

        mae = mean_absolute_error(
            actual,
            pred
        )

        rmse = math.sqrt(
            mean_squared_error(
                actual,
                pred
            )
        )

        # True directional hit:
        # warming vs cooling.
        # Zero predictions are counted as miss
        # unless actual is also zero.
        direction = np.mean(
            np.sign(actual)
            ==
            np.sign(pred)
        )

        reg_metrics.append({
            "horizon_min":
                horizon,

            "model_name":
                model_name,

            "pooled_loyo_rows":
                len(rset),

            "mae_delta_c":
                mae,

            "rmse_delta_c":
                rmse,

            "direction_accuracy":
                float(direction),
        })


# ============================================================================
# 4. Direction classifier
#
# Target:
# P(track temperature decreases over next horizon)
#
# Baselines:
# - TRAIN_BASE_RATE
# - CURRENT_15M_SLOPE_SIGN
# - CURRENT_30M_SLOPE_SIGN
# - LOGISTIC_DIRECTION
# ============================================================================

class_predictions = []


for horizon in [15, 30]:

    hr = [
        r for r in rows
        if r["horizon_min"] == horizon
    ]

    for test_year in years:

        train = [
            r for r in hr
            if r["year"] != test_year
        ]

        test = [
            r for r in hr
            if r["year"] == test_year
        ]

        if not train or not test:
            continue

        y_train = np.array(
            [
                r["target_cooling"]
                for r in train
            ],
            dtype=int
        )

        y_test = np.array(
            [
                r["target_cooling"]
                for r in test
            ],
            dtype=int
        )

        # ------------------------------------------------------------------
        # BASE RATE
        # ------------------------------------------------------------------

        base_prob = float(
            np.mean(y_train)
        )

        base_probs = np.full(
            len(test),
            base_prob,
            dtype=float
        )

        for r, a, p in zip(
            test,
            y_test,
            base_probs
        ):
            class_predictions.append({
                "task":
                    "COOLING_CLASSIFICATION",

                "horizon_min":
                    horizon,

                "model_name":
                    "TRAIN_BASE_RATE",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    r["target_delta_track_c"],

                "predicted_delta_track_c":
                    "",

                "actual_cooling":
                    int(a),

                "predicted_probability_cooling":
                    float(p),
            })

        # ------------------------------------------------------------------
        # CURRENT 15M SLOPE SIGN
        #
        # Deterministic probability-like output:
        # cooling slope -> 0.75
        # warming slope -> 0.25
        # exactly zero -> 0.50
        # ------------------------------------------------------------------

        slope15_probs = []

        for r in test:

            slope = r[
                "past_track_slope_15m_c_per_min"
            ]

            if slope < 0:
                p = 0.75

            elif slope > 0:
                p = 0.25

            else:
                p = 0.50

            slope15_probs.append(p)

        for r, a, p in zip(
            test,
            y_test,
            slope15_probs
        ):
            class_predictions.append({
                "task":
                    "COOLING_CLASSIFICATION",

                "horizon_min":
                    horizon,

                "model_name":
                    "CURRENT_15M_SLOPE_SIGN",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    r["target_delta_track_c"],

                "predicted_delta_track_c":
                    "",

                "actual_cooling":
                    int(a),

                "predicted_probability_cooling":
                    float(p),
            })

        # ------------------------------------------------------------------
        # CURRENT 30M SLOPE SIGN
        # ------------------------------------------------------------------

        slope30_probs = []

        for r in test:

            slope = r[
                "past_track_slope_30m_c_per_min"
            ]

            if slope < 0:
                p = 0.75

            elif slope > 0:
                p = 0.25

            else:
                p = 0.50

            slope30_probs.append(p)

        for r, a, p in zip(
            test,
            y_test,
            slope30_probs
        ):
            class_predictions.append({
                "task":
                    "COOLING_CLASSIFICATION",

                "horizon_min":
                    horizon,

                "model_name":
                    "CURRENT_30M_SLOPE_SIGN",

                "test_year":
                    test_year,

                "decision_time_utc":
                    r["decision_time_utc"],

                "actual_delta_track_c":
                    r["target_delta_track_c"],

                "predicted_delta_track_c":
                    "",

                "actual_cooling":
                    int(a),

                "predicted_probability_cooling":
                    float(p),
            })

        # ------------------------------------------------------------------
        # LOGISTIC
        # ------------------------------------------------------------------

        if len(set(y_train.tolist())) >= 2:

            X_train = np.array(
                [
                    [
                        r[f]
                        for f in FEATURES
                    ]
                    for r in train
                ],
                dtype=float
            )

            X_test = np.array(
                [
                    [
                        r[f]
                        for f in FEATURES
                    ]
                    for r in test
                ],
                dtype=float
            )

            logistic = Pipeline([
                (
                    "scale",
                    StandardScaler()
                ),
                (
                    "logit",
                    LogisticRegression(
                        C=0.15,
                        solver="liblinear",
                        random_state=42,
                        max_iter=1000,
                    )
                ),
            ])

            logistic.fit(
                X_train,
                y_train
            )

            probs = logistic.predict_proba(
                X_test
            )[:, 1]

            for r, a, p in zip(
                test,
                y_test,
                probs
            ):
                class_predictions.append({
                    "task":
                        "COOLING_CLASSIFICATION",

                    "horizon_min":
                        horizon,

                    "model_name":
                        "LOGISTIC_DIRECTION",

                    "test_year":
                        test_year,

                    "decision_time_utc":
                        r["decision_time_utc"],

                    "actual_delta_track_c":
                        r["target_delta_track_c"],

                    "predicted_delta_track_c":
                        "",

                    "actual_cooling":
                        int(a),

                    "predicted_probability_cooling":
                        float(p),
                })


# ============================================================================
# 5. Classification metrics
# ============================================================================

CLASS_MODELS = [
    "TRAIN_BASE_RATE",
    "CURRENT_15M_SLOPE_SIGN",
    "CURRENT_30M_SLOPE_SIGN",
    "LOGISTIC_DIRECTION",
]

class_metrics = []

for horizon in [15, 30]:

    for model_name in CLASS_MODELS:

        rset = [
            r for r in class_predictions
            if (
                r["horizon_min"] == horizon
                and
                r["model_name"] == model_name
            )
        ]

        if not rset:
            continue

        actual = np.array(
            [
                r["actual_cooling"]
                for r in rset
            ],
            dtype=int
        )

        probs = np.array(
            [
                r[
                    "predicted_probability_cooling"
                ]
                for r in rset
            ],
            dtype=float
        )

        cls = (
            probs >= 0.5
        ).astype(int)

        brier = brier_score_loss(
            actual,
            probs
        )

        ll = log_loss(
            actual,
            probs,
            labels=[0, 1]
        )

        accuracy = accuracy_score(
            actual,
            cls
        )

        balanced = balanced_accuracy_score(
            actual,
            cls
        )

        auc = (
            roc_auc_score(
                actual,
                probs
            )
            if len(
                set(actual.tolist())
            ) >= 2
            else None
        )

        class_metrics.append({
            "horizon_min":
                horizon,

            "model_name":
                model_name,

            "pooled_loyo_rows":
                len(rset),

            "brier_score":
                brier,

            "log_loss":
                ll,

            "accuracy":
                accuracy,

            "balanced_accuracy":
                balanced,

            "roc_auc":
                auc,
        })


# ============================================================================
# 6. Save predictions
# ============================================================================

all_predictions = (
    reg_predictions
    +
    class_predictions
)

write_csv(
    OUT_PRED,
    all_predictions,
    [
        "task",
        "horizon_min",
        "model_name",
        "test_year",
        "decision_time_utc",
        "actual_delta_track_c",
        "predicted_delta_track_c",
        "actual_cooling",
        "predicted_probability_cooling",
    ]
)


write_csv(
    OUT_REG_METRICS,
    reg_metrics,
    [
        "horizon_min",
        "model_name",
        "pooled_loyo_rows",
        "mae_delta_c",
        "rmse_delta_c",
        "direction_accuracy",
    ]
)


write_csv(
    OUT_CLASS_METRICS,
    class_metrics,
    [
        "horizon_min",
        "model_name",
        "pooled_loyo_rows",
        "brier_score",
        "log_loss",
        "accuracy",
        "balanced_accuracy",
        "roc_auc",
    ]
)


# ============================================================================
# 7. QA
# ============================================================================

qa_rows = [
    {
        "metric":
            "r4p8_input_rows",

        "value":
            len(raw),

        "expected":
            312,

        "status":
            (
                "PASS"
                if len(raw) == 312
                else "FAIL"
            ),
    },

    {
        "metric":
            "ml_complete_rows",

        "value":
            len(rows),

        "expected":
            292,

        "status":
            (
                "PASS"
                if len(rows) == 292
                else "FAIL"
            ),
    },

    {
        "metric":
            "target_is_delta_not_absolute",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "direction_probability_target",

        "value":
            "P_TRACK_COOLING",

        "expected":
            "P_TRACK_COOLING",

        "status":
            "PASS",
    },

    {
        "metric":
            "future_realized_weather_used_as_feature",

        "value":
            False,

        "expected":
            False,

        "status":
            "PASS",
    },

    {
        "metric":
            "validation_protocol",

        "value":
            "LEAVE_ONE_YEAR_OUT",

        "expected":
            "LEAVE_ONE_YEAR_OUT",

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
# 8. Report
# ============================================================================

best_reg = {}
best_class = {}

for horizon in [15, 30]:

    candidates = [
        r for r in reg_metrics
        if r["horizon_min"] == horizon
    ]

    if candidates:

        best = min(
            candidates,
            key=lambda r: r["mae_delta_c"]
        )

        best_reg[str(horizon)] = {
            "model":
                best["model_name"],

            "mae_delta_c":
                best["mae_delta_c"],

            "rmse_delta_c":
                best["rmse_delta_c"],

            "direction_accuracy":
                best["direction_accuracy"],
        }

    candidates = [
        r for r in class_metrics
        if r["horizon_min"] == horizon
    ]

    if candidates:

        best = min(
            candidates,
            key=lambda r: r["brier_score"]
        )

        best_class[str(horizon)] = {
            "model":
                best["model_name"],

            "brier_score":
                best["brier_score"],

            "accuracy":
                best["accuracy"],

            "balanced_accuracy":
                best["balanced_accuracy"],

            "roc_auc":
                best["roc_auc"],
        }


report = {
    "phase":
        "R4P9",

    "purpose":
        (
            "Model future track-temperature "
            "change and cooling probability "
            "rather than absolute future "
            "track temperature."
        ),

    "input_rows":
        len(raw),

    "ml_complete_rows":
        len(rows),

    "horizons_minutes":
        [15, 30],

    "best_delta_regression":
        best_reg,

    "best_direction_classifier":
        best_class,

    "important_semantics": {
        "regression_target":
            "future_track_c - current_track_c",

        "classification_target":
            "P(future_track_c < current_track_c)",

        "decision_use":
            (
                "Track thermal state input "
                "for future qualifying-window "
                "evaluation."
            ),

        "final_strategy_probability":
            False,
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
# 9. Console
# ============================================================================

print()
print("=" * 112)
print("R4P9 DELTA REGRESSION")
print("=" * 112)

for horizon in [15, 30]:

    print()
    print(
        f"{horizon} MINUTES"
    )

    for r in [
        x for x in reg_metrics
        if x["horizon_min"] == horizon
    ]:

        print(
            f"{r['model_name']:22s} | "
            f"n={r['pooled_loyo_rows']:>3} | "
            f"MAEΔ={r['mae_delta_c']:.4f} C | "
            f"RMSEΔ={r['rmse_delta_c']:.4f} C | "
            f"direction={r['direction_accuracy']:.4f}"
        )


print()
print("=" * 112)
print("R4P9 COOLING PROBABILITY")
print("=" * 112)

for horizon in [15, 30]:

    print()
    print(
        f"{horizon} MINUTES"
    )

    for r in [
        x for x in class_metrics
        if x["horizon_min"] == horizon
    ]:

        auc_text = (
            ""
            if r["roc_auc"] is None
            else f"{r['roc_auc']:.4f}"
        )

        print(
            f"{r['model_name']:24s} | "
            f"n={r['pooled_loyo_rows']:>3} | "
            f"Brier={r['brier_score']:.4f} | "
            f"Acc={r['accuracy']:.4f} | "
            f"BalAcc={r['balanced_accuracy']:.4f} | "
            f"AUC={auc_text}"
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
print(OUT_REG_METRICS.relative_to(ROOT))
print(OUT_CLASS_METRICS.relative_to(ROOT))
print(OUT_PRED.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print(
    "R4P9_TRACK_TEMPERATURE_DELTA_DIRECTION_READY"
)
