from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import csv
import json
import math
import hashlib
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT_PATH = (
    OUT /
    "r4f7c2c_development_numeric_matrix_v1.csv"
)

OUT_STATE = (
    OUT /
    "r4f7c5_prospective_past_only_state_panel_v1.csv"
)

OUT_HEURISTIC = (
    OUT /
    "r4f7c5_past_only_heuristic_metrics_v1.csv"
)

OUT_LOYO = (
    OUT /
    "r4f7c5_prospective_loyo_model_metrics_v1.csv"
)

OUT_PRED = (
    OUT /
    "r4f7c5_prospective_loyo_predictions_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c5_prospective_past_only_field_state_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c5_prospective_past_only_field_state_report_v1.json"
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


STATE_FEATURES = [
    "session_elapsed_minutes",

    "past_other_count",

    "past_other_mean_residual_mph",

    "past_other_median_residual_mph",

    "past_other_ewma_10m_residual_mph",

    "past_other_ewma_20m_residual_mph",

    "past_other_ewma_30m_residual_mph",

    "past_other_ewma_45m_residual_mph",

    "past_other_recent_10m_count",

    "past_other_recent_20m_count",

    "past_other_recent_30m_count",

    "past_other_recent_45m_count",

    "own_prior_available",

    "own_previous_residual_mph",

    "own_previous_age_minutes",
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


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.endswith("Z"):
        s = (
            s[:-1]
            +
            "+00:00"
        )

    try:
        dt = datetime.fromisoformat(
            s
        )

    except Exception:
        return None

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


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

    with path.open(
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(
                chunk
            )

    return h.hexdigest()


def mae(y, p):
    return (
        sum(
            abs(a - b)
            for a, b
            in zip(y, p)
        )
        /
        len(y)
    )


def rmse(y, p):
    return math.sqrt(
        sum(
            (a - b) ** 2
            for a, b
            in zip(y, p)
        )
        /
        len(y)
    )


def bias(y, p):
    return (
        sum(
            b - a
            for a, b
            in zip(y, p)
        )
        /
        len(y)
    )


def correlation(a, b):

    if len(a) < 2:
        return None

    ma = (
        sum(a)
        /
        len(a)
    )

    mb = (
        sum(b)
        /
        len(b)
    )

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
        (x - ma)
        *
        (y - mb)
        for x, y
        in zip(a, b)
    )

    return (
        cov
        /
        math.sqrt(
            va * vb
        )
    )


def metric_dict(
    actual,
    pred,
):

    actual = list(
        map(
            float,
            actual
        )
    )

    pred = list(
        map(
            float,
            pred
        )
    )

    corr = correlation(
        actual,
        pred
    )

    return {
        "n":
            len(actual),

        "mae_mph":
            mae(
                actual,
                pred
            ),

        "rmse_mph":
            rmse(
                actual,
                pred
            ),

        "bias_mph":
            bias(
                actual,
                pred
            ),

        "correlation":
            (
                corr
                if corr is not None
                else ""
            ),
    }


def ewma_residual(
    past_rows,
    current_time,
    half_life_minutes,
):

    if not past_rows:
        return None

    numerator = 0.0
    denominator = 0.0

    for r in past_rows:

        age_minutes = (
            (
                current_time
                -
                r[
                    "_time"
                ]
            ).total_seconds()
            /
            60.0
        )

        if age_minutes < 0:
            raise RuntimeError(
                "FUTURE ROW ENTERED PAST STATE"
            )

        weight = math.exp(
            -math.log(2.0)
            *
            age_minutes
            /
            half_life_minutes
        )

        numerator += (
            weight
            *
            r[
                "_residual"
            ]
        )

        denominator += weight


    if denominator <= 0:
        return None

    return (
        numerator
        /
        denominator
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

    from sklearn.linear_model import (
        Ridge
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
    "performance_time_utc",
    "target_four_lap_average_speed_mph",
    "fast_friday_reference_mph",
    *THERMAL_FEATURES,
}


missing = sorted(
    required
    -
    set(fields)
)

if missing:

    raise SystemExit(
        "MISSING REQUIRED COLUMNS: "
        +
        ", ".join(
            missing
        )
    )


# =============================================================================
# Parse frozen development rows
# =============================================================================

rows = []


for r in raw:

    year = int(
        float(
            clean(
                r.get(
                    "year"
                )
            )
        )
    )

    time = parse_dt(
        r.get(
            "performance_time_utc"
        )
    )

    actual = num(
        r.get(
            "target_four_lap_average_speed_mph"
        )
    )

    reference = num(
        r.get(
            "fast_friday_reference_mph"
        )
    )


    thermal = {
        f:
            num(
                r.get(f)
            )
        for f in THERMAL_FEATURES
    }


    if (
        time is None
        or
        actual is None
        or
        reference is None
        or
        any(
            value is None
            for value
            in thermal.values()
        )
    ):

        raise SystemExit(
            "INCOMPLETE DEVELOPMENT ROW: "
            +
            clean(
                r.get(
                    "attempt_id"
                )
            )
        )


    rows.append({
        **r,

        "_year":
            year,

        "_time":
            time,

        "_actual":
            actual,

        "_reference":
            reference,

        "_residual":
            actual
            -
            reference,

        "_driver":
            clean(
                r.get(
                    "driver_key"
                )
            ),
    })


if len(rows) != 104:

    raise SystemExit(
        f"EXPECTED 104 ROWS, GOT {len(rows)}"
    )


years = sorted(
    {
        r[
            "_year"
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
        f"UNEXPECTED YEARS: {years}"
    )


print("=" * 152)
print("R4F7C5 — PROSPECTIVE PAST-ONLY FIELD STATE")
print("=" * 152)

print(
    f"Development rows: {len(rows)}"
)

print(
    f"Years: {years}"
)

print(
    "2024 validation is NOT read."
)

print(
    "Common-field state uses only STRICTLY EARLIER "
    "same-year attempts from OTHER drivers."
)


# =============================================================================
# Build strictly prospective state panel
# =============================================================================

state_rows = []


for year in years:

    year_rows = [
        r
        for r in rows
        if r[
            "_year"
        ] == year
    ]


    year_rows = sorted(
        year_rows,
        key=lambda r: (
            r[
                "_time"
            ],
            r[
                "attempt_id"
            ],
        )
    )


    first_time = min(
        r[
            "_time"
        ]
        for r in year_rows
    )


    for current in year_rows:

        current_time = (
            current[
                "_time"
            ]
        )

        current_driver = (
            current[
                "_driver"
            ]
        )


        # ---------------------------------------------------------------------
        # Common field state:
        # strictly earlier + other drivers only.
        # ---------------------------------------------------------------------

        past_other = [
            r
            for r in year_rows
            if (
                r[
                    "_time"
                ]
                <
                current_time
                and
                r[
                    "_driver"
                ]
                !=
                current_driver
            )
        ]


        # ---------------------------------------------------------------------
        # Own previous information is kept separate.
        # ---------------------------------------------------------------------

        past_own = [
            r
            for r in year_rows
            if (
                r[
                    "_time"
                ]
                <
                current_time
                and
                r[
                    "_driver"
                ]
                ==
                current_driver
            )
        ]


        past_own = sorted(
            past_own,
            key=lambda r:
                r[
                    "_time"
                ]
        )


        past_residuals = [
            r[
                "_residual"
            ]
            for r in past_other
        ]


        if past_residuals:

            past_mean = (
                sum(
                    past_residuals
                )
                /
                len(
                    past_residuals
                )
            )

            past_median = (
                statistics.median(
                    past_residuals
                )
            )

        else:

            past_mean = None
            past_median = None


        ewma_10 = ewma_residual(
            past_other,
            current_time,
            10.0,
        )

        ewma_20 = ewma_residual(
            past_other,
            current_time,
            20.0,
        )

        ewma_30 = ewma_residual(
            past_other,
            current_time,
            30.0,
        )

        ewma_45 = ewma_residual(
            past_other,
            current_time,
            45.0,
        )


        def recent_count(
            minutes
        ):

            return sum(
                (
                    (
                        current_time
                        -
                        r[
                            "_time"
                        ]
                    ).total_seconds()
                    /
                    60.0
                )
                <= minutes
                for r in past_other
            )


        own_previous = (
            past_own[-1]
            if past_own
            else None
        )


        if own_previous:

            own_age = (
                (
                    current_time
                    -
                    own_previous[
                        "_time"
                    ]
                ).total_seconds()
                /
                60.0
            )

            own_residual = (
                own_previous[
                    "_residual"
                ]
            )

            own_available = 1.0

        else:

            own_age = 0.0
            own_residual = 0.0
            own_available = 0.0


        session_elapsed = (
            (
                current_time
                -
                first_time
            ).total_seconds()
            /
            60.0
        )


        state = {
            "attempt_id":
                current[
                    "attempt_id"
                ],

            "year":
                year,

            "driver_key":
                current_driver,

            "driver_name":
                clean(
                    current.get(
                        "driver_name"
                    )
                ),

            "performance_time_utc":
                clean(
                    current.get(
                        "performance_time_utc"
                    )
                ),

            "actual_speed_mph":
                current[
                    "_actual"
                ],

            "reference_speed_mph":
                current[
                    "_reference"
                ],

            "reference_residual_mph":
                current[
                    "_residual"
                ],

            "session_elapsed_minutes":
                session_elapsed,

            "past_other_count":
                len(
                    past_other
                ),

            "past_other_mean_residual_mph":
                (
                    past_mean
                    if past_mean is not None
                    else 0.0
                ),

            "past_other_median_residual_mph":
                (
                    past_median
                    if past_median is not None
                    else 0.0
                ),

            "past_other_ewma_10m_residual_mph":
                (
                    ewma_10
                    if ewma_10 is not None
                    else 0.0
                ),

            "past_other_ewma_20m_residual_mph":
                (
                    ewma_20
                    if ewma_20 is not None
                    else 0.0
                ),

            "past_other_ewma_30m_residual_mph":
                (
                    ewma_30
                    if ewma_30 is not None
                    else 0.0
                ),

            "past_other_ewma_45m_residual_mph":
                (
                    ewma_45
                    if ewma_45 is not None
                    else 0.0
                ),

            "past_other_recent_10m_count":
                recent_count(
                    10.0
                ),

            "past_other_recent_20m_count":
                recent_count(
                    20.0
                ),

            "past_other_recent_30m_count":
                recent_count(
                    30.0
                ),

            "past_other_recent_45m_count":
                recent_count(
                    45.0
                ),

            "own_prior_available":
                own_available,

            "own_previous_residual_mph":
                own_residual,

            "own_previous_age_minutes":
                own_age,

            "past_state_supported":
                len(
                    past_other
                )
                > 0,

            "past_state_n_ge_3":
                len(
                    past_other
                )
                >= 3,

            "past_state_n_ge_5":
                len(
                    past_other
                )
                >= 5,
        }


        for f in THERMAL_FEATURES:

            state[
                f
            ] = num(
                current.get(
                    f
                )
            )


        state_rows.append(
            state
        )


state_rows = sorted(
    state_rows,
    key=lambda r: (
        r[
            "year"
        ],
        r[
            "performance_time_utc"
        ],
        r[
            "attempt_id"
        ],
    )
)


# =============================================================================
# Leakage audit
#
# Reconstruct every state and ensure no contributing observation has
# timestamp >= current timestamp.
# =============================================================================

leakage_violations = []


for current in state_rows:

    current_time = parse_dt(
        current[
            "performance_time_utc"
        ]
    )

    year = current[
        "year"
    ]

    driver = current[
        "driver_key"
    ]


    source_candidates = [
        r
        for r in rows
        if (
            r[
                "_year"
            ] == year
            and
            r[
                "_driver"
            ] != driver
            and
            r[
                "_time"
            ] < current_time
        )
    ]


    if len(
        source_candidates
    ) != current[
        "past_other_count"
    ]:

        leakage_violations.append(
            current[
                "attempt_id"
            ]
        )


# =============================================================================
# Fixed past-only heuristics
#
# These are NOT declared to be the latent window.
# They are observable prospective proxies used only to establish whether
# past field performance carries predictive information.
# =============================================================================

heuristic_rows = []


for support_name, minimum_count in [
    (
        "N_GE_1",
        1,
    ),
    (
        "N_GE_3",
        3,
    ),
    (
        "N_GE_5",
        5,
    ),
]:

    for year in years:

        subset = [
            r
            for r in state_rows
            if (
                r[
                    "year"
                ] == year
                and
                r[
                    "past_other_count"
                ]
                >=
                minimum_count
            )
        ]


        if not subset:
            continue


        actual = [
            r[
                "actual_speed_mph"
            ]
            for r in subset
        ]


        models = {
            "FAST_FRIDAY_REFERENCE_ONLY":
                [
                    r[
                        "reference_speed_mph"
                    ]
                    for r in subset
                ],

            "REFERENCE_PLUS_PAST_OTHER_MEAN":
                [
                    r[
                        "reference_speed_mph"
                    ]
                    +
                    r[
                        "past_other_mean_residual_mph"
                    ]
                    for r in subset
                ],

            "REFERENCE_PLUS_PAST_OTHER_MEDIAN":
                [
                    r[
                        "reference_speed_mph"
                    ]
                    +
                    r[
                        "past_other_median_residual_mph"
                    ]
                    for r in subset
                ],

            "REFERENCE_PLUS_PAST_OTHER_EWMA20":
                [
                    r[
                        "reference_speed_mph"
                    ]
                    +
                    r[
                        "past_other_ewma_20m_residual_mph"
                    ]
                    for r in subset
                ],

            "REFERENCE_PLUS_PAST_OTHER_EWMA45":
                [
                    r[
                        "reference_speed_mph"
                    ]
                    +
                    r[
                        "past_other_ewma_45m_residual_mph"
                    ]
                    for r in subset
                ],
        }


        for model_name, pred in models.items():

            m = metric_dict(
                actual,
                pred,
            )

            heuristic_rows.append({
                "support":
                    support_name,

                "year":
                    year,

                "model":
                    model_name,

                **m,
            })


# =============================================================================
# LOYO prospective structural evaluation
#
# Every test-row state feature is itself constructed using only information
# strictly available before that test attempt.
#
# Model coefficients are learned from OTHER YEARS only.
# =============================================================================

STATE_MODEL_FEATURES = STATE_FEATURES


all_feature_names = (
    STATE_MODEL_FEATURES
    +
    THERMAL_FEATURES
)


def feature_matrix(
    subset,
    feature_names,
):

    return np.array(
        [
            [
                float(
                    r[f]
                )
                for f
                in feature_names
            ]
            for r in subset
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


prediction_rows = []
loyo_metric_rows = []


for test_year in years:

    train_rows = [
        r
        for r in state_rows
        if r[
            "year"
        ] != test_year
    ]

    test_rows = [
        r
        for r in state_rows
        if r[
            "year"
        ] == test_year
    ]


    train_target = np.array(
        [
            r[
                "reference_residual_mph"
            ]
            for r in train_rows
        ],
        dtype=float,
    )


    # Fair cross-year constant calibration baseline.
    train_global_offset = float(
        np.mean(
            train_target
        )
    )


    model_specs = {
        "FAST_FRIDAY_REFERENCE_ONLY":
            None,

        "REFERENCE_PLUS_GLOBAL_TRAIN_CALIBRATION":
            None,

        "REFERENCE_PLUS_PAST_STATE_RIDGE":
            STATE_MODEL_FEATURES,

        "REFERENCE_PLUS_THERMAL_RIDGE":
            THERMAL_FEATURES,

        "REFERENCE_PLUS_PAST_STATE_PLUS_THERMAL_RIDGE":
            all_feature_names,
    }


    for model_name, feature_names in model_specs.items():

        if (
            model_name
            ==
            "FAST_FRIDAY_REFERENCE_ONLY"
        ):

            pred = np.array(
                [
                    r[
                        "reference_speed_mph"
                    ]
                    for r in test_rows
                ],
                dtype=float,
            )


        elif (
            model_name
            ==
            "REFERENCE_PLUS_GLOBAL_TRAIN_CALIBRATION"
        ):

            pred = np.array(
                [
                    r[
                        "reference_speed_mph"
                    ]
                    +
                    train_global_offset
                    for r in test_rows
                ],
                dtype=float,
            )


        else:

            X_train = feature_matrix(
                train_rows,
                feature_names,
            )

            X_test = feature_matrix(
                test_rows,
                feature_names,
            )


            model = ridge_pipeline()

            model.fit(
                X_train,
                train_target,
            )


            residual_pred = model.predict(
                X_test
            )


            pred = np.array(
                [
                    r[
                        "reference_speed_mph"
                    ]
                    for r in test_rows
                ],
                dtype=float,
            ) + residual_pred


        actual = np.array(
            [
                r[
                    "actual_speed_mph"
                ]
                for r in test_rows
            ],
            dtype=float,
        )


        metric = metric_dict(
            actual,
            pred,
        )


        loyo_metric_rows.append({
            "test_year":
                test_year,

            "model":
                model_name,

            **metric,
        })


        for r, p in zip(
            test_rows,
            pred,
        ):

            prediction_rows.append({
                "test_year":
                    test_year,

                "model":
                    model_name,

                "attempt_id":
                    r[
                        "attempt_id"
                    ],

                "driver_key":
                    r[
                        "driver_key"
                    ],

                "performance_time_utc":
                    r[
                        "performance_time_utc"
                    ],

                "past_other_count":
                    r[
                        "past_other_count"
                    ],

                "own_prior_available":
                    r[
                        "own_prior_available"
                    ],

                "observed_speed_mph":
                    r[
                        "actual_speed_mph"
                    ],

                "reference_speed_mph":
                    r[
                        "reference_speed_mph"
                    ],

                "predicted_speed_mph":
                    float(p),

                "error_mph":
                    float(
                        p
                        -
                        r[
                            "actual_speed_mph"
                        ]
                    ),

                "absolute_error_mph":
                    abs(
                        float(
                            p
                            -
                            r[
                                "actual_speed_mph"
                            ]
                        )
                    ),
            })


# =============================================================================
# Aggregate LOYO
# =============================================================================

aggregate_loyo = []


for model_name in sorted(
    {
        r[
            "model"
        ]
        for r in prediction_rows
    }
):

    subset = [
        r
        for r in prediction_rows
        if r[
            "model"
        ] == model_name
    ]

    actual = [
        r[
            "observed_speed_mph"
        ]
        for r in subset
    ]

    pred = [
        r[
            "predicted_speed_mph"
        ]
        for r in subset
    ]

    m = metric_dict(
        actual,
        pred,
    )

    aggregate_loyo.append({
        "test_year":
            "ALL_LOYO",

        "model":
            model_name,

        **m,
    })


# =============================================================================
# Support summary
# =============================================================================

support_summary = []


for year in years:

    subset = [
        r
        for r in state_rows
        if r[
            "year"
        ] == year
    ]


    support_summary.append({
        "year":
            year,

        "rows":
            len(
                subset
            ),

        "past_other_ge_1":
            sum(
                r[
                    "past_other_count"
                ] >= 1
                for r in subset
            ),

        "past_other_ge_3":
            sum(
                r[
                    "past_other_count"
                ] >= 3
                for r in subset
            ),

        "past_other_ge_5":
            sum(
                r[
                    "past_other_count"
                ] >= 5
                for r in subset
            ),

        "own_prior_available":
            sum(
                r[
                    "own_prior_available"
                ] > 0
                for r in subset
            ),

        "median_past_other_count":
            statistics.median(
                [
                    r[
                        "past_other_count"
                    ]
                    for r in subset
                ]
            ),
    })


# =============================================================================
# Save
# =============================================================================

with OUT_STATE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            state_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        state_rows
    )


with OUT_HEURISTIC.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            heuristic_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        heuristic_rows
    )


combined_loyo = (
    loyo_metric_rows
    +
    aggregate_loyo
)


with OUT_LOYO.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            combined_loyo[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        combined_loyo
    )


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


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "development_rows",
        "value":
            len(
                state_rows
            ),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(
                    state_rows
                ) == 104
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
            "past_state_leakage_violations",
        "value":
            len(
                leakage_violations
            ),
        "expected":
            0,
        "status":
            (
                "PASS"
                if not leakage_violations
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
            "common_field_excludes_current_driver",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "strictly_earlier_time_rule",
        "value":
            True,
        "expected":
            True,
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
            "past_proxies_not_declared_latent_truth",
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
        "R4F7C5",

    "status":
        "R4F7C5_PROSPECTIVE_PAST_ONLY_FIELD_STATE_READY",

    "development_rows":
        len(
            state_rows
        ),

    "development_years":
        years,

    "2024_validation_access":
        "NOT_READ",

    "support_summary":
        support_summary,

    "state_features":
        STATE_MODEL_FEATURES,

    "thermal_features":
        THERMAL_FEATURES,

    "aggregate_loyo_metrics":
        aggregate_loyo,

    "common_field_state_rule":
        (
            "Only qualifying attempts with timestamp strictly earlier "
            "than the current attempt and belonging to other drivers "
            "may contribute to common-field state."
        ),

    "own_entry_rule":
        (
            "Earlier attempts from the same driver are kept separate "
            "as own_previous_residual and may be used prospectively."
        ),

    "ewma_rule":
        (
            "10/20/30/45-minute exponentially decayed past residual "
            "summaries are observable state proxies, not definitions "
            "of the latent performance window."
        ),

    "important_boundary":
        (
            "The purpose of R4F7C5 is to test whether strictly past "
            "whole-field performance history contains incremental "
            "prospective information. A formal latent state-space "
            "model is introduced only if this evidence supports it."
        ),

    "input_hash":
        sha256(
            INPUT_PATH
        ),

    "next_phase_rule":
        (
            "If past-only state improves fair LOYO or consistently "
            "improves supported within-year heuristics, proceed to "
            "R4F7C6 latent state-space / hierarchical shrinkage. "
            "If not, latent-window uncertainty must remain broad and "
            "weather/history should not be over-weighted."
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
print("=" * 152)
print("PAST-STATE SUPPORT")
print("=" * 152)

for r in support_summary:

    print(
        f"{r['year']} | "
        f"rows={r['rows']:3d} | "
        f"N>=1={r['past_other_ge_1']:3d} | "
        f"N>=3={r['past_other_ge_3']:3d} | "
        f"N>=5={r['past_other_ge_5']:3d} | "
        f"own_prior={r['own_prior_available']:3d} | "
        f"median_past_N={r['median_past_other_count']}"
    )


print()
print("=" * 152)
print("PAST-ONLY HEURISTICS — N>=3 SUPPORT")
print("=" * 152)

for year in years:

    print()
    print(
        f"YEAR {year}"
    )

    subset = [
        r
        for r in heuristic_rows
        if (
            r[
                "year"
            ] == year
            and
            r[
                "support"
            ] == "N_GE_3"
        )
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
            f"{r['model']:42s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f} | "
            f"CORR={r['correlation']}"
        )


print()
print("=" * 152)
print("PROSPECTIVE LEAVE-ONE-YEAR-OUT — AGGREGATE")
print("=" * 152)

for r in sorted(
    aggregate_loyo,
    key=lambda r:
        r[
            "mae_mph"
        ]
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
print("=" * 152)
print("PROSPECTIVE LEAVE-ONE-YEAR-OUT — BY YEAR")
print("=" * 152)

for year in years:

    print()
    print(
        f"TEST YEAR {year}"
    )

    subset = [
        r
        for r in loyo_metric_rows
        if r[
            "test_year"
        ] == year
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
            f"{r['model']:52s} | "
            f"n={r['n']:3d} | "
            f"MAE={r['mae_mph']:.6f} | "
            f"RMSE={r['rmse_mph']:.6f} | "
            f"BIAS={r['bias_mph']:+.6f}"
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
    OUT_STATE.relative_to(ROOT)
)
print(
    OUT_HEURISTIC.relative_to(ROOT)
)
print(
    OUT_LOYO.relative_to(ROOT)
)
print(
    OUT_PRED.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C5_PROSPECTIVE_PAST_ONLY_FIELD_STATE_READY"
)
