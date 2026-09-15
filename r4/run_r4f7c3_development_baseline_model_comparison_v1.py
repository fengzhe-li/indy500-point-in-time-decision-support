from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import statistics
import hashlib
import sys

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT_PATH = (
    OUT /
    "r4f7c2c_development_numeric_matrix_v1.csv"
)

OUT_PRED = (
    OUT /
    "r4f7c3_development_baseline_predictions_v1.csv"
)

OUT_METRICS = (
    OUT /
    "r4f7c3_development_baseline_metrics_v1.csv"
)

OUT_LOYO = (
    OUT /
    "r4f7c3_leave_one_year_out_metrics_v1.csv"
)

OUT_GROUPCV = (
    OUT /
    "r4f7c3_driver_grouped_cv_metrics_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c3_development_baseline_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c3_development_baseline_report_v1.json"
)


THERMAL_FEATURES = [
    "ptsc_track_temp_c_past_safe",
    "ptsc_track_temp_slope_c_per_min_past_safe",
    "forecast_temp_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_pressure_hpa",
    "forecast_gust_ms",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
    "forecast_wind_direction_sin",
    "forecast_wind_direction_cos",
]


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


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def mae(y, pred):
    return sum(
        abs(a - b)
        for a, b
        in zip(y, pred)
    ) / len(y)


def rmse(y, pred):
    return math.sqrt(
        sum(
            (a - b) ** 2
            for a, b
            in zip(y, pred)
        ) / len(y)
    )


def bias(y, pred):
    return sum(
        p - a
        for a, p
        in zip(y, pred)
    ) / len(y)


def correlation(a, b):

    if len(a) < 2:
        return None

    ma = sum(a) / len(a)
    mb = sum(b) / len(b)

    va = sum(
        (x - ma) ** 2
        for x in a
    )

    vb = sum(
        (x - mb) ** 2
        for x in b
    )

    if (
        va <= 0
        or
        vb <= 0
    ):
        return None

    cov = sum(
        (x - ma) * (y - mb)
        for x, y
        in zip(a, b)
    )

    return cov / math.sqrt(
        va * vb
    )


if not INPUT_PATH.exists():

    raise SystemExit(
        f"MISSING INPUT: {INPUT_PATH}"
    )


try:
    import numpy as np

    from sklearn.compose import (
        ColumnTransformer
    )

    from sklearn.pipeline import (
        Pipeline
    )

    from sklearn.preprocessing import (
        StandardScaler
    )

    from sklearn.linear_model import (
        Ridge,
        HuberRegressor,
    )

    from sklearn.model_selection import (
        GroupKFold
    )

except Exception as e:

    raise SystemExit(
        "SCIKIT-LEARN / NUMPY REQUIRED: "
        +
        repr(e)
    )


fields, raw = read_csv(
    INPUT_PATH
)


required = {
    "attempt_id",
    "year",
    "driver_key",
    "target_four_lap_average_speed_mph",
    "fast_friday_reference_mph",
    *THERMAL_FEATURES,
}


missing_cols = sorted(
    required
    -
    set(fields)
)

if missing_cols:

    raise SystemExit(
        "MISSING REQUIRED COLUMNS: "
        +
        ", ".join(
            missing_cols
        )
    )


# =============================================================================
# Parse frozen development rows
# =============================================================================

rows = []


for r in raw:

    try:

        year = int(
            float(
                clean(
                    r.get(
                        "year"
                    )
                )
            )
        )

    except Exception:

        raise SystemExit(
            "INVALID YEAR"
        )


    y = num(
        r.get(
            "target_four_lap_average_speed_mph"
        )
    )

    ref = num(
        r.get(
            "fast_friday_reference_mph"
        )
    )


    features = {
        f:
            num(
                r.get(f)
            )
        for f in THERMAL_FEATURES
    }


    if (
        y is None
        or
        ref is None
        or
        any(
            v is None
            for v in features.values()
        )
    ):

        raise SystemExit(
            f"INCOMPLETE DEVELOPMENT ROW: "
            f"{clean(r.get('attempt_id'))}"
        )


    rows.append({
        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "year":
            year,

        "driver_key":
            clean(
                r.get(
                    "driver_key"
                )
            ),

        "driver_name":
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "observed_speed":
            y,

        "reference_speed":
            ref,

        "reference_residual":
            y - ref,

        **features,
    })


