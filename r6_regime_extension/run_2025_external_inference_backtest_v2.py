from pathlib import Path
import importlib.util
import json
import re

import numpy as np
import pandas as pd


ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

ENGINE_PATH = (
    ROOT /
    "r6_regime_extension/"
    "run_production_inference_v1.py"
)

TRANSITIONS_PATH = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_repeat_ptsc_linkage_v1/"
    "r6_repeat_transitions_primary_physics_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_ptsc_canonical_v1/"
    "r6_ptsc_2019_2025_canonical_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "external_regime_inference_backtest_2025_v2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

PRODUCT_HORIZON_MIN = 120.0
VALIDATION_HORIZON_MIN = 180.0

MAX_PTSC_GAP_MIN = 30.0
STEP_MIN = 1.0
DRAWS = 20000
BASE_SEED = 20250913


# ============================================================
# Load frozen production inference implementation
# ============================================================

spec = importlib.util.spec_from_file_location(
    "production_inference_v1",
    ENGINE_PATH
)

engine = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    engine
)


# ============================================================
# Helpers
# ============================================================

def norm(s):
    return (
        str(s)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_col(df, exact=None, token_sets=None):

    normalized = {
        norm(c): c
        for c in df.columns
    }

    if exact:
        for candidate in exact:

            key = norm(candidate)

            if key in normalized:
                return normalized[key]

    if token_sets:
        for tokens in token_sets:

            for c in df.columns:

                n = norm(c)

                if all(
                    token.lower() in n
                    for token in tokens
                ):
                    return c

    return None


def require_col(df, label, exact=None, token_sets=None):

    c = find_col(
        df,
        exact=exact,
        token_sets=token_sets,
    )

    if c is None:

        raise RuntimeError(
            f"Could not detect {label}.\n"
            f"Columns:\n"
            +
            "\n".join(
                map(str, df.columns)
            )
        )

    return c


def interpolate_curve_at_wait(
    curve,
    wait_min,
):

    x = curve[
        "wait_minutes"
    ].to_numpy(
        dtype=float
    )

    if (
        wait_min < x.min() - 1e-9
        or
        wait_min > x.max() + 1e-9
    ):
        return None

    fields = [
        "expected_delta_track_c",
        "expected_physical_delta_speed_mph",
        "median_total_delta_speed_mph",
        "q10_delta_speed_mph",
        "q90_delta_speed_mph",
        "q05_delta_speed_mph",
        "q95_delta_speed_mph",
        "p_improve",
        "expected_future_speed_mph",
        "median_future_speed_mph",
    ]

    result = {
        "wait_minutes":
            float(wait_min)
    }

    for field in fields:

        result[field] = float(
            np.interp(
                wait_min,
                x,
                curve[
                    field
                ].to_numpy(
                    dtype=float
                )
            )
        )

    return result


# ============================================================
# Transition schema
# ============================================================

transitions = pd.read_csv(
    TRANSITIONS_PATH,
    low_memory=False
)

year_col = require_col(
    transitions,
    "year",
    exact=[
        "year"
    ]
)

driver_col = require_col(
    transitions,
    "driver",
    exact=[
        "driver_name",
        "driver",
    ],
    token_sets=[
        ["driver"]
    ]
)

car_col = require_col(
    transitions,
    "car number",
    exact=[
        "car_number",
        "car_no",
        "car",
    ],
    token_sets=[
        ["car", "number"]
    ]
)

before_time_col = require_col(
    transitions,
    "before timestamp",
    exact=[
        "before_time_utc",
        "from_time_utc",
        "before_timestamp_utc",
        "from_timestamp_utc",
    ],
    token_sets=[
        ["before", "time"],
        ["from", "time"],
    ]
)

after_time_col = require_col(
    transitions,
    "after timestamp",
    exact=[
        "after_time_utc",
        "to_time_utc",
        "after_timestamp_utc",
        "to_timestamp_utc",
    ],
    token_sets=[
        ["after", "time"],
        ["to", "time"],
    ]
)

before_speed_col = require_col(
    transitions,
    "before speed",
    exact=[
        "before_speed_mph",
        "from_speed_mph",
        "before_four_lap_average_speed_mph",
    ],
    token_sets=[
        ["before", "speed"],
        ["from", "speed"],
    ]
)

after_speed_col = require_col(
    transitions,
    "after speed",
    exact=[
        "after_speed_mph",
        "to_speed_mph",
        "after_four_lap_average_speed_mph",
    ],
    token_sets=[
        ["after", "speed"],
        ["to", "speed"],
    ]
)

before_track_col = require_col(
    transitions,
    "before track temperature",
    exact=[
        "before_track_temp_c",
        "from_track_temp_c",
        "before_ptsc_track_c",
    ],
    token_sets=[
        ["before", "track"],
        ["from", "track"],
    ]
)

before_ambient_col = require_col(
    transitions,
    "before ambient temperature",
    exact=[
        "before_air_temp_c",
        "from_air_temp_c",
        "before_ambient_c",
        "before_ptsc_ambient_c",
    ],
    token_sets=[
        ["before", "ambient"],
        ["from", "ambient"],
        ["before", "air", "temp"],
    ]
)


t = transitions[
    pd.to_numeric(
        transitions[
            year_col
        ],
        errors="coerce"
    )
    ==
    2025
].copy()

t[
    "_before_time"
] = pd.to_datetime(
    t[
        before_time_col
    ],
    utc=True,
    errors="coerce"
)

t[
    "_after_time"
] = pd.to_datetime(
    t[
        after_time_col
    ],
    utc=True,
    errors="coerce"
)

for target, source in [
    (
        "_before_speed",
        before_speed_col
    ),
    (
        "_after_speed",
        after_speed_col
    ),
    (
        "_before_track",
        before_track_col
    ),
    (
        "_before_ambient",
        before_ambient_col
    ),
]:

    t[
        target
    ] = pd.to_numeric(
        t[
            source
        ],
        errors="coerce"
    )

t[
    "_actual_wait_min"
] = (
    (
        t[
            "_after_time"
        ]
        -
        t[
            "_before_time"
        ]
    )
    .dt.total_seconds()
    /
    60.0
)

t[
    "_actual_delta_speed"
] = (
    t[
        "_after_speed"
    ]
    -
    t[
        "_before_speed"
    ]
)


# ============================================================
# PTSC
# ============================================================

ptsc = pd.read_csv(
    PTSC_PATH,
    low_memory=False
)

ptsc_year_col = require_col(
    ptsc,
    "PTSC year",
    exact=[
        "year"
    ]
)

ptsc_time_col = require_col(
    ptsc,
    "PTSC time",
    exact=[
        "timestamp_utc",
        "time_utc",
        "datetime_utc",
    ],
    token_sets=[
        ["utc"],
        ["time"],
    ]
)

ptsc_ambient_col = require_col(
    ptsc,
    "PTSC ambient",
    exact=[
        "ambient_c",
        "air_temp_c",
        "temp_c",
        "ptsc_ambient_c",
    ],
    token_sets=[
        ["ambient"],
        ["air", "temp"],
    ]
)

p = ptsc[
    pd.to_numeric(
        ptsc[
            ptsc_year_col
        ],
        errors="coerce"
    )
    ==
    2025
].copy()

p[
    "_time"
] = pd.to_datetime(
    p[
        ptsc_time_col
    ],
    utc=True,
    errors="coerce"
)

p[
    "_ambient"
] = pd.to_numeric(
    p[
        ptsc_ambient_col
    ],
    errors="coerce"
)

p = (
    p[
        p[
            "_time"
        ].notna()
        &
        p[
            "_ambient"
        ].notna()
    ]
    .sort_values(
        "_time"
    )
    .drop_duplicates(
        subset=[
            "_time"
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# Realized ambient trajectory
# ============================================================

def build_realized_forecast(
    start_time,
    start_ambient,
    target_wait,
):

    target_end = (
        start_time
        +
        pd.Timedelta(
            minutes=float(
                target_wait
            )
        )
    )

    left_rows = p[
        p[
            "_time"
        ]
        <=
        start_time
    ]

    right_rows = p[
        p[
            "_time"
        ]
        >=
        target_end
    ]

    if left_rows.empty:
        return None, "NO_PTSC_BEFORE_START"

    if right_rows.empty:
        return None, "NO_PTSC_AFTER_TARGET"

    left = left_rows.iloc[
        -1
    ][
        "_time"
    ]

    right = right_rows.iloc[
        0
    ][
        "_time"
    ]

    window = p[
        (
            p[
                "_time"
            ]
            >=
            left
        )
        &
        (
            p[
                "_time"
            ]
            <=
            right
        )
    ][
        [
            "_time",
            "_ambient",
        ]
    ].copy()

    window = window.sort_values(
        "_time"
    ).reset_index(
        drop=True
    )

    if len(
        window
    ) < 2:

        return None, "TOO_FEW_PTSC_POINTS"

    for i in range(
        1,
        len(
            window
        )
    ):

        a = window.loc[
            i - 1,
            "_time"
        ]

        b = window.loc[
            i,
            "_time"
        ]

        gap_min = (
            b - a
        ).total_seconds() / 60.0

        overlap_start = max(
            a,
            start_time
        )

        overlap_end = min(
            b,
            target_end
        )

        if (
            overlap_end
            >
            overlap_start
            and
            gap_min
            >
            MAX_PTSC_GAP_MIN
        ):

            return (
                None,
                f"PTSC_GAP_{gap_min:.1f}_MIN"
            )

    forecast = pd.DataFrame({
        "timestamp_utc":
            window[
                "_time"
            ],

        "ambient_c":
            window[
                "_ambient"
            ],
    })

    anchor = pd.DataFrame({
        "timestamp_utc": [
            start_time
        ],

        "ambient_c": [
            float(
                start_ambient
            )
        ],
    })

    forecast = pd.concat(
        [
            forecast,
            anchor,
        ],
        ignore_index=True
    )

    forecast = (
        forecast
        .sort_values(
            "timestamp_utc"
        )
        .drop_duplicates(
            subset=[
                "timestamp_utc"
            ],
            keep="last"
        )
        .reset_index(
            drop=True
        )
    )

    return forecast, "OK"


# ============================================================
# Run up to frozen model's validated 180-minute horizon
# ============================================================

rows = []
manifest = []

case_counter = 0

for _, r in t.iterrows():

    case_counter += 1

    driver = str(
        r[
            driver_col
        ]
    )

    car = str(
        r[
            car_col
        ]
    )

    before_time = r[
        "_before_time"
    ]

    after_time = r[
        "_after_time"
    ]

    before_speed = r[
        "_before_speed"
    ]

    after_speed = r[
        "_after_speed"
    ]

    current_track = r[
        "_before_track"
    ]

    current_ambient = r[
        "_before_ambient"
    ]

    actual_wait = r[
        "_actual_wait_min"
    ]

    actual_delta = r[
        "_actual_delta_speed"
    ]

    case_id = (
        f"2025_{case_counter:02d}_"
        +
        re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            driver
        ).strip(
            "_"
        )
    )

    base = {
        "case_id":
            case_id,

        "driver_name":
            driver,

        "car_number":
            car,

        "before_time_utc":
            before_time,

        "after_time_utc":
            after_time,

        "actual_wait_min":
            actual_wait,

        "before_speed_mph":
            before_speed,

        "after_speed_mph":
            after_speed,

        "actual_delta_speed_mph":
            actual_delta,

        "current_track_c":
            current_track,

        "current_ambient_c":
            current_ambient,

        "inside_product_120":
            (
                pd.notna(
                    actual_wait
                )
                and
                actual_wait
                <=
                PRODUCT_HORIZON_MIN
            ),
    }

    required = [
        before_time,
        after_time,
        before_speed,
        after_speed,
        current_track,
        current_ambient,
        actual_wait,
    ]

    if any(
        pd.isna(
            x
        )
        for x in required
    ):

        base[
            "status"
        ] = "EXCLUDED_MISSING_INPUT"

        manifest.append(
            base
        )

        continue

    if actual_wait <= 0:

        base[
            "status"
        ] = "EXCLUDED_NONPOSITIVE_WAIT"

        manifest.append(
            base
        )

        continue

    if actual_wait > VALIDATION_HORIZON_MIN:

        base[
            "status"
        ] = "EXCLUDED_WAIT_GT_180"

        manifest.append(
            base
        )

        continue

    forecast, forecast_status = (
        build_realized_forecast(
            start_time=before_time,
            start_ambient=current_ambient,
            target_wait=actual_wait,
        )
    )

    if forecast is None:

        base[
            "status"
        ] = (
            "EXCLUDED_"
            +
            forecast_status
        )

        manifest.append(
            base
        )

        continue

    case_dir = (
        OUT /
        "cases" /
        case_id
    )

    case_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    forecast.to_csv(
        case_dir /
        "realized_ambient_trajectory.csv",
        index=False
    )

    artificial_session_end = (
        before_time
        +
        pd.Timedelta(
            minutes=VALIDATION_HORIZON_MIN
        )
    )

    curve, metadata = engine.simulate_curve(
        current_speed_mph=float(
            before_speed
        ),

        current_track_c=float(
            current_track
        ),

        current_ambient_c=float(
            current_ambient
        ),

        current_time_utc=before_time,

        session_end_utc=artificial_session_end,

        forecast=forecast,

        requested_horizon_min=float(
            actual_wait
        ),

        step_min=STEP_MIN,

        draws=DRAWS,

        seed=(
            BASE_SEED
            +
            case_counter
        ),
    )

    point = interpolate_curve_at_wait(
        curve,
        float(
            actual_wait
        )
    )

    if point is None:

        base[
            "status"
        ] = "EXCLUDED_CURVE_RANGE"

        manifest.append(
            base
        )

        continue

    curve.to_csv(
        case_dir /
        "inference_curve.csv",
        index=False
    )

    expected = point[
        "expected_physical_delta_speed_mph"
    ]

    lower80 = point[
        "q10_delta_speed_mph"
    ]

    upper80 = point[
        "q90_delta_speed_mph"
    ]

    lower90 = point[
        "q05_delta_speed_mph"
    ]

    upper90 = point[
        "q95_delta_speed_mph"
    ]

    result = {
        **base,

        "status":
            "BACKTEST_INCLUDED",

        "validation_band":
            (
                "PRODUCT_120"
                if actual_wait
                <=
                PRODUCT_HORIZON_MIN
                else
                "EXTENDED_120_TO_180"
            ),

        "model_expected_delta_speed_mph":
            expected,

        "model_median_delta_speed_mph":
            point[
                "median_total_delta_speed_mph"
            ],

        "lower_80_mph":
            lower80,

        "upper_80_mph":
            upper80,

        "lower_90_mph":
            lower90,

        "upper_90_mph":
            upper90,

        "p_improve":
            point[
                "p_improve"
            ],

        "absolute_error_mph":
            abs(
                expected
                -
                actual_delta
            ),

        "signed_error_mph":
            (
                expected
                -
                actual_delta
            ),

        "actual_improved":
            bool(
                actual_delta
                >
                0
            ),

        "predicted_direction_improved":
            bool(
                expected
                >
                0
            ),

        "direction_correct":
            bool(
                (
                    actual_delta
                    >
                    0
                )
                ==
                (
                    expected
                    >
                    0
                )
            ),

        "inside_80":
            bool(
                lower80
                <=
                actual_delta
                <=
                upper80
            ),

        "inside_90":
            bool(
                lower90
                <=
                actual_delta
                <=
                upper90
            ),

        "expected_delta_track_c":
            point[
                "expected_delta_track_c"
            ],

        "track_residual_mode":
            metadata[
                "track_residual_mode"
            ],
    }

    rows.append(
        result
    )

    manifest.append(
        result
    )


results = pd.DataFrame(
    rows
)

manifest_df = pd.DataFrame(
    manifest
)

if results.empty:

    raise RuntimeError(
        "No usable validation cases."
    )


# ============================================================
# Metrics
# ============================================================

def metrics_for(
    df,
    label
):

    if df.empty:

        return {
            "label":
                label,

            "n":
                0,
        }

    improved = df[
        df[
            "actual_improved"
        ]
    ]

    declined = df[
        ~df[
            "actual_improved"
        ]
    ]

    return {
        "label":
            label,

        "n":
            int(
                len(
                    df
                )
            ),

        "mae_mph":
            float(
                df[
                    "absolute_error_mph"
                ].mean()
            ),

        "median_absolute_error_mph":
            float(
                df[
                    "absolute_error_mph"
                ].median()
            ),

        "rmse_mph":
            float(
                np.sqrt(
                    np.mean(
                        df[
                            "signed_error_mph"
                        ] ** 2
                    )
                )
            ),

        "direction_accuracy":
            float(
                df[
                    "direction_correct"
                ].mean()
            ),

        "coverage_80":
            float(
                df[
                    "inside_80"
                ].mean()
            ),

        "coverage_90":
            float(
                df[
                    "inside_90"
                ].mean()
            ),

        "actual_improvement_rate":
            float(
                df[
                    "actual_improved"
                ].mean()
            ),

        "mean_p_improve":
            float(
                df[
                    "p_improve"
                ].mean()
            ),

        "mean_p_improve_when_actual_improved":
            (
                float(
                    improved[
                        "p_improve"
                    ].mean()
                )
                if len(
                    improved
                )
                else np.nan
            ),

        "mean_p_improve_when_actual_declined":
            (
                float(
                    declined[
                        "p_improve"
                    ].mean()
                )
                if len(
                    declined
                )
                else np.nan
            ),
    }


product = results[
    results[
        "actual_wait_min"
    ]
    <=
    PRODUCT_HORIZON_MIN
].copy()

extended = results.copy()

metrics_product = metrics_for(
    product,
    "PRODUCT_HORIZON_LE_120"
)

metrics_extended = metrics_for(
    extended,
    "EXTERNAL_VALIDATION_LE_180"
)

metrics = {
    "validation_type":
        "2025_EXTERNAL_REGIME_REALIZED_WEATHER_BACKTEST",

    "production_core":
        "FROZEN_2020_2024",

    "test_regime":
        "2025_AEROSCREEN_HYBRID",

    "production_horizon_minutes":
        PRODUCT_HORIZON_MIN,

    "scientific_validation_horizon_minutes":
        VALIDATION_HORIZON_MIN,

    "product_subset":
        metrics_product,

    "extended_validation":
        metrics_extended,

    "weather_semantics":
        (
            "Realized PTSC ambient trajectory. "
            "Retrospective physical-inference validation, "
            "not weather-forecast validation."
        ),

    "product_semantics":
        (
            "Production inference remains capped at 120 minutes. "
            "The 120-180 minute cases are used only for external "
            "validation because the frozen future-track model was "
            "validated through 180 minutes."
        ),

    "queue_wait_prediction":
        False,

    "strategy_recommendation":
        False,
}


# ============================================================
# Save
# ============================================================

RESULTS_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_rows_v2.csv"
)

MANIFEST_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_manifest_v2.csv"
)

METRICS_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_metrics_v2.json"
)

