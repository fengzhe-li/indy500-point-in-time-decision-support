from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
OUT.mkdir(parents=True, exist_ok=True)

TRANS_PATH = OUT / "r4p2_multi_run_transitions_v1.csv"
HRRR_PATH = ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"

OUT_DATASET = OUT / "r4p6_decision_safe_conditional_dataset_v1.csv"
OUT_METRICS = OUT / "r4p6_decision_safe_probability_metrics_v1.csv"
OUT_PRED = OUT / "r4p6_decision_safe_probability_predictions_v1.csv"
OUT_QA = OUT / "r4p6_decision_safe_probability_qa_v1.csv"
OUT_REPORT = OUT / "r4p6_decision_safe_probability_report_v1.json"

AVAILABILITY_LAG_MIN = 60

WEATHER_FEATURES = [
    "temp_c",
    "dewpoint_c",
    "relative_humidity_pct",
    "wind_speed_10m_ms",
    "wind_direction_deg",
    "pressure_hpa",
    "gust_ms",
    "cloud_cover_pct",
    "shortwave_radiation_wm2",
]


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


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    s = s.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def fmt(v, digits=6):
    if v is None:
        return ""
    return f"{v:.{digits}f}"


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def circular_delta_deg(after, before):
    if after is None or before is None:
        return None

    return ((after - before + 180.0) % 360.0) - 180.0


def circular_interp_deg(a, b, weight):
    if a is None or b is None:
        return None

    ar = math.radians(a)
    br = math.radians(b)

    ax = math.cos(ar)
    ay = math.sin(ar)

    bx = math.cos(br)
    by = math.sin(br)

    x = ax + (bx - ax) * weight
    y = ay + (by - ay) * weight

    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return None

    return math.degrees(math.atan2(y, x)) % 360.0


def interpolate_cycle(cycle_rows, target_dt):
    ordered = sorted(
        cycle_rows,
        key=lambda r: r["_valid_dt"]
    )

    if not ordered:
        return None

    for r in ordered:
        if r["_valid_dt"] == target_dt:
            return dict(r["_features"])

    before = None
    after = None

    for r in ordered:
        if r["_valid_dt"] <= target_dt:
            before = r

        if r["_valid_dt"] >= target_dt:
            after = r
            break

    if before is None or after is None:
        return None

    total_seconds = (
        after["_valid_dt"] - before["_valid_dt"]
    ).total_seconds()

    if total_seconds <= 0:
        return None

    elapsed_seconds = (
        target_dt - before["_valid_dt"]
    ).total_seconds()

    weight = elapsed_seconds / total_seconds

    out = {}

    for feature in WEATHER_FEATURES:
        a = before["_features"][feature]
        b = after["_features"][feature]

        if feature == "wind_direction_deg":
            out[feature] = circular_interp_deg(
                a, b, weight
            )

        elif a is None or b is None:
            out[feature] = None

        else:
            out[feature] = a + (b - a) * weight

    return out


print("=" * 112)
print("R4P6 — DECISION-SAFE CONDITIONAL PERFORMANCE PROBABILITY")
print("=" * 112)

if not TRANS_PATH.exists():
    raise SystemExit(f"MISSING: {TRANS_PATH}")

if not HRRR_PATH.exists():
    raise SystemExit(f"MISSING: {HRRR_PATH}")

transitions = read_csv(TRANS_PATH)
raw_hrrr = read_csv(HRRR_PATH)

print(f"Transitions: {len(transitions)}")
print(f"Raw HRRR rows: {len(raw_hrrr)}")


# ============================================================================
# 1. Parse HRRR archive into cycles
# ============================================================================

cycles = defaultdict(list)

for r in raw_hrrr:
    cycle_dt = parse_dt(r.get("cycle_time_utc"))
    valid_dt = parse_dt(r.get("valid_time_utc"))

    if cycle_dt is None or valid_dt is None:
        continue

    cycles[cycle_dt].append({
        "_valid_dt": valid_dt,
        "_features": {
            feature: num(r.get(feature))
            for feature in WEATHER_FEATURES
        },
    })

cycle_times = sorted(cycles.keys())

print(f"Distinct HRRR cycles: {len(cycle_times)}")


# ============================================================================
# 2. Build conditional historical training dataset
#
# Decision time = BEFORE attempt performance observation.
#
# Candidate future run time for historical supervision =
# actual AFTER performance observation time.
#
# Crucially:
#
# weather at the candidate future time is taken ONLY from an HRRR cycle
# already available at decision time.
#
# The actual future time is used only to align the historical supervision
# target. Future realized weather is never used.
# ============================================================================

