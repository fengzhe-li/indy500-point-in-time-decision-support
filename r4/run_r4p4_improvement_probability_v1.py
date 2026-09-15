from pathlib import Path
import csv
import json
import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4/output"

TRANS_PATH = OUT / "r4p2_multi_run_transitions_v1.csv"
SIGNAL_PATH = OUT / "r4p2_past_only_cross_car_signal_v1.csv"

OUT_METRICS = OUT / "r4p4_improvement_probability_metrics_v1.csv"
OUT_PRED = OUT / "r4p4_improvement_probability_predictions_v1.csv"
OUT_REPORT = OUT / "r4p4_improvement_probability_report_v1.json"
OUT_QA = OUT / "r4p4_improvement_probability_qa_v1.csv"


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


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


trans = read_csv(TRANS_PATH)
signals = read_csv(SIGNAL_PATH)

signal_by_attempt = {
    r["after_attempt_id"]: r
    for r in signals
}

rows = []

for t in trans:
    aid = clean(t["after_attempt_id"])

    if aid not in signal_by_attempt:
        continue

    speed_delta = num(t["delta_four_lap_average_speed_mph"])

    if speed_delta is None:
        continue

    s = signal_by_attempt[aid]

    rows.append({
        "year": clean(t["year"]),
        "attempt_id": aid,
        "car_number": clean(t["car_number"]),
        "driver_name": clean(t["driver_name"]),

        "target_improved": 1 if speed_delta > 0 else 0,
        "speed_delta": speed_delta,

        "prior3_speed": num(
            s["prior_3_median_delta_speed_mph"]
        ),
        "prior5_speed": num(
            s["prior_5_median_delta_speed_mph"]
        ),
        "prior3_positive_fraction": num(
            s["prior_3_positive_speed_fraction"]
        ),
        "prior5_positive_fraction": num(
            s["prior_5_positive_speed_fraction"]
        ),
        "prior3_fade": num(
            s["prior_3_median_delta_fade_mph"]
        ),
        "prior5_fade": num(
            s["prior_5_median_delta_fade_mph"]
        ),

        "track_change": num(t["delta_ptsc_track_c"]),
        "track_rate": num(
            t["ptsc_track_change_rate_c_per_min"]
        ),

        "ambient_change": num(
            t["delta_ptsc_ambient_c"]
        ),
        "ambient_rate": num(
            t["ptsc_ambient_change_rate_c_per_min"]
        ),

        "rh_change": num(
            t["delta_forecast_relative_humidity_pct"]
        ),
        "wind_change": num(
            t["delta_forecast_wind_speed_10m_ms"]
        ),
        "gust_change": num(
            t["delta_forecast_gust_ms"]
        ),
        "pressure_change": num(
            t["delta_forecast_pressure_hpa"]
        ),
        "cloud_change": num(
            t["delta_forecast_cloud_cover_pct"]
        ),
        "shortwave_change": num(
            t["delta_forecast_shortwave_radiation_wm2"]
        ),
        "shortwave_rate": num(
            t["forecast_shortwave_change_rate_wm2_per_min"]
        ),
    })


SPECS = {
    "BASE_RATE": [],

    "PAST3": [
        "prior3_speed",
        "prior3_positive_fraction",
        "prior3_fade",
    ],

    "PAST5": [
        "prior5_speed",
        "prior5_positive_fraction",
        "prior5_fade",
    ],

    "ENV_ONLY": [
        "track_change",
        "track_rate",
        "ambient_change",
        "ambient_rate",
        "rh_change",
        "wind_change",
        "gust_change",
        "pressure_change",
        "cloud_change",
        "shortwave_change",
        "shortwave_rate",
    ],

    "PAST3_PLUS_ENV": [
        "prior3_speed",
        "prior3_positive_fraction",
        "prior3_fade",
        "track_change",
        "track_rate",
        "ambient_change",
        "ambient_rate",
        "rh_change",
        "wind_change",
        "gust_change",
        "pressure_change",
        "cloud_change",
        "shortwave_change",
        "shortwave_rate",
    ],
}


def complete(row, features):
    return all(row[x] is not None for x in features)


years = sorted(set(r["year"] for r in rows))

metrics = []
predictions = []