results.to_csv(
    RESULTS_OUT,
    index=False
)

manifest_df.to_csv(
    MANIFEST_OUT,
    index=False
)

METRICS_OUT.write_text(
    json.dumps(
        metrics,
        indent=2
    ),
    encoding="utf-8"
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)

print(
    "2025 EXTERNAL-REGIME INFERENCE BACKTEST V2"
)

print(
    "=" * 170
)

print(
    "Production horizon: 120 min"
)

print(
    "Scientific validation horizon: 180 min"
)

print(
    "Production core: frozen 2020-2024"
)


print(
    "\n" + "=" * 170
)

print(
    "PART 1 — CASE ELIGIBILITY"
)

print(
    "=" * 170
)

print(
    manifest_df[
        "status"
    ]
    .value_counts()
    .rename_axis(
        "status"
    )
    .reset_index(
        name="rows"
    )
    .to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)

print(
    "PART 2 — INCLUDED CASES"
)

print(
    "=" * 170
)

print(
    results[
        [
            "case_id",
            "driver_name",
            "actual_wait_min",
            "validation_band",
            "actual_delta_speed_mph",
            "model_expected_delta_speed_mph",
            "absolute_error_mph",
            "p_improve",
            "direction_correct",
            "inside_80",
            "inside_90",
        ]
    ]
    .sort_values(
        "actual_wait_min"
    )
    .to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)