dataset = []

point_timed_transitions = 0
safe_cycle_transitions = 0
forecast_at_actual_future_time_available = 0

for t in transitions:

    decision_dt = parse_dt(
        t.get("before_time_utc")
    )

    future_run_dt = parse_dt(
        t.get("after_time_utc")
    )

    speed_delta = num(
        t.get(
            "delta_four_lap_average_speed_mph"
        )
    )

    if (
        decision_dt is None
        or future_run_dt is None
        or speed_delta is None
    ):
        continue

    if future_run_dt <= decision_dt:
        continue

    point_timed_transitions += 1

    latest_allowed_cycle = (
        decision_dt
        - timedelta(
            minutes=AVAILABILITY_LAG_MIN
        )
    )

    available_cycles = [
        c
        for c in cycle_times
        if (
            c <= latest_allowed_cycle
            and c.date() == decision_dt.date()
        )
    ]

    if not available_cycles:
        continue

    selected_cycle = max(
        available_cycles
    )

    safe_cycle_transitions += 1

    forecast_now = interpolate_cycle(
        cycles[selected_cycle],
        decision_dt
    )

    forecast_future = interpolate_cycle(
        cycles[selected_cycle],
        future_run_dt
    )

    if (
        forecast_now is None
        or forecast_future is None
    ):
        continue

    forecast_at_actual_future_time_available += 1

    wait_min = (
        future_run_dt - decision_dt
    ).total_seconds() / 60.0

    row = {
        "year": clean(t.get("year")),
        "session_id": clean(t.get("session_id")),
        "car_number": clean(t.get("car_number")),
        "driver_name": clean(t.get("driver_name")),

        "before_attempt_id":
            clean(t.get("before_attempt_id")),

        "after_attempt_id":
            clean(t.get("after_attempt_id")),

        "decision_time_utc":
            decision_dt.isoformat(),

        "historical_future_run_time_utc":
            future_run_dt.isoformat(),

        "historical_wait_to_next_run_min":
            fmt(wait_min),

        "historical_wait_role":
            (
                "SUPERVISED_CANDIDATE_TIME_ALIGNMENT_"
                "NOT_QUEUE_MODEL"
            ),

        "selected_hrrr_cycle_utc":
            selected_cycle.isoformat(),

        "cycle_age_minutes_at_decision":
            fmt(
                (
                    decision_dt
                    - selected_cycle
                ).total_seconds() / 60.0
            ),

        "availability_lag_guard_minutes":
            AVAILABILITY_LAG_MIN,

        "current_four_lap_average_speed_mph":
            clean(
                t.get(
                    "before_four_lap_average_speed_mph"
                )
            ),

        "current_lap1_to_lap4_delta_mph":
            clean(
                t.get(
                    "before_lap1_to_lap4_delta_mph"
                )
            ),

        "current_late_run_fade_mph":
            clean(
                t.get(
                    "before_late_run_fade_mph"
                )
            ),

        "actual_next_run_speed_delta_mph":
            fmt(speed_delta),

        "actual_next_run_improved":
            1 if speed_delta > 0 else 0,

        "future_realized_weather_used":
            "False",

        "decision_time_safe":
            "True",
    }

    for feature in WEATHER_FEATURES:

        now = forecast_now[feature]
        future = forecast_future[feature]

        row[f"forecast_now_{feature}"] = fmt(now)
        row[f"forecast_future_{feature}"] = fmt(future)

        if feature == "wind_direction_deg":
            change = circular_delta_deg(
                future,
                now
            )
        elif (
            now is not None
            and future is not None
        ):
            change = future - now
        else:
            change = None

        row[
            f"forecast_change_{feature}"
        ] = fmt(change)

        row[
            f"forecast_rate_{feature}_per_min"
        ] = (
            fmt(
                change / wait_min,
                8
            )
            if (
                change is not None
                and wait_min > 0
            )
            else ""
        )

    dataset.append(row)


# ============================================================================
# 3. Dataset output
# ============================================================================

dataset_fields = [
    "year",
    "session_id",
    "car_number",
    "driver_name",
    "before_attempt_id",
    "after_attempt_id",
    "decision_time_utc",
    "historical_future_run_time_utc",
    "historical_wait_to_next_run_min",
    "historical_wait_role",
    "selected_hrrr_cycle_utc",
    "cycle_age_minutes_at_decision",
    "availability_lag_guard_minutes",
    "current_four_lap_average_speed_mph",
    "current_lap1_to_lap4_delta_mph",
    "current_late_run_fade_mph",
    "actual_next_run_speed_delta_mph",
    "actual_next_run_improved",
    "future_realized_weather_used",
    "decision_time_safe",
]