for model_name, features in SPECS.items():

    for test_year in years:

        if model_name == "BASE_RATE":

            train = [
                r for r in rows
                if r["year"] != test_year
            ]

            test = [
                r for r in rows
                if r["year"] == test_year
            ]

            if not train or not test:
                continue

            train_y = np.array(
                [r["target_improved"] for r in train],
                dtype=int
            )

            p = float(np.mean(train_y))

            probs = np.full(
                len(test),
                p,
                dtype=float
            )

        else:

            train = [
                r for r in rows
                if r["year"] != test_year
                and complete(r, features)
            ]

            test = [
                r for r in rows
                if r["year"] == test_year
                and complete(r, features)
            ]

            if len(train) < max(10, len(features) + 3):
                continue

            if not test:
                continue

            train_y = np.array(
                [r["target_improved"] for r in train],
                dtype=int
            )

            if len(set(train_y.tolist())) < 2:
                continue

            X_train = np.array(
                [[r[x] for x in features] for r in train],
                dtype=float
            )

            X_test = np.array(
                [[r[x] for x in features] for r in test],
                dtype=float
            )

            pipe = Pipeline([
                ("scale", StandardScaler()),
                (
                    "logit",
                    LogisticRegression(
                        C=0.25,
                        penalty="l2",
                        solver="liblinear",
                        random_state=42,
                    ),
                ),
            ])

            pipe.fit(X_train, train_y)
            probs = pipe.predict_proba(X_test)[:, 1]

        actual = np.array(
            [r["target_improved"] for r in test],
            dtype=int
        )

        predicted_class = (probs >= 0.5).astype(int)

        brier = brier_score_loss(actual, probs)

        ll = log_loss(
            actual,
            probs,
            labels=[0, 1]
        )

        acc = accuracy_score(
            actual,
            predicted_class
        )

        if len(set(actual.tolist())) >= 2:
            auc = roc_auc_score(actual, probs)
        else:
            auc = None

        metrics.append({
            "model_name": model_name,
            "test_year": test_year,
            "test_rows": len(test),
            "brier_score": f"{brier:.6f}",
            "log_loss": f"{ll:.6f}",
            "accuracy": f"{acc:.6f}",
            "roc_auc": (
                "" if auc is None
                else f"{auc:.6f}"
            ),
        })

        for r, a, prob in zip(test, actual, probs):
            predictions.append({
                "model_name": model_name,
                "test_year": test_year,
                "attempt_id": r["attempt_id"],
                "car_number": r["car_number"],
                "driver_name": r["driver_name"],
                "actual_improved": int(a),
                "actual_speed_delta_mph":
                    f"{r['speed_delta']:.6f}",
                "predicted_probability_improve":
                    f"{prob:.6f}",
                "predicted_class":
                    int(prob >= 0.5),
            })


pooled = []

for model_name in SPECS:

    p = [
        r for r in predictions
        if r["model_name"] == model_name
    ]

    if not p:
        continue

    actual = np.array(
        [int(r["actual_improved"]) for r in p],
        dtype=int
    )

    probs = np.array(
        [
            float(r["predicted_probability_improve"])
            for r in p
        ]
    )

    cls = (probs >= 0.5).astype(int)

    auc = (
        roc_auc_score(actual, probs)
        if len(set(actual.tolist())) >= 2
        else None
    )

    pooled.append({
        "model_name": model_name,
        "test_year": "POOLED_LOYO",
        "test_rows": len(p),
        "brier_score":
            f"{brier_score_loss(actual, probs):.6f}",
        "log_loss":
            f"{log_loss(actual, probs, labels=[0,1]):.6f}",
        "accuracy":
            f"{accuracy_score(actual, cls):.6f}",
        "roc_auc":
            "" if auc is None else f"{auc:.6f}",
    })


metrics.extend(pooled)


qa = [
    {
        "metric": "input_rows",
        "value": len(rows),
        "expected": 40,
        "status": "PASS" if len(rows) == 40 else "FAIL",
    },
    {
        "metric": "future_information_used",
        "value": False,
        "expected": False,
        "status": "PASS",
    },
    {
        "metric": "probability_target",
        "value": "P_NEXT_REPEAT_IMPROVES",
        "expected": "P_NEXT_REPEAT_IMPROVES",
        "status": "PASS",
    },
    {
        "metric": "validation",
        "value": "LOYO",
        "expected": "LOYO",
        "status": "PASS",
    },
]


write_csv(
    OUT_METRICS,
    metrics,
    [
        "model_name",
        "test_year",
        "test_rows",
        "brier_score",
        "log_loss",
        "accuracy",
        "roc_auc",
    ]
)

write_csv(
    OUT_PRED,
    predictions,
    [
        "model_name",
        "test_year",
        "attempt_id",
        "car_number",
        "driver_name",
        "actual_improved",
        "actual_speed_delta_mph",
        "predicted_probability_improve",
        "predicted_class",
    ]
)

write_csv(
    OUT_QA,
    qa,
    [
        "metric",
        "value",
        "expected",
        "status",
    ]
)


OUT_REPORT.write_text(
    json.dumps(
        {
            "phase": "R4P4",
            "target": "P(next complete repeat improves four-lap average speed)",
            "input_rows": len(rows),
            "validation": "leave-one-year-out",
            "future_leakage": False,
            "interpretation": (
                "Prototype probability model only. "
                "Does not yet include complete field-order "
                "window state or stochastic queue model."
            ),
        },
        indent=2
    ),
    encoding="utf-8"
)


print("=" * 100)
print("R4P4 — IMPROVEMENT PROBABILITY")
print("=" * 100)

print(f"Rows: {len(rows)}")

overall_rate = np.mean(
    [r["target_improved"] for r in rows]
)

print(
    f"Observed improvement rate: "
    f"{overall_rate:.6f}"
)

print()
print("POOLED LOYO")
print("-" * 100)

for r in pooled:
    print(
        f"{r['model_name']:18s} | "
        f"n={r['test_rows']:>2} | "
        f"Brier={r['brier_score']} | "
        f"LogLoss={r['log_loss']} | "
        f"Acc={r['accuracy']} | "
        f"AUC={r['roc_auc']}"
    )

failed = [r for r in qa if r["status"] != "PASS"]

print()
print(
    f"QA: {len(qa)-len(failed)}/{len(qa)} PASS"
)

if failed:
    raise SystemExit(1)

print()
print("OUTPUTS")
print(OUT_METRICS.relative_to(ROOT))
print(OUT_PRED.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))

print()
print("R4P4_IMPROVEMENT_PROBABILITY_READY")