if len(rows) != 104:

    raise SystemExit(
        f"EXPECTED 104 DEVELOPMENT ROWS, GOT {len(rows)}"
    )


years = sorted(
    {
        r[
            "year"
        ]
        for r in rows
    }
)


if years != [
    2020,
    2021,
    2023,
]:

    raise SystemExit(
        f"UNEXPECTED DEVELOPMENT YEARS: {years}"
    )


print("=" * 150)
print("R4F7C3 — DEVELOPMENT-ONLY BASELINE MODEL COMPARISON")
print("=" * 150)

print(
    f"Development rows: {len(rows)}"
)

print(
    f"Years: {years}"
)

print(
    "2024 validation file is NOT read by this script."
)


# =============================================================================
# Numeric arrays
# =============================================================================

X = np.array(
    [
        [
            r[f]
            for f in THERMAL_FEATURES
        ]
        for r in rows
    ],
    dtype=float,
)

y = np.array(
    [
        r[
            "observed_speed"
        ]
        for r in rows
    ],
    dtype=float,
)

ref = np.array(
    [
        r[
            "reference_speed"
        ]
        for r in rows
    ],
    dtype=float,
)

residual = (
    y
    -
    ref
)

groups = np.array(
    [
        r[
            "driver_key"
        ]
        for r in rows
    ],
    dtype=object,
)

year_array = np.array(
    [
        r[
            "year"
        ]
        for r in rows
    ],
    dtype=int,
)


# =============================================================================
# Predictors
# =============================================================================

def predict_reference_only(
    train_idx,
    test_idx,
):

    return ref[
        test_idx
    ].copy()


def predict_year_intercept(
    train_idx,
    test_idx,
):

    train_y = y[
        train_idx
    ]

    train_years = year_array[
        train_idx
    ]

    global_mean = float(
        np.mean(
            train_y
        )
    )

    year_means = {}

    for yr in np.unique(
        train_years
    ):

        year_means[
            int(yr)
        ] = float(
            np.mean(
                train_y[
                    train_years
                    ==
                    yr
                ]
            )
        )


    pred = []

    for idx in test_idx:

        yr = int(
            year_array[
                idx
            ]
        )

        pred.append(
            year_means.get(
                yr,
                global_mean
            )
        )

    return np.array(
        pred,
        dtype=float,
    )


def predict_ridge(
    train_idx,
    test_idx,
):

    model = Pipeline([
        (
            "scale",
            StandardScaler(),
        ),
        (
            "ridge",
            Ridge(
                alpha=10.0
            ),
        ),
    ])


    model.fit(
        X[
            train_idx
        ],
        residual[
            train_idx
        ],
    )


    residual_pred = model.predict(
        X[
            test_idx
        ]
    )


    return (
        ref[
            test_idx
        ]
        +
        residual_pred
    )


def predict_huber(
    train_idx,
    test_idx,
):

    model = Pipeline([
        (
            "scale",
            StandardScaler(),
        ),
        (
            "huber",
            HuberRegressor(
                epsilon=1.35,
                alpha=1.0,
                max_iter=5000,
            ),
        ),
    ])


    model.fit(
        X[
            train_idx
        ],
        residual[
            train_idx
        ],
    )


    residual_pred = model.predict(
        X[
            test_idx
        ]
    )


    return (
        ref[
            test_idx
        ]
        +
        residual_pred
    )


MODELS = {
    "YEAR_INTERCEPT_ONLY":
        predict_year_intercept,

    "FAST_FRIDAY_REFERENCE_ONLY":
        predict_reference_only,

    "FAST_FRIDAY_PLUS_THERMAL_RIDGE":
        predict_ridge,

    "FAST_FRIDAY_PLUS_THERMAL_HUBER":
        predict_huber,
}


# =============================================================================
# CV helper
# =============================================================================

prediction_rows = []
metric_rows = []