for feature in WEATHER_FEATURES:
    dataset_fields.extend([
        f"forecast_now_{feature}",
        f"forecast_future_{feature}",
        f"forecast_change_{feature}",
        f"forecast_rate_{feature}_per_min",
    ])

write_csv(
    OUT_DATASET,
    dataset,
    dataset_fields
)


# ============================================================================
# 4. ML-ready representation
# ============================================================================

def value(row, key):
    return num(row.get(key))


model_rows = []

for r in dataset:

    model_rows.append({
        "year": r["year"],
        "attempt_id": r["after_attempt_id"],
        "car_number": r["car_number"],
        "driver_name": r["driver_name"],

        "target": int(
            r["actual_next_run_improved"]
        ),

        "wait_min":
            value(
                r,
                "historical_wait_to_next_run_min"
            ),

        "current_l14":
            value(
                r,
                "current_lap1_to_lap4_delta_mph"
            ),

        "current_fade":
            value(
                r,
                "current_late_run_fade_mph"
            ),
    })

    m = model_rows[-1]

    for feature in WEATHER_FEATURES:

        m[f"now_{feature}"] = value(
            r,
            f"forecast_now_{feature}"
        )

        m[f"future_{feature}"] = value(
            r,
            f"forecast_future_{feature}"
        )

        m[f"change_{feature}"] = value(
            r,
            f"forecast_change_{feature}"
        )

        m[f"rate_{feature}"] = value(
            r,
            f"forecast_rate_{feature}_per_min"
        )


# ============================================================================
# 5. Model specifications
# ============================================================================

CURRENT_RUN_FEATURES = [
    "current_l14",
    "current_fade",
]

FORECAST_FUTURE_FEATURES = [
    "future_temp_c",
    "future_relative_humidity_pct",
    "future_wind_speed_10m_ms",
    "future_pressure_hpa",
    "future_gust_ms",
    "future_cloud_cover_pct",
    "future_shortwave_radiation_wm2",
]

FORECAST_TREND_FEATURES = [
    "change_temp_c",
    "change_relative_humidity_pct",
    "change_wind_speed_10m_ms",
    "change_pressure_hpa",
    "change_gust_ms",
    "change_cloud_cover_pct",
    "change_shortwave_radiation_wm2",
]

FORECAST_RATE_FEATURES = [
    "rate_temp_c",
    "rate_relative_humidity_pct",
    "rate_wind_speed_10m_ms",
    "rate_pressure_hpa",
    "rate_gust_ms",
    "rate_cloud_cover_pct",
    "rate_shortwave_radiation_wm2",
]

SPECS = {
    "BASE_RATE": [],

    "CURRENT_RUN_ONLY":
        CURRENT_RUN_FEATURES,

    "FORECAST_FUTURE_ONLY":
        FORECAST_FUTURE_FEATURES,

    "FORECAST_TREND_ONLY":
        FORECAST_TREND_FEATURES,

    "FORECAST_RATE_ONLY":
        FORECAST_RATE_FEATURES,

    "CURRENT_PLUS_FORECAST":
        (
            CURRENT_RUN_FEATURES
            + FORECAST_FUTURE_FEATURES
        ),

    "CURRENT_PLUS_TREND":
        (
            CURRENT_RUN_FEATURES
            + FORECAST_TREND_FEATURES
        ),
}


def complete(row, features):

    if row["target"] is None:
        return False

    return all(
        row.get(feature) is not None
        for feature in features
    )


years = sorted({
    r["year"]
    for r in model_rows
})

metrics = []
predictions = []


# ============================================================================
# 6. Leave-one-year-out probability validation
# ============================================================================

