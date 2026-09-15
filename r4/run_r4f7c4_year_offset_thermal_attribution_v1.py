from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import hashlib

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT_PATH = (
    OUT /
    "r4f7c2c_development_numeric_matrix_v1.csv"
)

OUT_GLOBAL = (
    OUT /
    "r4f7c4_global_year_offset_thermal_cv_v1.csv"
)

OUT_WITHIN = (
    OUT /
    "r4f7c4_within_year_thermal_cv_v1.csv"
)

OUT_COEFFICIENTS = (
    OUT /
    "r4f7c4_within_year_ridge_coefficients_v1.csv"
)

OUT_PREDICTIONS = (
    OUT /
    "r4f7c4_attribution_predictions_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c4_year_offset_thermal_attribution_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c4_year_offset_thermal_attribution_report_v1.json"
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


def mae(y, p):

    return sum(
        abs(a - b)
        for a, b in zip(y, p)
    ) / len(y)


def rmse(y, p):

    return math.sqrt(
        sum(
            (a - b) ** 2
            for a, b in zip(y, p)
        ) / len(y)
    )


def bias(y, p):

    return sum(
        b - a
        for a, b in zip(y, p)
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

    if va <= 0 or vb <= 0:
        return None

    cov = sum(
        (x - ma) * (y - mb)
        for x, y in zip(a, b)
    )

    return (
        cov /
        math.sqrt(
            va * vb
        )
    )


if not INPUT_PATH.exists():

    raise SystemExit(
        f"MISSING INPUT: {INPUT_PATH}"
    )


try:
    import numpy as np

    from sklearn.pipeline import Pipeline

    from sklearn.preprocessing import (
        StandardScaler
    )

    from sklearn.linear_model import Ridge

    from sklearn.model_selection import (
        GroupKFold
    )

except Exception as e:

    raise SystemExit(
        "NUMPY / SCIKIT-LEARN REQUIRED: "
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
    "driver_name",
    "target_four_lap_average_speed_mph",
    "fast_friday_reference_mph",
    *THERMAL_FEATURES,
}


missing = sorted(
    required - set(fields)
)

if missing:

    raise SystemExit(
        "MISSING REQUIRED COLUMNS: "
        +
        ", ".join(missing)
    )


# =============================================================================
# Parse frozen development set
# =============================================================================

rows = []


for r in raw:

    year = int(
        float(
            clean(
                r.get("year")
            )
        )
    )

    observed = num(
        r.get(
            "target_four_lap_average_speed_mph"
        )
    )

    reference = num(
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
        observed is None
        or
        reference is None
        or
        any(
            v is None
            for v in features.values()
        )
    ):

        raise SystemExit(
            "INCOMPLETE ROW: "
            +
            clean(
                r.get(
                    "attempt_id"
                )
            )
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
            observed,

        "reference_speed":
            reference,

        "residual":
            observed
            -
            reference,

        **features,
    })


if len(rows) != 104:

    raise SystemExit(
        f"EXPECTED 104 ROWS, GOT {len(rows)}"
    )


years = sorted(
    {
        r["year"]
        for r in rows
    }
)


if years != [
    2020,
    2021,
    2023,
]:

    raise SystemExit(
        f"UNEXPECTED YEARS: {years}"
    )


print("=" * 150)
print("R4F7C4 — YEAR-OFFSET VS WITHIN-YEAR THERMAL ATTRIBUTION")
print("=" * 150)

print(
    f"Development rows: {len(rows)}"
)

print(
    f"Years: {years}"
)

print(
    "2024 validation is NOT read."
)


# =============================================================================
# Arrays
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
    y - ref
)

year_array = np.array(
    [
        r["year"]
        for r in rows
    ],
    dtype=int,
)

groups = np.array(
    [
        r["driver_key"]
        for r in rows
    ],
    dtype=object,
)


# =============================================================================
# Helpers
# =============================================================================

def training_year_offsets(
    train_idx
):

    global_offset = float(
        np.mean(
            residual[
                train_idx
            ]
        )
    )

    offsets = {}

    train_years = (
        year_array[
            train_idx
        ]
    )


    for yr in np.unique(
        train_years
    ):

        mask = (
            train_years == yr
        )

        offsets[
            int(yr)
        ] = float(
            np.mean(
                residual[
                    train_idx
                ][
                    mask
                ]
            )
        )


    return (
        offsets,
        global_offset,
    )