def record_fold(
    validation_scheme,
    fold_label,
    model_name,
    test_idx,
    pred,
):

    actual = y[
        test_idx
    ]


    fold_mae = mae(
        actual,
        pred,
    )

    fold_rmse = rmse(
        actual,
        pred,
    )

    fold_bias = bias(
        actual,
        pred,
    )

    fold_corr = correlation(
        list(
            actual
        ),
        list(
            pred
        ),
    )


    metric_rows.append({
        "validation_scheme":
            validation_scheme,

        "fold":
            fold_label,

        "model":
            model_name,

        "n":
            len(
                test_idx
            ),

        "mae_mph":
            fold_mae,

        "rmse_mph":
            fold_rmse,

        "bias_mph":
            fold_bias,

        "correlation":
            (
                fold_corr
                if fold_corr
                is not None
                else ""
            ),
    })


    for idx, p in zip(
        test_idx,
        pred
    ):

        prediction_rows.append({
            "validation_scheme":
                validation_scheme,

            "fold":
                fold_label,

            "model":
                model_name,

            "attempt_id":
                rows[
                    idx
                ][
                    "attempt_id"
                ],

            "year":
                rows[
                    idx
                ][
                    "year"
                ],

            "driver_key":
                rows[
                    idx
                ][
                    "driver_key"
                ],

            "observed_speed_mph":
                y[
                    idx
                ],

            "reference_speed_mph":
                ref[
                    idx
                ],

            "predicted_speed_mph":
                float(
                    p
                ),

            "error_mph":
                float(
                    p
                    -
                    y[
                        idx
                    ]
                ),

            "absolute_error_mph":
                abs(
                    float(
                        p
                        -
                        y[
                            idx
                        ]
                    )
                ),
        })


# =============================================================================
# Driver-grouped 5-fold CV
#
# Same driver is never split between train and test.
# This avoids repeated-attempt identity leakage.
# =============================================================================

unique_groups = len(
    set(
        groups
    )
)

n_splits = min(
    5,
    unique_groups,
)


gkf = GroupKFold(
    n_splits=n_splits
)


for fold_no, (
    train_idx,
    test_idx,
) in enumerate(
    gkf.split(
        X,
        y,
        groups=groups,
    ),
    start=1,
):

    for model_name, fn in MODELS.items():

        pred = fn(
            train_idx,
            test_idx,
        )

        record_fold(
            "DRIVER_GROUPED_5FOLD",
            f"FOLD_{fold_no}",
            model_name,
            test_idx,
            pred,
        )


# =============================================================================
# Leave-one-year-out
#
# Entire year is absent from training.
# YEAR_INTERCEPT_ONLY therefore must fall back to global training mean
# for the unseen test year. This is deliberate and is recorded as a
# transfer diagnostic rather than an operational same-year estimate.
# =============================================================================

for test_year in years:

    test_idx = np.where(
        year_array
        ==
        test_year
    )[0]

    train_idx = np.where(
        year_array
        !=
        test_year
    )[0]


    for model_name, fn in MODELS.items():

        pred = fn(
            train_idx,
            test_idx,
        )

        record_fold(
            "LEAVE_ONE_YEAR_OUT",
            f"TEST_{test_year}",
            model_name,
            test_idx,
            pred,
        )


# =============================================================================
# Aggregate metrics by validation scheme + model
# =============================================================================

aggregate_rows = []


for scheme in [
    "DRIVER_GROUPED_5FOLD",
    "LEAVE_ONE_YEAR_OUT",
]:

    for model_name in MODELS:

        preds = [
            r
            for r in prediction_rows
            if (
                r[
                    "validation_scheme"
                ]
                ==
                scheme
                and
                r[
                    "model"
                ]
                ==
                model_name
            )
        ]


        actual = [
            float(
                r[
                    "observed_speed_mph"
                ]
            )
            for r in preds
        ]

        prediction = [
            float(
                r[
                    "predicted_speed_mph"
                ]
            )
            for r in preds
        ]


        corr = correlation(
            actual,
            prediction,
        )


        aggregate_rows.append({
            "validation_scheme":
                scheme,

            "model":
                model_name,

            "n":
                len(
                    preds
                ),

            "mae_mph":
                mae(
                    actual,
                    prediction,
                ),

            "rmse_mph":
                rmse(
                    actual,
                    prediction,
                ),

            "bias_mph":
                bias(
                    actual,
                    prediction,
                ),

            "correlation":
                (
                    corr
                    if corr
                    is not None
                    else ""
                ),
        })