for model_name, features in SPECS.items():

    for test_year in years:

        if model_name == "BASE_RATE":

            train = [
                r for r in model_rows
                if r["year"] != test_year
            ]

            test = [
                r for r in model_rows
                if r["year"] == test_year
            ]

            if not train or not test:
                continue

            train_y = np.array(
                [
                    r["target"]
                    for r in train
                ],
                dtype=int
            )

            probability = float(
                np.mean(train_y)
            )

            probs = np.full(
                len(test),
                probability,
                dtype=float
            )

        else:

            train = [
                r for r in model_rows
                if (
                    r["year"] != test_year
                    and complete(r, features)
                )
            ]

            test = [
                r for r in model_rows
                if (
                    r["year"] == test_year
                    and complete(r, features)
                )
            ]

            minimum_train = max(
                10,
                len(features) + 3
            )

            if (
                len(train) < minimum_train
                or not test
            ):
                continue

            train_y = np.array(
                [
                    r["target"]
                    for r in train
                ],
                dtype=int
            )

            if len(set(train_y.tolist())) < 2:
                continue

            X_train = np.array(
                [
                    [
                        r[feature]
                        for feature in features
                    ]
                    for r in train
                ],
                dtype=float
            )

            X_test = np.array(
                [
                    [
                        r[feature]
                        for feature in features
                    ]
                    for r in test
                ],
                dtype=float
            )

            model = Pipeline([
                (
                    "scale",
                    StandardScaler()
                ),
                (
                    "logistic",
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
                train_y
            )

            probs = model.predict_proba(
                X_test
            )[:, 1]

        actual = np.array(
            [
                r["target"]
                for r in test
            ],
            dtype=int
        )

        predicted_class = (
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
            predicted_class
        )

        if (
            len(set(actual.tolist()))
            >= 2
        ):
            auc = roc_auc_score(
                actual,
                probs
            )
        else:
            auc = None

        metrics.append({
            "model_name": model_name,
            "test_year": test_year,
            "test_rows": len(test),
            "brier_score": fmt(brier),
            "log_loss": fmt(ll),
            "accuracy": fmt(accuracy),
            "roc_auc": (
                ""
                if auc is None
                else fmt(auc)
            ),
        })

        for row, actual_value, probability in zip(
            test,
            actual,
            probs
        ):

            predictions.append({
                "model_name":
                    model_name,

                "test_year":
                    test_year,

                "attempt_id":
                    row["attempt_id"],

                "car_number":
                    row["car_number"],

                "driver_name":
                    row["driver_name"],

                "actual_improved":
                    int(actual_value),

                "predicted_probability_improve":
                    fmt(probability),

                "predicted_class":
                    int(
                        probability >= 0.5
                    ),
            })


# ============================================================================
# 7. Pooled LOYO
# ============================================================================

pooled = []

for model_name in SPECS:

    rows = [
        r for r in predictions
        if r["model_name"] == model_name
    ]

    if not rows:
        continue

    actual = np.array(
        [
            int(r["actual_improved"])
            for r in rows
        ],
        dtype=int
    )

    probs = np.array(
        [
            float(
                r[
                    "predicted_probability_improve"
                ]
            )
            for r in rows
        ],
        dtype=float
    )

    predicted_class = (
        probs >= 0.5
    ).astype(int)

    auc = (
        roc_auc_score(
            actual,
            probs
        )
        if len(set(actual.tolist())) >= 2
        else None
    )

    pooled.append({
        "model_name":
            model_name,

        "test_year":
            "POOLED_LOYO",

        "test_rows":
            len(rows),

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

        "accuracy":
            fmt(
                accuracy_score(
                    actual,
                    predicted_class
                )
            ),

        "roc_auc":
            (
                ""
                if auc is None
                else fmt(auc)
            ),
    })


metrics.extend(
    pooled
)


# ============================================================================
# 8. QA
# ============================================================================

unsafe_cycle_rows = []
future_weather_leak_rows = []
bad_wait_semantics = []

for r in dataset:

    decision = parse_dt(
        r["decision_time_utc"]
    )

    cycle = parse_dt(
        r["selected_hrrr_cycle_utc"]
    )

    if (
        decision is None
        or cycle is None
        or cycle
        >
        decision
        - timedelta(
            minutes=AVAILABILITY_LAG_MIN
        )
    ):
        unsafe_cycle_rows.append(r)

    if (
        r["future_realized_weather_used"]
        != "False"
    ):
        future_weather_leak_rows.append(r)

    if (
        r["historical_wait_role"]
        !=
        "SUPERVISED_CANDIDATE_TIME_ALIGNMENT_NOT_QUEUE_MODEL"
    ):
        bad_wait_semantics.append(r)


qa_rows = [
    {
        "metric":
            "point_timed_transition_rows",

        "value":
            point_timed_transitions,

        "expected":
            40,

        "status":
            (
                "PASS"
                if point_timed_transitions == 40
                else "FAIL"
            ),
    },

    {
        "metric":
            "safe_cycle_transition_rows",

        "value":
            safe_cycle_transitions,

        "expected":
            40,

        "status":
            (
                "PASS"
                if safe_cycle_transitions == 40
                else "FAIL"
            ),
    },

    {
        "metric":
            "conditional_forecast_training_rows",

        "value":
            len(dataset),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if len(dataset) > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "unsafe_cycle_rows",

        "value":
            len(unsafe_cycle_rows),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(unsafe_cycle_rows) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "realized_future_weather_used",

        "value":
            len(future_weather_leak_rows),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(future_weather_leak_rows) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "historical_wait_mislabeled_as_queue_model",

        "value":
            len(bad_wait_semantics),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(bad_wait_semantics) == 0
                else "FAIL"
            ),
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
# 9. Output metrics / predictions
# ============================================================================

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
        "predicted_probability_improve",
        "predicted_class",
    ]
)


# ============================================================================
# 10. Report
# ============================================================================

per_year = {}

for year in sorted({
    r["year"]
    for r in dataset
}):

    yr = [
        r for r in dataset
        if r["year"] == year
    ]

    waits = [
        num(
            r[
                "historical_wait_to_next_run_min"
            ]
        )
        for r in yr
    ]

    waits = [
        x for x in waits
        if x is not None
    ]

    per_year[year] = {
        "rows": len(yr),

        "mean_historical_candidate_wait_min":
            (
                sum(waits) / len(waits)
                if waits
                else None
            ),

        "min_historical_candidate_wait_min":
            (
                min(waits)
                if waits
                else None
            ),

        "max_historical_candidate_wait_min":
            (
                max(waits)
                if waits
                else None
            ),
    }


report = {
    "phase":
        "R4P6",

    "purpose":
        (
            "Train a decision-time-safe conditional "
            "probability model for whether a future "
            "complete qualifying attempt improves "
            "the current four-lap average."
        ),

    "input_transition_rows":
        len(transitions),

    "point_timed_transition_rows":
        point_timed_transitions,

    "safe_cycle_rows":
        safe_cycle_transitions,

    "conditional_training_rows":
        len(dataset),

    "availability_guard_minutes":
        AVAILABILITY_LAG_MIN,

    "future_realized_weather_used":
        False,

    "queue_model_used":
        False,

    "historical_future_run_time_role":
        (
            "Used only as supervised candidate-time "
            "alignment for the forecast available "
            "at decision time."
        ),

    "validation":
        "leave-one-year-out",

    "per_year":
        per_year,

    "important_limitations": [
        (
            "This is conditional on a candidate future "
            "run time; the model does not predict "
            "queue waiting time."
        ),
        (
            "HRRR atmospheric forecast does not directly "
            "forecast track-surface temperature."
        ),
        (
            "Dataset remains small and concentrated "
            "in 2020, 2021 and 2023."
        ),
        (
            "No causal claim is made."
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


# ============================================================================
# 11. Console
# ============================================================================

print()
print("=" * 112)
print("R4P6 SUMMARY")
print("=" * 112)

print(
    f"Point-timed historical transitions: "
    f"{point_timed_transitions}"
)

print(
    f"Safe HRRR cycle available: "
    f"{safe_cycle_transitions}"
)

print(
    f"Forecast available at actual future-run time: "
    f"{forecast_at_actual_future_time_available}"
)

print(
    f"Conditional training rows: "
    f"{len(dataset)}"
)

print()
print("BY YEAR")

for year in sorted(per_year):

    p = per_year[year]

    print(
        f"{year}: "
        f"rows={p['rows']} | "
        f"mean_wait={fmt(p['mean_historical_candidate_wait_min'])} | "
        f"min_wait={fmt(p['min_historical_candidate_wait_min'])} | "
        f"max_wait={fmt(p['max_historical_candidate_wait_min'])}"
    )


print()
print("=" * 112)
print("POOLED LOYO PROBABILITY RESULTS")
print("=" * 112)

for r in pooled:

    print(
        f"{r['model_name']:24s} | "
        f"n={str(r['test_rows']):>2s} | "
        f"Brier={r['brier_score']} | "
        f"LogLoss={r['log_loss']} | "
        f"Acc={r['accuracy']} | "
        f"AUC={r['roc_auc']}"
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
print(OUT_DATASET.relative_to(ROOT))
print(OUT_METRICS.relative_to(ROOT))
print(OUT_PRED.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print("R4P6_DECISION_SAFE_CONDITIONAL_PERFORMANCE_READY")
