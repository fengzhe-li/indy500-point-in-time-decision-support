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
    "external_regime_inference_backtest_2025_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

MAX_HORIZON_MIN = 120.0
MAX_PTSC_GAP_MIN = 30.0
STEP_MIN = 1.0
DRAWS = 20000
BASE_SEED = 20250913


# ============================================================
# Load production inference engine without refitting anything
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


def find_col(
    df,
    exact=None,
    token_sets=None,
):
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
                    t.lower() in n
                    for t in tokens
                ):
                    return c

    return None


def require_col(
    df,
    label,
    exact=None,
    token_sets=None,
):
    c = find_col(
        df,
        exact=exact,
        token_sets=token_sets,
    )

    if c is None:
        raise RuntimeError(
            f"Could not detect {label}.\n"
            f"Available columns:\n"
            +
            "\n".join(
                map(str, df.columns)
            )
        )

    return c


def boolish(x):
    if isinstance(x, bool):
        return x

    if pd.isna(x):
        return False

    return str(x).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
        "pass",
        "safe",
        "primary_safe",
    }


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

    out = {
        "wait_minutes":
            float(wait_min)
    }

    for field in fields:
        out[field] = float(
            np.interp(
                wait_min,
                x,
                curve[field].to_numpy(
                    dtype=float
                )
            )
        )

    return out


# ============================================================
# Load 2025 transitions
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
    "before/from timestamp",
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
    "after/to timestamp",
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
    "before/from four-lap speed",
    exact=[
        "before_speed_mph",
        "from_speed_mph",
        "before_four_lap_average_speed_mph",
        "from_four_lap_average_speed_mph",
    ],
    token_sets=[
        ["before", "speed"],
        ["from", "speed"],
    ]
)

after_speed_col = require_col(
    transitions,
    "after/to four-lap speed",
    exact=[
        "after_speed_mph",
        "to_speed_mph",
        "after_four_lap_average_speed_mph",
        "to_four_lap_average_speed_mph",
    ],
    token_sets=[
        ["after", "speed"],
        ["to", "speed"],
    ]
)

before_track_col = require_col(
    transitions,
    "before/from track temperature",
    exact=[
        "before_track_temp_c",
        "from_track_temp_c",
        "before_ptsc_track_c",
        "from_ptsc_track_c",
    ],
    token_sets=[
        ["before", "track", "c"],
        ["from", "track", "c"],
    ]
)