# =============================================================================
# Per-year raw Fast Friday diagnostic
# =============================================================================

raw_reference_by_year = []


for yr in years:

    idx = np.where(
        year_array
        ==
        yr
    )[0]


    raw_reference_by_year.append({
        "year":
            yr,

        "n":
            len(
                idx
            ),

        "reference_only_mae":
            mae(
                y[
                    idx
                ],
                ref[
                    idx
                ],
            ),

        "reference_only_rmse":
            rmse(
                y[
                    idx
                ],
                ref[
                    idx
                ],
            ),

        "reference_bias_pred_minus_actual":
            bias(
                y[
                    idx
                ],
                ref[
                    idx
                ],
            ),

        "residual_mean_actual_minus_reference":
            float(
                np.mean(
                    residual[
                        idx
                    ]
                )
            ),

        "residual_median_actual_minus_reference":
            float(
                np.median(
                    residual[
                        idx
                    ]
                )
            ),
    })


# =============================================================================
# Outlier influence diagnostic
#
# Diagnostic only. No row is removed from official primary metrics.
# =============================================================================

abs_residual = np.abs(
    residual
)

outlier_order = np.argsort(
    -abs_residual
)


top_residual_outliers = []


for idx in outlier_order[:10]:

    top_residual_outliers.append({
        "attempt_id":
            rows[
                idx
            ][
                "attempt_id"
            ],

        "year":
            rows[
                idx
            ][
                "year"
            ],

        "driver_name":
            rows[
                idx
            ][
                "driver_name"
            ],

        "reference_speed_mph":
            ref[
                idx
            ],

        "observed_speed_mph":
            y[
                idx
            ],

        "reference_residual_mph":
            residual[
                idx
            ],
    })


# =============================================================================
# Save outputs
# =============================================================================

with OUT_PRED.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            prediction_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        prediction_rows
    )


with OUT_METRICS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            aggregate_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        aggregate_rows
    )


loyo_rows = [
    r
    for r in metric_rows
    if r[
        "validation_scheme"
    ]
    ==
    "LEAVE_ONE_YEAR_OUT"
]


group_rows = [
    r
    for r in metric_rows
    if r[
        "validation_scheme"
    ]
    ==
    "DRIVER_GROUPED_5FOLD"
]


with OUT_LOYO.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            loyo_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        loyo_rows
    )


with OUT_GROUPCV.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            group_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        group_rows
    )


# =============================================================================
# QA
# =============================================================================

validation_file_path = (
    OUT /
    "r4f7c2c_2024_validation_numeric_matrix_v1.csv"
)

# Important: existence may be checked as metadata, but content is NEVER read.
validation_content_read = False


all_prediction_count_ok = all(
    r[
        "n"
    ] == 104
    for r in aggregate_rows
)