print(
    "PART 3 — PRODUCT-HORIZON METRICS <=120"
)

print(
    "=" * 170
)

for k, v in metrics_product.items():
    print(
        f"{k}: {v}"
    )


print(
    "\n" + "=" * 170
)

print(
    "PART 4 — EXTENDED EXTERNAL VALIDATION METRICS <=180"
)

print(
    "=" * 170
)

for k, v in metrics_extended.items():
    print(
        f"{k}: {v}"
    )


print(
    "\n" + "=" * 170
)

print(
    "PART 5 — CASES OUTSIDE 180 / OTHER EXCLUSIONS"
)

print(
    "=" * 170
)

excluded = manifest_df[
    manifest_df[
        "status"
    ]
    !=
    "BACKTEST_INCLUDED"
]

if excluded.empty:

    print(
        "NONE"
    )

else:

    print(
        excluded[
            [
                "case_id",
                "driver_name",
                "actual_wait_min",
                "status",
            ]
        ]
        .sort_values(
            "actual_wait_min"
        )
        .to_string(
            index=False
        )
    )


print(
    "\nOUTPUTS:"
)

for pth in [
    RESULTS_OUT,
    MANIFEST_OUT,
    METRICS_OUT,
]:

    print(
        pth.relative_to(
            ROOT
        )
    )

print(
    "\nEXTERNAL_REGIME_INFERENCE_BACKTEST_2025_V2_COMPLETE"
)