def year_offset_vector(
    train_idx,
    indices
):

    offsets, global_offset = (
        training_year_offsets(
            train_idx
        )
    )

    return np.array(
        [
            offsets.get(
                int(
                    year_array[idx]
                ),
                global_offset,
            )
            for idx in indices
        ],
        dtype=float,
    )


def ridge_pipeline():

    return Pipeline([
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


def metrics(
    actual,
    pred,
):

    actual_list = list(
        map(
            float,
            actual
        )
    )

    pred_list = list(
        map(
            float,
            pred
        )
    )

    corr = correlation(
        actual_list,
        pred_list,
    )

    return {
        "mae_mph":
            mae(
                actual_list,
                pred_list
            ),

        "rmse_mph":
            rmse(
                actual_list,
                pred_list
            ),

        "bias_mph":
            bias(
                actual_list,
                pred_list
            ),

        "correlation":
            (
                corr
                if corr is not None
                else ""
            ),
    }


# =============================================================================
# Global driver-grouped CV
#
# Important:
# YEAR_OFFSET models are OFFLINE STRUCTURAL DIAGNOSTICS.
#
# Their training-fold year offset may use observations occurring later
# than a particular test attempt. Therefore this is NOT the final
# prospective pit-wall implementation.
#
# Purpose:
# determine whether the thermal gain survives after explicit removal
# of annual/session-level mean calibration.
# =============================================================================

global_prediction_rows = []

gkf = GroupKFold(
    n_splits=5
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

    # -------------------------------------------------------------------------
    # Model 1 — raw Fast Friday
    # -------------------------------------------------------------------------

    pred_reference = (
        ref[
            test_idx
        ].copy()
    )


    # -------------------------------------------------------------------------
    # Model 2 — Fast Friday + training-fold year offset
    # -------------------------------------------------------------------------

    test_year_offset = (
        year_offset_vector(
            train_idx,
            test_idx,
        )
    )

    pred_year = (
        ref[
            test_idx
        ]
        +
        test_year_offset
    )


    # -------------------------------------------------------------------------
    # Model 3 — thermal ridge without explicit year calibration
    # -------------------------------------------------------------------------

    ridge_raw = ridge_pipeline()

    ridge_raw.fit(
        X[
            train_idx
        ],
        residual[
            train_idx
        ],
    )

    pred_thermal = (
        ref[
            test_idx
        ]
        +
        ridge_raw.predict(
            X[
                test_idx
            ]
        )
    )


    # -------------------------------------------------------------------------
    # Model 4 — year offset + thermal ridge
    #
    # Train thermal model on residual AFTER removing training-fold
    # year-specific mean.
    # -------------------------------------------------------------------------

    train_year_offset = (
        year_offset_vector(
            train_idx,
            train_idx,
        )
    )

    centered_train_target = (
        residual[
            train_idx
        ]
        -
        train_year_offset
    )


    ridge_centered = (
        ridge_pipeline()
    )

    ridge_centered.fit(
        X[
            train_idx
        ],
        centered_train_target,
    )


    centered_thermal_pred = (
        ridge_centered.predict(
            X[
                test_idx
            ]
        )
    )


    pred_year_thermal = (
        ref[
            test_idx
        ]
        +
        test_year_offset
        +
        centered_thermal_pred
    )


    fold_models = {
        "FAST_FRIDAY_REFERENCE_ONLY":
            pred_reference,

        "FAST_FRIDAY_PLUS_YEAR_OFFSET":
            pred_year,

        "FAST_FRIDAY_PLUS_THERMAL_RIDGE":
            pred_thermal,

        "FAST_FRIDAY_PLUS_YEAR_OFFSET_PLUS_THERMAL_RIDGE":
            pred_year_thermal,
    }


    for model_name, pred in fold_models.items():

        for idx, p in zip(
            test_idx,
            pred,
        ):

            global_prediction_rows.append({
                "validation_scheme":
                    "GLOBAL_DRIVER_GROUPED_5FOLD",

                "fold":
                    f"FOLD_{fold_no}",

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
                    float(
                        y[idx]
                    ),

                "reference_speed_mph":
                    float(
                        ref[idx]
                    ),

                "predicted_speed_mph":
                    float(p),

                "error_mph":
                    float(
                        p - y[idx]
                    ),

                "absolute_error_mph":
                    abs(
                        float(
                            p - y[idx]
                        )
                    ),
            })


# =============================================================================
# Aggregate global CV
# =============================================================================

global_metric_rows = []


global_models = [
    "FAST_FRIDAY_REFERENCE_ONLY",
    "FAST_FRIDAY_PLUS_YEAR_OFFSET",
    "FAST_FRIDAY_PLUS_THERMAL_RIDGE",
    "FAST_FRIDAY_PLUS_YEAR_OFFSET_PLUS_THERMAL_RIDGE",
]


for model_name in global_models:

    subset = [
        r
        for r in global_prediction_rows
        if r[
            "model"
        ] == model_name
    ]

    actual = [
        float(
            r[
                "observed_speed_mph"
            ]
        )
        for r in subset
    ]

    pred = [
        float(
            r[
                "predicted_speed_mph"
            ]
        )
        for r in subset
    ]

    result = metrics(
        actual,
        pred,
    )


    global_metric_rows.append({
        "validation_scheme":
            "GLOBAL_DRIVER_GROUPED_5FOLD",

        "model":
            model_name,

        "n":
            len(subset),

        **result,
    })


# =============================================================================
# Within-year CV
#
# This directly tests within-session/year variation.
#
# No cross-year weather distribution can explain success here because
# each model is fitted and evaluated entirely inside one qualifying year.
# =============================================================================

within_prediction_rows = []
within_metric_rows = []


for year in years:

    year_indices = np.where(
        year_array == year
    )[0]

    year_groups = groups[
        year_indices
    ]


    unique_driver_count = len(
        set(
            year_groups
        )
    )


    n_splits = min(
        5,
        unique_driver_count,
    )


    if n_splits < 2:
        continue


    year_gkf = GroupKFold(
        n_splits=n_splits
    )


    for fold_no, (
        local_train,
        local_test,
    ) in enumerate(
        year_gkf.split(
            X[
                year_indices
            ],
            y[
                year_indices
            ],
            groups=year_groups,
        ),
        start=1,
    ):

        train_idx = (
            year_indices[
                local_train
            ]
        )

        test_idx = (
            year_indices[
                local_test
            ]
        )


        # Fast Friday raw
        pred_reference = (
            ref[
                test_idx
            ].copy()
        )


        # Training-only same-year constant offset
        offset = float(
            np.mean(
                residual[
                    train_idx
                ]
            )
        )

        pred_offset = (
            ref[
                test_idx
            ]
            +
            offset
        )


        # Same-year thermal model
        model = ridge_pipeline()

        model.fit(
            X[
                train_idx
            ],
            residual[
                train_idx
            ],
        )


        pred_thermal = (
            ref[
                test_idx
            ]
            +
            model.predict(
                X[
                    test_idx
                ]
            )
        )


        predictions = {
            "FAST_FRIDAY_REFERENCE_ONLY":
                pred_reference,

            "FAST_FRIDAY_PLUS_CONSTANT_OFFSET":
                pred_offset,

            "FAST_FRIDAY_PLUS_WITHIN_YEAR_THERMAL_RIDGE":
                pred_thermal,
        }


        for model_name, pred in predictions.items():

            for idx, p in zip(
                test_idx,
                pred,
            ):

                within_prediction_rows.append({
                    "validation_scheme":
                        "WITHIN_YEAR_DRIVER_GROUPED_CV",

                    "year":
                        year,

                    "fold":
                        f"FOLD_{fold_no}",

                    "model":
                        model_name,

                    "attempt_id":
                        rows[
                            idx
                        ][
                            "attempt_id"
                        ],

                    "driver_key":
                        rows[
                            idx
                        ][
                            "driver_key"
                        ],

                    "observed_speed_mph":
                        float(
                            y[idx]
                        ),

                    "reference_speed_mph":
                        float(
                            ref[idx]
                        ),

                    "predicted_speed_mph":
                        float(p),

                    "error_mph":
                        float(
                            p - y[idx]
                        ),

                    "absolute_error_mph":
                        abs(
                            float(
                                p - y[idx]
                            )
                        ),
                })


    for model_name in [
        "FAST_FRIDAY_REFERENCE_ONLY",
        "FAST_FRIDAY_PLUS_CONSTANT_OFFSET",
        "FAST_FRIDAY_PLUS_WITHIN_YEAR_THERMAL_RIDGE",
    ]:

        subset = [
            r
            for r in within_prediction_rows
            if (
                r[
                    "year"
                ] == year
                and
                r[
                    "model"
                ] == model_name
            )
        ]


        actual = [
            float(
                r[
                    "observed_speed_mph"
                ]
            )
            for r in subset
        ]

        pred = [
            float(
                r[
                    "predicted_speed_mph"
                ]
            )
            for r in subset
        ]


        result = metrics(
            actual,
            pred,
        )


        within_metric_rows.append({
            "year":
                year,

            "model":
                model_name,

            "n":
                len(
                    subset
                ),

            **result,
        })


# =============================================================================
# Fit within-year ridge coefficients for stability diagnostic
#
# These are descriptive only, not selected prospective coefficients.
# Features are standardized before fitting so coefficient magnitudes
# are somewhat comparable.
# =============================================================================

coefficient_rows = []


for year in years:

    idx = np.where(
        year_array == year
    )[0]


    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        X[idx]
    )


    model = Ridge(
        alpha=10.0
    )

    model.fit(
        X_scaled,
        residual[idx],
    )


    for feature, coef in zip(
        THERMAL_FEATURES,
        model.coef_,
    ):

        coefficient_rows.append({
            "year":
                year,

            "feature":
                feature,

            "standardized_ridge_coefficient":
                float(coef),

            "sign":
                (
                    "POSITIVE"
                    if coef > 0
                    else
                    (
                        "NEGATIVE"
                        if coef < 0
                        else
                        "ZERO"
                    )
                ),
        })


# =============================================================================
# Coefficient sign agreement summary
# =============================================================================

sign_summary = []


for feature in THERMAL_FEATURES:

    subset = [
        r
        for r in coefficient_rows
        if r[
            "feature"
        ] == feature
    ]


    signs = [
        r[
            "sign"
        ]
        for r in subset
        if r[
            "sign"
        ] != "ZERO"
    ]


    counts = {
        "POSITIVE":
            signs.count(
                "POSITIVE"
            ),

        "NEGATIVE":
            signs.count(
                "NEGATIVE"
            ),
    }


    dominant = max(
        counts.values()
    )


    sign_summary.append({
        "feature":
            feature,

        "positive_years":
            counts[
                "POSITIVE"
            ],

        "negative_years":
            counts[
                "NEGATIVE"
            ],

        "same_sign_all_three_years":
            dominant == 3,

        "dominant_sign_count":
            dominant,
    })


# =============================================================================
# Save
# =============================================================================

with OUT_GLOBAL.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            global_metric_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        global_metric_rows
    )


with OUT_WITHIN.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            within_metric_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        within_metric_rows
    )


