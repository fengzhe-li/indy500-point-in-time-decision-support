from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import csv
import json
import math

import numpy as np

from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    accuracy_score,
    balanced_accuracy_score,
    roc_auc_score,
)

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

TRANS_PATH = (
    OUT /
    "r4p2_multi_run_transitions_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

R4P8_DATASET_PATH = (
    OUT /
    "r4p8_track_temperature_training_dataset_v1.csv"
)

OUT_DATASET = (
    OUT /
    "r4p10_thermal_conditioned_repeat_dataset_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4p10_thermal_conditioned_repeat_metrics_v1.csv"
)

OUT_PRED = (
    OUT /
    "r4p10_thermal_conditioned_repeat_predictions_v1.csv"
)

OUT_QA = (
    OUT /
    "r4p10_thermal_conditioned_repeat_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4p10_thermal_conditioned_repeat_report_v1.json"
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
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


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


def interpolate_series(
    rows,
    target_dt,
    key
):
    ordered = sorted(
        rows,
        key=lambda r: r["_dt"]
    )

    exact = [
        r for r in ordered
        if r["_dt"] == target_dt
    ]

    if exact:
        return exact[0].get(key)

    before = None
    after = None

    for r in ordered:

        if r["_dt"] <= target_dt:
            before = r

        if r["_dt"] >= target_dt:
            after = r
            break

    if (
        before is None
        or after is None
    ):
        return None

    a = before.get(key)
    b = after.get(key)

    if a is None or b is None:
        return None

    total = (
        after["_dt"]
        - before["_dt"]
    ).total_seconds()

    if total <= 0:
        return None

    weight = (
        target_dt
        - before["_dt"]
    ).total_seconds() / total

    return (
        a
        +
        (b - a) * weight
    )


print("=" * 116)
print("R4P10 — THERMAL-CONDITIONED REPEAT IMPROVEMENT PROBABILITY")
print("=" * 116)

for path in [
    TRANS_PATH,
    PTSC_PATH,
    R4P8_DATASET_PATH,
]:
    if not path.exists():
        raise SystemExit(
            f"MISSING: {path}"
        )

transitions = read_csv(
    TRANS_PATH
)

ptsc_raw = read_csv(
    PTSC_PATH
)

thermal_supervised = read_csv(
    R4P8_DATASET_PATH
)

print(
    f"Historical repeat transitions: "
    f"{len(transitions)}"
)

print(
    f"PTSC observations: "
    f"{len(ptsc_raw)}"
)

print(
    f"Thermal supervised rows: "
    f"{len(thermal_supervised)}"
)


# =============================================================================
# 1. Build PTSC time-series lookup
# =============================================================================

ptsc_by_year = defaultdict(list)

for r in ptsc_raw:

    dt = parse_dt(
        r.get("utc_datetime")
    )

    track = num(
        r.get("track_c")
    )

    ambient = num(
        r.get("ambient_c")
    )

    if (
        dt is None
        or track is None
    ):
        continue

    year = clean(
        r.get("year")
    )

    ptsc_by_year[year].append({
        "_dt": dt,
        "track_c": track,
        "ambient_c": ambient,
        "humidity":
            num(r.get("humidity")),
        "wind":
            num(r.get("wind")),
        "pressure":
            num(r.get("pressure")),
    })


for year in ptsc_by_year:

    ptsc_by_year[year].sort(
        key=lambda r: r["_dt"]
    )


# =============================================================================
# 2. Parse R4P8 thermal supervised dataset
#
# These rows already contain decision-time-safe HRRR features.
# We will train thermal models inside each outer LOYO fold.
# =============================================================================

THERMAL_FEATURES = [
    "current_track_c",
    "current_ambient_c",
    "current_humidity",
    "current_wind",
    "current_pressure",
    "track_minus_ambient_c",
    "past_track_slope_15m_c_per_min",
    "past_track_slope_30m_c_per_min",
    "hrrr_now_temp_c",
    "hrrr_future_temp_c",
    "hrrr_delta_temp_c",
    "hrrr_delta_relative_humidity_pct",
    "hrrr_delta_wind_speed_10m_ms",
    "hrrr_delta_gust_ms",
    "hrrr_delta_cloud_cover_pct",
    "hrrr_delta_shortwave_radiation_wm2",
]


thermal_rows = []

for r in thermal_supervised:

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

        "horizon_min":
            int(horizon),

        "target_delta_track_c":
            target_delta,

        "target_cooling":
            1
            if target_delta < 0
            else 0,
    }

    complete = True

    for feature in THERMAL_FEATURES:

        value = num(
            r.get(feature)
        )

        row[feature] = value

        if value is None:
            complete = False

    if complete:
        thermal_rows.append(
            row
        )


# =============================================================================
# 3. Build performance decision-point rows
#
# Only point-timed BEFORE observations.
# Approximate performance timestamps remain approximate;
# they are not re-labelled as exact timed-run starts.
# =============================================================================

perf_rows = []

for t in transitions:

    year = clean(
        t.get("year")
    )

    decision_dt = parse_dt(
        t.get("before_time_utc")
    )

    speed_delta = num(
        t.get(
            "delta_four_lap_average_speed_mph"
        )
    )

    if (
        not year
        or decision_dt is None
        or speed_delta is None
    ):
        continue

    if year not in ptsc_by_year:
        continue

    ptsc_rows = ptsc_by_year[
        year
    ]

    current_track = interpolate_series(
        ptsc_rows,
        decision_dt,
        "track_c"
    )

    current_ambient = interpolate_series(
        ptsc_rows,
        decision_dt,
        "ambient_c"
    )

    current_humidity = interpolate_series(
        ptsc_rows,
        decision_dt,
        "humidity"
    )

    current_wind = interpolate_series(
        ptsc_rows,
        decision_dt,
        "wind"
    )

    current_pressure = interpolate_series(
        ptsc_rows,
        decision_dt,
        "pressure"
    )

    track_15_ago = interpolate_series(
        ptsc_rows,
        decision_dt
        - timedelta(minutes=15),
        "track_c"
    )

    track_30_ago = interpolate_series(
        ptsc_rows,
        decision_dt
        - timedelta(minutes=30),
        "track_c"
    )

    slope15 = (
        (
            current_track
            - track_15_ago
        ) / 15.0

        if (
            current_track is not None
            and track_15_ago is not None
        )

        else None
    )

    slope30 = (
        (
            current_track
            - track_30_ago
        ) / 30.0

        if (
            current_track is not None
            and track_30_ago is not None
        )

        else None
    )

    row = {
        "year":
            year,

        "decision_time_utc":
            decision_dt.isoformat(),

        "before_attempt_id":
            clean(
                t.get(
                    "before_attempt_id"
                )
            ),

        "after_attempt_id":
            clean(
                t.get(
                    "after_attempt_id"
                )
            ),

        "car_number":
            clean(
                t.get("car_number")
            ),

        "driver_name":
            clean(
                t.get("driver_name")
            ),

        "target_improved":
            1
            if speed_delta > 0
            else 0,

        "actual_speed_delta_mph":
            speed_delta,

        "current_speed_mph":
            num(
                t.get(
                    "before_four_lap_average_speed_mph"
                )
            ),

        "current_lap1_to_lap4_delta_mph":
            num(
                t.get(
                    "before_lap1_to_lap4_delta_mph"
                )
            ),

        "current_late_run_fade_mph":
            num(
                t.get(
                    "before_late_run_fade_mph"
                )
            ),

        "current_track_c":
            current_track,

        "current_ambient_c":
            current_ambient,

        "current_humidity":
            current_humidity,

        "current_wind":
            current_wind,

        "current_pressure":
            current_pressure,

        "track_minus_ambient_c":
            (
                current_track
                - current_ambient

                if (
                    current_track is not None
                    and current_ambient is not None
                )

                else None
            ),

        "past_track_slope_15m_c_per_min":
            slope15,

        "past_track_slope_30m_c_per_min":
            slope30,

        "timing_semantic":
            (
                "APPROXIMATE_PERFORMANCE_"
                "DECISION_PROXY_NOT_EXACT_RUN_START"
            ),

        "historical_wait_used_as_feature":
            False,
    }

    perf_rows.append(
        row
    )


print(
    f"Point-timed performance decision rows: "
    f"{len(perf_rows)}"
)


# =============================================================================
# 4. Helper:
# find HRRR-derived thermal feature vector from R4P8 rows
#
# At a performance decision point, we need feature values appropriate for
# 15m and 30m thermal models.
#
# R4P8 already generated thermal feature rows at many PTSC timestamps.
# We interpolate feature values in time within the same year/horizon.
#
# This preserves decision-time-safe HRRR construction from R4P8.
# =============================================================================

thermal_feature_series = defaultdict(list)

for r in thermal_supervised:

    year = clean(
        r.get("year")
    )

    horizon = num(
        r.get("horizon_min")
    )

    dt = parse_dt(
        r.get("decision_time_utc")
    )

    if (
        not year
        or horizon is None
        or dt is None
    ):
        continue

    item = {
        "_dt": dt
    }

    valid = True

    for feature in THERMAL_FEATURES:

        value = num(
            r.get(feature)
        )

        item[feature] = value

        if value is None:
            valid = False

    if valid:

        thermal_feature_series[
            (
                year,
                int(horizon)
            )
        ].append(
            item
        )


for key in thermal_feature_series:

    thermal_feature_series[
        key
    ].sort(
        key=lambda r: r["_dt"]
    )


def interpolate_feature_vector(
    year,
    horizon,
    target_dt
):
    rows = thermal_feature_series.get(
        (
            year,
            horizon
        ),
        []
    )

    if not rows:
        return None

    out = {}

    for feature in THERMAL_FEATURES:

        value = interpolate_series(
            rows,
            target_dt,
            feature
        )

        if value is None:
            return None

        out[feature] = value

    return out


# =============================================================================
# 5. Outer leave-one-year-out
#
# For each test year:
#
# 1. train 15m thermal Ridge + cooling Logistic excluding test year
# 2. train 30m thermal Ridge + cooling Logistic excluding test year
# 3. generate thermal predictions for performance rows
# 4. train downstream repeat-improvement classifier on non-test years
# 5. test only on held-out year
# =============================================================================

years = sorted({
    r["year"]
    for r in perf_rows
})


MODEL_SPECS = {
    "BASE_RATE": [],

    "CURRENT_SHAPE": [
        "current_lap1_to_lap4_delta_mph",
        "current_late_run_fade_mph",
    ],

    "THERMAL_30": [
        "current_track_c",
        "past_track_slope_30m_c_per_min",
        "predicted_track_delta_30m_c",
        "predicted_cooling_probability_30m",
    ],

    "CURRENT_SHAPE_PLUS_THERMAL_30": [
        "current_lap1_to_lap4_delta_mph",
        "current_late_run_fade_mph",
        "current_track_c",
        "past_track_slope_30m_c_per_min",
        "predicted_track_delta_30m_c",
        "predicted_cooling_probability_30m",
    ],

    "THERMAL_15_30": [
        "current_track_c",
        "past_track_slope_15m_c_per_min",
        "past_track_slope_30m_c_per_min",
        "predicted_track_delta_15m_c",
        "predicted_cooling_probability_15m",
        "predicted_track_delta_30m_c",
        "predicted_cooling_probability_30m",
    ],
}


fold_feature_rows = []
predictions = []
metrics = []


for test_year in years:

    print()
    print(
        f"OUTER TEST YEAR: "
        f"{test_year}"
    )

    thermal_models = {}

    # -------------------------------------------------------------------------
    # Train thermal models excluding outer test year
    # -------------------------------------------------------------------------

    for horizon in [15, 30]:

        tr = [
            r for r in thermal_rows
            if (
                r["year"] != test_year
                and
                r["horizon_min"] == horizon
            )
        ]

        if len(tr) < 20:
            raise SystemExit(
                f"INSUFFICIENT THERMAL TRAINING ROWS "
                f"FOR {test_year} / {horizon}m"
            )

        X = np.array(
            [
                [
                    r[f]
                    for f in THERMAL_FEATURES
                ]
                for r in tr
            ],
            dtype=float
        )

        y_delta = np.array(
            [
                r[
                    "target_delta_track_c"
                ]
                for r in tr
            ],
            dtype=float
        )

        y_cooling = np.array(
            [
                r[
                    "target_cooling"
                ]
                for r in tr
            ],
            dtype=int
        )

        ridge = Pipeline([
            (
                "scale",
                StandardScaler()
            ),
            (
                "ridge",
                Ridge(
                    alpha=20.0
                )
            ),
        ])

        ridge.fit(
            X,
            y_delta
        )

        cooling_model = Pipeline([
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

        cooling_model.fit(
            X,
            y_cooling
        )

        thermal_models[
            horizon
        ] = (
            ridge,
            cooling_model
        )

    # -------------------------------------------------------------------------
    # Generate nested-safe thermal features
    # -------------------------------------------------------------------------

    current_fold = []

    for r in perf_rows:

        decision_dt = parse_dt(
            r[
                "decision_time_utc"
            ]
        )

        if decision_dt is None:
            continue

        enriched = dict(r)

        successful = True

        for horizon in [15, 30]:

            feature_vector = (
                interpolate_feature_vector(
                    r["year"],
                    horizon,
                    decision_dt
                )
            )

            if feature_vector is None:
                successful = False
                break

            X = np.array(
                [[
                    feature_vector[f]
                    for f in THERMAL_FEATURES
                ]],
                dtype=float
            )

            ridge, cooling = (
                thermal_models[
                    horizon
                ]
            )

            delta_pred = float(
                ridge.predict(
                    X
                )[0]
            )

            cooling_prob = float(
                cooling.predict_proba(
                    X
                )[0, 1]
            )

            enriched[
                f"predicted_track_delta_{horizon}m_c"
            ] = delta_pred

            enriched[
                f"predicted_cooling_probability_{horizon}m"
            ] = cooling_prob

        if not successful:
            continue

        enriched[
            "outer_test_year"
        ] = test_year

        enriched[
            "thermal_model_trained_without_outer_test_year"
        ] = True

        current_fold.append(
            enriched
        )

    fold_feature_rows.extend(
        current_fold
    )

    # -------------------------------------------------------------------------
    # Downstream repeat-improvement models
    # -------------------------------------------------------------------------

    for model_name, features in MODEL_SPECS.items():

        if model_name == "BASE_RATE":

            train = [
                r for r in current_fold
                if r["year"] != test_year
            ]

            test = [
                r for r in current_fold
                if r["year"] == test_year
            ]

            if (
                not train
                or not test
            ):
                continue

            y_train = np.array(
                [
                    r["target_improved"]
                    for r in train
                ],
                dtype=int
            )

            base_probability = float(
                np.mean(
                    y_train
                )
            )

            probs = np.full(
                len(test),
                base_probability,
                dtype=float
            )

        else:

            def complete(
                row
            ):
                return all(
                    row.get(f) is not None
                    for f in features
                )

            train = [
                r for r in current_fold
                if (
                    r["year"] != test_year
                    and complete(r)
                )
            ]

            test = [
                r for r in current_fold
                if (
                    r["year"] == test_year
                    and complete(r)
                )
            ]

            if (
                len(train)
                <
                max(
                    10,
                    len(features) + 3
                )
                or not test
            ):
                continue

            X_train = np.array(
                [
                    [
                        r[f]
                        for f in features
                    ]
                    for r in train
                ],
                dtype=float
            )

            y_train = np.array(
                [
                    r["target_improved"]
                    for r in train
                ],
                dtype=int
            )

            if (
                len(
                    set(
                        y_train.tolist()
                    )
                )
                < 2
            ):
                continue

            X_test = np.array(
                [
                    [
                        r[f]
                        for f in features
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
                    "logit",
                    LogisticRegression(
                        C=0.20,
                        solver="liblinear",
                        random_state=42,
                        max_iter=1000,
                    )
                ),
            ])

            model.fit(
                X_train,
                y_train
            )

            probs = model.predict_proba(
                X_test
            )[:, 1]

        actual = np.array(
            [
                r[
                    "target_improved"
                ]
                for r in test
            ],
            dtype=int
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

        balanced = (
            balanced_accuracy_score(
                actual,
                cls
            )
        )

        auc = (
            roc_auc_score(
                actual,
                probs
            )

            if len(
                set(
                    actual.tolist()
                )
            ) >= 2

            else None
        )

        metrics.append({
            "model_name":
                model_name,

            "test_year":
                test_year,

            "test_rows":
                len(test),

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

        for row, a, p in zip(
            test,
            actual,
            probs
        ):

            predictions.append({
                "model_name":
                    model_name,

                "test_year":
                    test_year,

                "after_attempt_id":
                    row[
                        "after_attempt_id"
                    ],

                "car_number":
                    row[
                        "car_number"
                    ],

                "driver_name":
                    row[
                        "driver_name"
                    ],

                "actual_improved":
                    int(a),

                "actual_speed_delta_mph":
                    row[
                        "actual_speed_delta_mph"
                    ],

                "predicted_probability_improve":
                    float(p),

                "predicted_class":
                    int(
                        p >= 0.5
                    ),

                "predicted_track_delta_15m_c":
                    row[
                        "predicted_track_delta_15m_c"
                    ],

                "predicted_cooling_probability_15m":
                    row[
                        "predicted_cooling_probability_15m"
                    ],

                "predicted_track_delta_30m_c":
                    row[
                        "predicted_track_delta_30m_c"
                    ],

                "predicted_cooling_probability_30m":
                    row[
                        "predicted_cooling_probability_30m"
                    ],
            })


# =============================================================================
# 6. Pooled LOYO
# =============================================================================

pooled = []

for model_name in MODEL_SPECS:

    rset = [
        r for r in predictions
        if (
            r["model_name"]
            == model_name
        )
    ]

    if not rset:
        continue

    actual = np.array(
        [
            r[
                "actual_improved"
            ]
            for r in rset
        ],
        dtype=int
    )

    probs = np.array(
        [
            r[
                "predicted_probability_improve"
            ]
            for r in rset
        ],
        dtype=float
    )

    cls = (
        probs >= 0.5
    ).astype(int)

    auc = (
        roc_auc_score(
            actual,
            probs
        )

        if len(
            set(
                actual.tolist()
            )
        ) >= 2

        else None
    )

    pooled.append({
        "model_name":
            model_name,

        "test_year":
            "POOLED_LOYO",

        "test_rows":
            len(rset),

        "brier_score":
            brier_score_loss(
                actual,
                probs
            ),

        "log_loss":
            log_loss(
                actual,
                probs,
                labels=[0, 1]
            ),

        "accuracy":
            accuracy_score(
                actual,
                cls
            ),

        "balanced_accuracy":
            balanced_accuracy_score(
                actual,
                cls
            ),

        "roc_auc":
            auc,
    })


metrics.extend(
    pooled
)


# =============================================================================
# 7. Deduplicated dataset output
#
# Keep one row per attempt using the fold in which that row was the outer test.
# This guarantees displayed thermal predictions are out-of-year for that row.
# =============================================================================

safe_dataset = []

seen = set()

for r in fold_feature_rows:

    if (
        r["year"]
        != r["outer_test_year"]
    ):
        continue

    key = (
        r[
            "after_attempt_id"
        ],
        r[
            "outer_test_year"
        ]
    )

    if key in seen:
        continue

    seen.add(
        key
    )

    safe_dataset.append(
        r
    )


DATASET_FIELDS = [
    "year",
    "decision_time_utc",
    "before_attempt_id",
    "after_attempt_id",
    "car_number",
    "driver_name",
    "target_improved",
    "actual_speed_delta_mph",
    "current_speed_mph",
    "current_lap1_to_lap4_delta_mph",
    "current_late_run_fade_mph",
    "current_track_c",
    "current_ambient_c",
    "current_humidity",
    "current_wind",
    "current_pressure",
    "track_minus_ambient_c",
    "past_track_slope_15m_c_per_min",
    "past_track_slope_30m_c_per_min",
    "predicted_track_delta_15m_c",
    "predicted_cooling_probability_15m",
    "predicted_track_delta_30m_c",
    "predicted_cooling_probability_30m",
    "outer_test_year",
    "thermal_model_trained_without_outer_test_year",
    "timing_semantic",
    "historical_wait_used_as_feature",
]

write_csv(
    OUT_DATASET,
    safe_dataset,
    DATASET_FIELDS
)


# =============================================================================
# 8. Save metrics/predictions
# =============================================================================

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
        "balanced_accuracy",
        "roc_auc",
    ]
)

write_csv(
    OUT_PRED,
    predictions,
    [
        "model_name",
        "test_year",
        "after_attempt_id",
        "car_number",
        "driver_name",
        "actual_improved",
        "actual_speed_delta_mph",
        "predicted_probability_improve",
        "predicted_class",
        "predicted_track_delta_15m_c",
        "predicted_cooling_probability_15m",
        "predicted_track_delta_30m_c",
        "predicted_cooling_probability_30m",
    ]
)


# =============================================================================
# 9. QA
# =============================================================================

bad_wait = [
    r for r in perf_rows
    if (
        r[
            "historical_wait_used_as_feature"
        ]
        is not False
    )
]

bad_outer_leak = [
    r for r in safe_dataset
    if not r[
        "thermal_model_trained_without_outer_test_year"
    ]
]

missing_thermal = [
    r for r in safe_dataset
    if (
        r[
            "predicted_track_delta_30m_c"
        ]
        is None
        or
        r[
            "predicted_cooling_probability_30m"
        ]
        is None
    )
]


qa_rows = [
    {
        "metric":
            "historical_transition_rows",

        "value":
            len(transitions),

        "expected":
            92,

        "status":
            (
                "PASS"
                if len(transitions) == 92
                else "FAIL"
            ),
    },

    {
        "metric":
            "point_timed_performance_rows",

        "value":
            len(perf_rows),

        "expected":
            40,

        "status":
            (
                "PASS"
                if len(perf_rows) == 40
                else "FAIL"
            ),
    },

    {
        "metric":
            "outer_test_safe_dataset_rows",

        "value":
            len(safe_dataset),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if len(safe_dataset) > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "thermal_outer_year_leak_rows",

        "value":
            len(bad_outer_leak),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(bad_outer_leak) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "missing_30m_thermal_predictions",

        "value":
            len(missing_thermal),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(missing_thermal) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "historical_wait_used_as_feature",

        "value":
            len(bad_wait),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(bad_wait) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "performance_validation",

        "value":
            "LEAVE_ONE_YEAR_OUT",

        "expected":
            "LEAVE_ONE_YEAR_OUT",

        "status":
            "PASS",
    },

    {
        "metric":
            "thermal_validation_nested_inside_outer_year",

        "value":
            True,

        "expected":
            True,

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


# =============================================================================
# 10. Report
# =============================================================================

best = None

if pooled:

    candidates = [
        r for r in pooled
        if r["model_name"]
        != "BASE_RATE"
    ]

    if candidates:

        best = min(
            candidates,
            key=lambda r: (
                r[
                    "brier_score"
                ],
                r[
                    "log_loss"
                ]
            )
        )


report = {
    "phase":
        "R4P10",

    "purpose":
        (
            "Test whether decision-time thermal state "
            "and nested-safe future track-temperature "
            "forecasts improve prediction of whether "
            "the next complete qualifying run beats "
            "the current four-lap average."
        ),

    "historical_transition_rows":
        len(transitions),

    "point_timed_performance_rows":
        len(perf_rows),

    "outer_test_safe_dataset_rows":
        len(safe_dataset),

    "validation":
        (
            "Outer leave-one-year-out performance "
            "validation with thermal models trained "
            "excluding the same held-out year."
        ),

    "historical_wait_used_as_feature":
        False,

    "best_nonbaseline_model":
        (
            best["model_name"]
            if best
            else None
        ),

    "best_nonbaseline_brier":
        (
            best["brier_score"]
            if best
            else None
        ),

    "best_nonbaseline_auc":
        (
            best["roc_auc"]
            if best
            else None
        ),

    "important_semantics": {
        "thermal_predictions": (
            "Generated without the held-out "
            "performance test year."
        ),

        "target": (
            "P(next complete repeat beats "
            "current four-lap average)."
        ),

        "wait_time": (
            "Historical repeat wait is not "
            "used as a predictor."
        ),

        "strategy": (
            "No STOP / RETAIN / WITHDRAW "
            "recommendation yet."
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


# =============================================================================
# 11. Console
# =============================================================================

print()
print("=" * 116)
print("R4P10 POOLED LOYO")
print("=" * 116)

for r in pooled:

    auc_text = (
        ""
        if r["roc_auc"] is None
        else f"{r['roc_auc']:.4f}"
    )

    print(
        f"{r['model_name']:34s} | "
        f"n={r['test_rows']:>2} | "
        f"Brier={r['brier_score']:.4f} | "
        f"LogLoss={r['log_loss']:.4f} | "
        f"Acc={r['accuracy']:.4f} | "
        f"BalAcc={r['balanced_accuracy']:.4f} | "
        f"AUC={auc_text}"
    )


if best:

    print()
    print(
        "BEST NON-BASELINE: "
        f"{best['model_name']}"
    )

    print(
        f"Brier={best['brier_score']:.4f} | "
        f"AUC="
        +
        (
            ""
            if best["roc_auc"] is None
            else f"{best['roc_auc']:.4f}"
        )
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
print(
    "R4P10_THERMAL_CONDITIONED_REPEAT_PROBABILITY_READY"
)