before_ambient_col = require_col(
    transitions,
    "before/from ambient temperature",
    exact=[
        "before_air_temp_c",
        "from_air_temp_c",
        "before_ambient_c",
        "from_ambient_c",
        "before_ptsc_ambient_c",
        "from_ptsc_ambient_c",
    ],
    token_sets=[
        ["before", "ambient"],
        ["from", "ambient"],
        ["before", "air", "temp"],
        ["from", "air", "temp"],
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

if t.empty:
    raise RuntimeError(
        "No 2025 transitions found."
    )

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

t[
    "_before_speed"
] = pd.to_numeric(
    t[
        before_speed_col
    ],
    errors="coerce"
)

t[
    "_after_speed"
] = pd.to_numeric(
    t[
        after_speed_col
    ],
    errors="coerce"
)

t[
    "_before_track"
] = pd.to_numeric(
    t[
        before_track_col
    ],
    errors="coerce"
)

t[
    "_before_ambient"
] = pd.to_numeric(
    t[
        before_ambient_col
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
# Load realized 2025 PTSC trajectory
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
    "PTSC UTC timestamp",
    exact=[
        "timestamp_utc",
        "time_utc",
        "datetime_utc",
        "observed_time_utc",
        "utc",
    ],
    token_sets=[
        ["utc"],
        ["time"],
    ]
)

ptsc_ambient_col = require_col(
    ptsc,
    "PTSC ambient temperature",
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

p = p[
    p[
        "_time"
    ].notna()
    &
    p[
        "_ambient"
    ].notna()
].copy()

p = (
    p
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

if p.empty:
    raise RuntimeError(
        "No usable 2025 PTSC observations."
    )


# ============================================================
# Case trajectory construction
# ============================================================

def build_realized_forecast(
    start_time,
    start_ambient,
    actual_wait,
):
    """
    Build historical realized ambient trajectory.

    Critical rule:
    do not bridge PTSC gaps > 30 min inside the interval needed
    to reach the actual second attempt.
    """

    target_end = (
        start_time
        +
        pd.Timedelta(
            minutes=float(
                min(
                    MAX_HORIZON_MIN,
                    actual_wait
                )
            )
        )
    )

    # Need a point shortly before/at start and shortly after/at target.
    before_candidates = p[
        p[
            "_time"
        ]
        <=
        start_time
    ]

    after_candidates = p[
        p[
            "_time"
        ]
        >=
        target_end
    ]

    if before_candidates.empty:
        return None, "NO_PTSC_BEFORE_START"

    if after_candidates.empty:
        return None, "NO_PTSC_AFTER_TARGET"

    left = before_candidates.iloc[
        -1
    ][
        "_time"
    ]

    right = after_candidates.iloc[
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

    if len(window) < 2:
        return None, "TOO_FEW_PTSC_POINTS"

    gaps = (
        window[
            "_time"
        ]
        .sort_values()
        .diff()
        .dt.total_seconds()
        /
        60.0
    )

    max_gap = float(
        gaps.max()
    )

    # Only reject a large gap if it actually lies inside the
    # inference interval from current attempt to actual reattempt.
    ordered = window.sort_values(
        "_time"
    ).reset_index(
        drop=True
    )

    blocking_gap = False
    blocking_gap_value = np.nan

    for i in range(
        1,
        len(ordered)
    ):
        a = ordered.loc[
            i - 1,
            "_time"
        ]

        b = ordered.loc[
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

        overlaps_needed_interval = (
            overlap_end
            >
            overlap_start
        )

        if (
            overlaps_needed_interval
            and
            gap_min
            >
            MAX_PTSC_GAP_MIN
        ):
            blocking_gap = True
            blocking_gap_value = gap_min
            break

    if blocking_gap:
        return (
            None,
            f"PTSC_GAP_{blocking_gap_value:.1f}_MIN"
        )

    forecast = pd.DataFrame({
        "timestamp_utc":
            ordered[
                "_time"
            ],

        "ambient_c":
            ordered[
                "_ambient"
            ],
    })

    # Exact observed current-state anchor overrides interpolation at t=0.
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
# Run external backtest
# ============================================================

results = []
case_manifest = []

case_counter = 0

for idx, r in t.iterrows():

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

    base_manifest = {
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
    }

    # ----------------------------------------
    # Input eligibility
    # ----------------------------------------

    missing = []

    for name, value in [
        (
            "before_time",
            before_time
        ),
        (
            "after_time",
            after_time
        ),
        (
            "before_speed",
            before_speed
        ),
        (
            "after_speed",
            after_speed
        ),
        (
            "current_track",
            current_track
        ),
        (
            "current_ambient",
            current_ambient
        ),
        (
            "actual_wait",
            actual_wait
        ),
    ]:
        if pd.isna(value):
            missing.append(
                name
            )

    if missing:
        base_manifest[
            "status"
        ] = (
            "EXCLUDED_MISSING_INPUT:"
            +
            ",".join(
                missing
            )
        )

        case_manifest.append(
            base_manifest
        )

        continue

    if actual_wait <= 0:
        base_manifest[
            "status"
        ] = "EXCLUDED_NONPOSITIVE_WAIT"

        case_manifest.append(
            base_manifest
        )

        continue

    if actual_wait > MAX_HORIZON_MIN:
        base_manifest[
            "status"
        ] = "EXCLUDED_WAIT_GT_120"

        case_manifest.append(
            base_manifest
        )

        continue

    forecast, forecast_status = (
        build_realized_forecast(
            start_time=before_time,
            start_ambient=current_ambient,
            actual_wait=actual_wait,
        )
    )

    if forecast is None:
        base_manifest[
            "status"
        ] = (
            "EXCLUDED_"
            +
            forecast_status
        )

        case_manifest.append(
            base_manifest
        )

        continue

    # Save exact realized trajectory used by this case.
    case_dir = (
        OUT /
        "cases" /
        case_id
    )

    case_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    forecast_out = (
        case_dir /
        "realized_ambient_trajectory.csv"
    )

    forecast.to_csv(
        forecast_out,
        index=False
    )

    # Set session-end later than 120 min so horizon restriction
    # comes only from product 120-min max / forecast coverage.
    artificial_session_end = (
        before_time
        +
        pd.Timedelta(
            minutes=MAX_HORIZON_MIN
        )
    )

    # Production engine expects enough forecast coverage for its
    # requested horizon. For this historical case, we only need
    # coverage through actual reattempt time.
    requested_horizon = float(
        actual_wait
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

        requested_horizon_min=requested_horizon,

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
        ),
    )

    if point is None:
        base_manifest[
            "status"
        ] = "EXCLUDED_CURVE_DOES_NOT_REACH_ACTUAL_WAIT"

        case_manifest.append(
            base_manifest
        )

        continue

    curve_out = (
        case_dir /
        "inference_curve.csv"
    )

    curve.to_csv(
        curve_out,
        index=False
    )

    expected = point[
        "expected_physical_delta_speed_mph"
    ]

    median = point[
        "median_total_delta_speed_mph"
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

    p_improve = point[
        "p_improve"
    ]

    inside80 = (
        lower80
        <=
        actual_delta
        <=
        upper80
    )

    inside90 = (
        lower90
        <=
        actual_delta
        <=
        upper90
    )

    actual_improved = (
        actual_delta
        >
        0
    )

    predicted_direction = (
        expected
        >
        0
    )

    result = {
        **base_manifest,

        "status":
            "BACKTEST_INCLUDED",

        "model_expected_delta_speed_mph":
            expected,

        "model_median_delta_speed_mph":
            median,

        "lower_80_mph":
            lower80,

        "upper_80_mph":
            upper80,

        "lower_90_mph":
            lower90,

        "upper_90_mph":
            upper90,

        "p_improve":
            p_improve,

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
            actual_improved,

        "predicted_expected_direction_improved":
            predicted_direction,

        "direction_correct":
            (
                actual_improved
                ==
                predicted_direction
            ),

        "inside_80":
            inside80,

        "inside_90":
            inside90,

        "expected_delta_track_c":
            point[
                "expected_delta_track_c"
            ],

        "forecast_status":
            forecast_status,

        "engine_track_residual_mode":
            metadata[
                "track_residual_mode"
            ],
    }

    results.append(
        result
    )

    case_manifest.append(
        result
    )


# ============================================================
# Aggregate metrics
# ============================================================

results_df = pd.DataFrame(
    results
)

manifest_df = pd.DataFrame(
    case_manifest
)

if results_df.empty:
    raise RuntimeError(
        "No 2025 cases survived external backtest gates."
    )

n = len(
    results_df
)

mae = float(
    results_df[
        "absolute_error_mph"
    ].mean()
)

median_ae = float(
    results_df[
        "absolute_error_mph"
    ].median()
)

rmse = float(
    np.sqrt(
        np.mean(
            results_df[
                "signed_error_mph"
            ] ** 2
        )
    )
)

direction_accuracy = float(
    results_df[
        "direction_correct"
    ].mean()
)

coverage80 = float(
    results_df[
        "inside_80"
    ].mean()
)

coverage90 = float(
    results_df[
        "inside_90"
    ].mean()
)

actual_improve_rate = float(
    results_df[
        "actual_improved"
    ].mean()
)

mean_p_improve = float(
    results_df[
        "p_improve"
    ].mean()
)

# Simple probability discrimination:
# mean P(improve) among actually improved vs declined cases.
improved_cases = results_df[
    results_df[
        "actual_improved"
    ]
]

declined_cases = results_df[
    ~results_df[
        "actual_improved"
    ]
]

mean_p_when_improved = (
    float(
        improved_cases[
            "p_improve"
        ].mean()
    )
    if len(
        improved_cases
    )
    else np.nan
)

mean_p_when_declined = (
    float(
        declined_cases[
            "p_improve"
        ].mean()
    )
    if len(
        declined_cases
    )
    else np.nan
)

metrics = {
    "validation_type":
        "2025_EXTERNAL_REGIME_REALIZED_WEATHER_BACKTEST",

    "production_core":
        "FROZEN_2020_2024",

    "test_regime":
        "2025_AEROSCREEN_HYBRID",

    "max_product_horizon_minutes":
        MAX_HORIZON_MIN,

    "included_cases":
        int(
            n
        ),

    "excluded_cases":
        int(
            len(
                manifest_df
            )
            -
            n
        ),

    "mae_mph":
        mae,

    "median_absolute_error_mph":
        median_ae,

    "rmse_mph":
        rmse,

    "direction_accuracy":
        direction_accuracy,

    "coverage_80":
        coverage80,

    "coverage_90":
        coverage90,

    "actual_improvement_rate":
        actual_improve_rate,

    "mean_predicted_p_improve":
        mean_p_improve,

    "mean_p_improve_when_actual_improved":
        mean_p_when_improved,

    "mean_p_improve_when_actual_declined":
        mean_p_when_declined,

    "weather_input_semantics":
        (
            "Realized 2025 PTSC ambient trajectory; "
            "retrospective/oracle-style weather input. "
            "This validates the frozen inference chain, "
            "not weather forecast accuracy."
        ),

    "wait_semantics":
        (
            "Actual wait is not supplied to the model as a "
            "decision variable. A full inference curve is generated; "
            "the prediction is read retrospectively at the observed "
            "second-attempt timestamp."
        ),

    "strategy_recommendation":
        False,

    "queue_wait_prediction":
        False,
}


# ============================================================
# Save outputs
# ============================================================

RESULTS_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_rows_v1.csv"
)

MANIFEST_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_manifest_v1.csv"
)

METRICS_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_metrics_v1.json"
)

QA_OUT = (
    OUT /
    "external_regime_inference_backtest_2025_qa_v1.csv"
)

results_df.to_csv(
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

qa = (
    manifest_df[
        [
            "case_id",
            "driver_name",
            "car_number",
            "actual_wait_min",
            "status",
        ]
    ]
    .copy()
)

qa.to_csv(
    QA_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)

print(
    "2025 EXTERNAL-REGIME PRODUCTION INFERENCE BACKTEST"
)

print(
    "=" * 170
)

print(
    "Production core: FROZEN 2020–2024"
)

print(
    "Test regime: 2025 Aeroscreen + Hybrid"
)

print(
    "Weather input: REALIZED PTSC trajectory"
)

print(
    "Queue-wait prediction: False"
)

print(
    "Strategy recommendation: False"
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

status_summary = (
    manifest_df[
        "status"
    ]
    .value_counts(
        dropna=False
    )
    .rename_axis(
        "status"
    )
    .reset_index(
        name="rows"
    )
)

print(
    status_summary.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)

print(
    "PART 2 — INCLUDED HISTORICAL CASES"
)

print(
    "=" * 170
)

print(
    results_df[
        [
            "case_id",
            "driver_name",
            "car_number",
            "actual_wait_min",
            "before_speed_mph",
            "after_speed_mph",
            "actual_delta_speed_mph",
            "model_expected_delta_speed_mph",
            "p_improve",
            "absolute_error_mph",
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
    "PART 3 — AGGREGATE METRICS"
)

print(
    "=" * 170
)

for key in [
    "included_cases",
    "excluded_cases",
    "mae_mph",
    "median_absolute_error_mph",
    "rmse_mph",
    "direction_accuracy",
    "coverage_80",
    "coverage_90",
    "actual_improvement_rate",
    "mean_predicted_p_improve",
    "mean_p_improve_when_actual_improved",
    "mean_p_improve_when_actual_declined",
]:
    print(
        f"{key}: {metrics[key]}"
    )


print(
    "\n" + "=" * 170
)

print(
    "PART 4 — EXCLUDED CASES"
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
                "car_number",
                "actual_wait_min",
                "status",
            ]
        ].to_string(
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
    QA_OUT,
]:

    print(
        pth.relative_to(
            ROOT
        )
    )

print(
    "\nEXTERNAL_REGIME_INFERENCE_BACKTEST_2025_V1_COMPLETE"
)