with OUT_COEFFICIENTS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            coefficient_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        coefficient_rows
    )


prediction_rows = (
    global_prediction_rows
    +
    within_prediction_rows
)


with OUT_PREDICTIONS.open(
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


# =============================================================================
# Decision diagnostics
# =============================================================================

global_lookup = {
    r[
        "model"
    ]:
    r
    for r in global_metric_rows
}


ref_global_mae = (
    global_lookup[
        "FAST_FRIDAY_REFERENCE_ONLY"
    ][
        "mae_mph"
    ]
)

year_global_mae = (
    global_lookup[
        "FAST_FRIDAY_PLUS_YEAR_OFFSET"
    ][
        "mae_mph"
    ]
)

thermal_global_mae = (
    global_lookup[
        "FAST_FRIDAY_PLUS_THERMAL_RIDGE"
    ][
        "mae_mph"
    ]
)

year_thermal_global_mae = (
    global_lookup[
        "FAST_FRIDAY_PLUS_YEAR_OFFSET_PLUS_THERMAL_RIDGE"
    ][
        "mae_mph"
    ]
)


thermal_survives_year_adjustment = (
    year_thermal_global_mae
    <
    year_global_mae
)


within_year_results = []


for year in years:

    lookup = {
        r[
            "model"
        ]:
        r
        for r in within_metric_rows
        if r[
            "year"
        ] == year
    }


    offset_mae = (
        lookup[
            "FAST_FRIDAY_PLUS_CONSTANT_OFFSET"
        ][
            "mae_mph"
        ]
    )

    thermal_mae = (
        lookup[
            "FAST_FRIDAY_PLUS_WITHIN_YEAR_THERMAL_RIDGE"
        ][
            "mae_mph"
        ]
    )


    within_year_results.append({
        "year":
            year,

        "offset_mae":
            offset_mae,

        "thermal_mae":
            thermal_mae,

        "thermal_beats_offset":
            thermal_mae
            <
            offset_mae,

        "mae_gain":
            offset_mae
            -
            thermal_mae,
    })


# =============================================================================
# QA
# =============================================================================

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
            "global_prediction_rows_per_model",
        "value":
            all(
                r[
                    "n"
                ] == 104
                for r in global_metric_rows
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    r[
                        "n"
                    ] == 104
                    for r in global_metric_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "all_years_within_year_evaluated",
        "value":
            sorted(
                {
                    r[
                        "year"
                    ]
                    for r in within_metric_rows
                }
            ),
        "expected":
            "[2020, 2021, 2023]",
        "status":
            (
                "PASS"
                if sorted(
                    {
                        r[
                            "year"
                        ]
                        for r in within_metric_rows
                    }
                )
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
            "2024_validation_read",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
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
            "attribution_only_no_2024_model_selection",
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
        "R4F7C4",

    "status":
        "R4F7C4_YEAR_OFFSET_THERMAL_ATTRIBUTION_READY",

    "development_rows":
        len(rows),

    "development_years":
        years,

    "2024_validation_access":
        "NOT_READ",

    "global_driver_grouped_metrics":
        global_metric_rows,

    "within_year_metrics":
        within_metric_rows,

    "within_year_results":
        within_year_results,

    "thermal_survives_explicit_year_offset":
        thermal_survives_year_adjustment,

    "coefficient_sign_summary":
        sign_summary,

    "interpretation_boundary":
        (
            "Year-offset models are offline structural diagnostics, "
            "not final prospective predictors, because fold-level "
            "same-year offsets are not constrained to use only "
            "observations before each test attempt."
        ),

    "decision_rule": {
        "case_A":
            (
                "If year-offset alone explains most of the C3 thermal "
                "gain and year+thermal adds little, do not interpret "
                "C3 as strong within-session thermal evidence."
            ),

        "case_B":
            (
                "If year+thermal materially beats year-offset and "
                "within-year thermal also improves multiple years, "
                "promote thermal state as a real incremental structural "
                "signal and proceed to time-safe latent-window modeling."
            ),

        "case_C":
            (
                "If within-year thermal is highly heterogeneous by year, "
                "use hierarchical shrinkage / year-sensitive response "
                "rather than one universal thermal coefficient."
            ),
    },

    "input_hash":
        sha256(
            INPUT_PATH
        ),

    "next_phase":
        (
            "R4F7C5: construct prospective past-only session calibration "
            "and latent-window state. 2024 remains unopened until the "
            "development architecture is frozen."
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
print("GLOBAL DRIVER-GROUPED ATTRIBUTION")
print("=" * 150)

for r in sorted(
    global_metric_rows,
    key=lambda x:
        x[
            "mae_mph"
        ],
):

    print(
        f"{r['model']:56s} | "
        f"n={r['n']:3d} | "
        f"MAE={r['mae_mph']:.6f} | "
        f"RMSE={r['rmse_mph']:.6f} | "
        f"BIAS={r['bias_mph']:+.6f} | "
        f"CORR={r['correlation']}"
    )


print()
print(
    "THERMAL SURVIVES EXPLICIT YEAR OFFSET: "
    f"{thermal_survives_year_adjustment}"
)


print()
print("=" * 150)
print("WITHIN-YEAR DRIVER-GROUPED ATTRIBUTION")
print("=" * 150)

for year in years:

    print()
    print(
        f"YEAR {year}"
    )

    subset = [
        r
        for r in within_metric_rows
        if r[
            "year"
        ] == year
    ]

    for r in sorted(
        subset,
        key=lambda x:
            x[
                "mae_mph"
            ],
    ):

        print(
            f"{r['model']:52s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f} | "
            f"CORR={r['correlation']}"
        )


print()
print("=" * 150)
print("WITHIN-YEAR THERMAL GAIN OVER CONSTANT OFFSET")
print("=" * 150)

for r in within_year_results:

    print(
        f"{r['year']} | "
        f"offset_MAE={r['offset_mae']:.6f} | "
        f"thermal_MAE={r['thermal_mae']:.6f} | "
        f"gain={r['mae_gain']:+.6f} | "
        f"thermal_beats_offset={r['thermal_beats_offset']}"
    )


print()
print("=" * 150)
print("STANDARDIZED RIDGE COEFFICIENT SIGN STABILITY")
print("=" * 150)

for r in sign_summary:

    print(
        f"{r['feature']:54s} | "
        f"positive_years={r['positive_years']} | "
        f"negative_years={r['negative_years']} | "
        f"all_same_sign={r['same_sign_all_three_years']}"
    )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
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
    OUT_GLOBAL.relative_to(ROOT)
)
print(
    OUT_WITHIN.relative_to(ROOT)
)
print(
    OUT_COEFFICIENTS.relative_to(ROOT)
)
print(
    OUT_PREDICTIONS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C4_YEAR_OFFSET_THERMAL_ATTRIBUTION_READY"
)