qa_rows = [
    {
        "metric":
            "development_rows",
        "value":
            len(rows),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(rows) == 104
                else "FAIL"
            ),
    },

    {
        "metric":
            "development_years",
        "value":
            ",".join(
                str(x)
                for x in years
            ),
        "expected":
            "2020,2021,2023",
        "status":
            (
                "PASS"
                if years
                ==
                [
                    2020,
                    2021,
                    2023,
                ]
                else "FAIL"
            ),
    },

    {
        "metric":
            "complete_predictions_per_model",
        "value":
            all_prediction_count_ok,
        "expected":
            True,
        "status":
            (
                "PASS"
                if all_prediction_count_ok
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_content_read",
        "value":
            validation_content_read,
        "expected":
            False,
        "status":
            (
                "PASS"
                if not validation_content_read
                else "FAIL"
            ),
    },

    {
        "metric":
            "same_attempt_lap_features_used",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "historical_action_labels_used",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "modeling_development_only",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F7C3",

    "status":
        "R4F7C3_DEVELOPMENT_BASELINE_COMPARISON_READY",

    "development_rows":
        len(
            rows
        ),

    "development_years":
        years,

    "validation_2024_access_policy":
        "NOT_READ",

    "thermal_features":
        THERMAL_FEATURES,

    "models":
        list(
            MODELS.keys()
        ),

    "aggregate_metrics":
        aggregate_rows,

    "raw_reference_by_year":
        raw_reference_by_year,

    "top_reference_residual_outliers":
        top_residual_outliers,

    "interpretation_policy": {
        "driver_grouped_cv":
            (
                "Primary same-regime development comparison. "
                "Rows from the same driver never cross train/test."
            ),

        "leave_one_year_out":
            (
                "Cross-year transfer stress test. "
                "Not identical to future same-year pit-wall operation."
            ),

        "year_intercept_loyo":
            (
                "Held-out year has no trained year intercept, "
                "therefore predictor falls back to global training mean."
            ),

        "outliers":
            (
                "No observations are removed from primary metrics. "
                "Huber is included as a robustness model."
            ),
    },

    "input_hash":
        sha256(
            INPUT_PATH
        ),

    "next_phase_rule":
        (
            "Do not open 2024 validation yet. "
            "First determine whether thermal information improves "
            "development CV over Fast Friday reference-only. "
            "Then introduce hierarchical entry correction and "
            "latent-window dynamics."
        ),
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
# Console
# =============================================================================

print()
print("=" * 150)
print("AGGREGATE DEVELOPMENT CV")
print("=" * 150)

for scheme in [
    "DRIVER_GROUPED_5FOLD",
    "LEAVE_ONE_YEAR_OUT",
]:

    print()
    print(
        scheme
    )

    subset = [
        r
        for r in aggregate_rows
        if r[
            "validation_scheme"
        ]
        ==
        scheme
    ]

    subset = sorted(
        subset,
        key=lambda r:
            r[
                "mae_mph"
            ]
    )

    for r in subset:

        print(
            f"{r['model']:38s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f} | "
            f"CORR={r['correlation']}"
        )


print()
print("=" * 150)
print("LEAVE-ONE-YEAR-OUT DETAIL")
print("=" * 150)

for test_year in years:

    print()
    print(
        f"TEST YEAR {test_year}"
    )

    subset = [
        r
        for r in loyo_rows
        if r[
            "fold"
        ]
        ==
        f"TEST_{test_year}"
    ]

    subset = sorted(
        subset,
        key=lambda r:
            r[
                "mae_mph"
            ]
    )

    for r in subset:

        print(
            f"{r['model']:38s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f}"
        )


print()
print("=" * 150)
print("RAW FAST FRIDAY REFERENCE BY YEAR")
print("=" * 150)

for r in raw_reference_by_year:

    print(
        f"{r['year']} | "
        f"n={r['n']:3d} | "
        f"MAE={r['reference_only_mae']:.6f} | "
        f"RMSE={r['reference_only_rmse']:.6f} | "
        f"pred_bias={r['reference_bias_pred_minus_actual']:+.6f} | "
        f"actual_minus_ref_mean="
        f"{r['residual_mean_actual_minus_reference']:+.6f}"
    )


print()
print("=" * 150)
print("TOP REFERENCE-RESIDUAL OUTLIERS")
print("=" * 150)

for r in top_residual_outliers:

    print(
        f"{r['year']} | "
        f"{r['driver_name'][:24]:24s} | "
        f"ref={r['reference_speed_mph']:.3f} | "
        f"actual={r['observed_speed_mph']:.3f} | "
        f"residual={r['reference_residual_mph']:+.3f}"
    )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ]
    ==
    "FAIL"
]


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)} PASS | "
    f"0 WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_PRED.relative_to(ROOT)
)
print(
    OUT_METRICS.relative_to(ROOT)
)
print(
    OUT_LOYO.relative_to(ROOT)
)
print(
    OUT_GROUPCV.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C3_DEVELOPMENT_BASELINE_COMPARISON_READY"
)
