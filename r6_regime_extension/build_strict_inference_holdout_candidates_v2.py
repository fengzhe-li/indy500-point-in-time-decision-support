from pathlib import Path
import re
import numpy as np
import pandas as pd


ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "strict_inference_holdout_candidates_v2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# Core datasets
# ============================================================

UNIVERSE = (
    ROOT /
    "r5_1/output/"
    "day1_same_car_repeat_inventory_v1.csv"
)

FROZEN39 = (
    ROOT /
    "r5/frozen_inputs/day1/"
    "day1_environment_linked_transitions_39_FROZEN.csv"
)

ANALYSIS42 = (
    ROOT /
    "r5_2/manual/"
    "r5_2_repeat_analysis_set_v1.csv"
)

RESCUED = (
    ROOT /
    "r5_2/manual/"
    "rescued_repeat_physical_transitions_v2.csv"
)

QUARANTINE = (
    ROOT /
    "r5_2/manual/"
    "rescued_repeat_transition_quarantine_v2.csv"
)

BACKTEST = (
    ROOT /
    "r5_2/manual/"
    "final_engine_rescued_case_backtest_v1.csv"
)

HRRR = (
    ROOT /
    "weather/output/"
    "hrrr_ims_2020_2024_features.csv"
)

TARGET_YEARS = {
    2022,
    2024,
}

MAX_INFERENCE_HORIZON_MIN = 120.0

# for historical forecast interpolation
MAX_FORECAST_EDGE_DISTANCE_MIN = 30.0


# ============================================================
# Helpers
# ============================================================

def num(
    x
):
    return pd.to_numeric(
        pd.Series([x]),
        errors="coerce"
    ).iloc[0]


def clean_driver(
    x
):

    if pd.isna(x):
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(x).lower()
    )


def clean_car(
    x
):

    if pd.isna(x):
        return ""

    s = str(x).strip().upper()

    if re.fullmatch(
        r"\d+\.0+",
        s
    ):
        s = str(
            int(
                float(s)
            )
        )

    return re.sub(
        r"[^A-Z0-9]",
        "",
        s
    )


def speed_key(
    x
):

    v = num(
        x
    )

    if pd.isna(v):
        return ""

    return f"{float(v):.3f}"


def pair_key(
    year,
    car,
    driver,
    before_speed,
    after_speed,
):

    return "|".join([
        str(
            int(year)
        ),
        clean_car(
            car
        ),
        clean_driver(
            driver
        ),
        speed_key(
            before_speed
        ),
        speed_key(
            after_speed
        ),
    ])


def first_existing(
    row,
    names,
):

    for name in names:

        if name in row.index:

            value = row[
                name
            ]

            if pd.notna(
                value
            ):
                return value

    return np.nan


def detect_hrrr_timestamp_column(
    df
):

    preferred = [
        "valid_time_utc",
        "timestamp_utc",
        "datetime_utc",
        "time_utc",
        "forecast_time_utc",
        "valid_time",
        "timestamp",
        "datetime",
    ]

    for c in preferred:

        if c in df.columns:
            return c

    for c in df.columns:

        s = str(
            c
        ).lower()

        if (
            "time" in s
            or
            "date" in s
        ):

            parsed = pd.to_datetime(
                df[c],
                utc=True,
                errors="coerce"
            )

            if parsed.notna().sum() >= 50:
                return c

    return None


def detect_hrrr_temp_column(
    df
):

    preferred = [
        "air_temp_c",
        "temperature_c",
        "temp_c",
        "forecast_temp_c",
        "forecast_air_temp_c",
        "TMP_2maboveground",
    ]

    for c in preferred:

        if c in df.columns:
            return c

    candidates = []

    for c in df.columns:

        s = str(
            c
        ).lower()

        if (
            (
                "temp" in s
                or
                "tmp" in s
            )
            and
            "dew" not in s
            and
            "track" not in s
        ):

            vals = pd.to_numeric(
                df[c],
                errors="coerce"
            )

            if vals.notna().sum() >= 50:

                candidates.append(
                    c
                )

    return (
        candidates[0]
        if candidates
        else None
    )


# ============================================================
# Load universe
# ============================================================

u = pd.read_csv(
    UNIVERSE,
    low_memory=False
)

u = u[
    u[
        "year"
    ].isin(
        TARGET_YEARS
    )
].copy()

u[
    "before_time_parsed"
] = pd.to_datetime(
    u[
        "before_time_utc"
    ],
    utc=True,
    errors="coerce"
)

u[
    "after_time_parsed"
] = pd.to_datetime(
    u[
        "after_time_utc"
    ],
    utc=True,
    errors="coerce"
)

u[
    "before_speed"
] = pd.to_numeric(
    u[
        "before_four_lap_average_speed_mph"
    ],
    errors="coerce"
)

u[
    "after_speed"
] = pd.to_numeric(
    u[
        "after_four_lap_average_speed_mph"
    ],
    errors="coerce"
)

u[
    "actual_delta_speed_mph"
] = (
    u[
        "after_speed"
    ]
    -
    u[
        "before_speed"
    ]
)

u[
    "actual_wait_min"
] = (
    (
        u[
            "after_time_parsed"
        ]
        -
        u[
            "before_time_parsed"
        ]
    )
    .dt.total_seconds()
    /
    60.0
)


# ============================================================
# Starting physical state
# ============================================================

def get_before_track(
    r
):

    return first_existing(
        r,
        [
            "before_ptsc_track_c",
            "previous_track_temp_c",
        ]
    )


def get_before_ambient(
    r
):

    return first_existing(
        r,
        [
            "before_ptsc_ambient_c",
            "previous_air_temp_c",
            "before_forecast_temp_c",
        ]
    )


u[
    "inference_current_track_c"
] = u.apply(
    get_before_track,
    axis=1
)

u[
    "inference_current_ambient_c"
] = u.apply(
    get_before_ambient,
    axis=1
)

u[
    "inference_current_track_c"
] = pd.to_numeric(
    u[
        "inference_current_track_c"
    ],
    errors="coerce"
)

u[
    "inference_current_ambient_c"
] = pd.to_numeric(
    u[
        "inference_current_ambient_c"
    ],
    errors="coerce"
)


# ============================================================
# Pair signatures
# ============================================================

u[
    "pair_signature"
] = u.apply(
    lambda r:
        pair_key(
            r[
                "year"
            ],
            r[
                "car_number"
            ],
            r[
                "driver_name"
            ],
            r[
                "before_speed"
            ],
            r[
                "after_speed"
            ],
        ),
    axis=1
)


# ============================================================
# Exact transition-id lineage
# ============================================================

def transition_ids_from(
    path
):

    if not path.exists():
        return set()

    df = pd.read_csv(
        path,
        low_memory=False
    )

    if "transition_id" not in df.columns:
        return set()

    return set(
        df[
            "transition_id"
        ]
        .dropna()
        .astype(str)
    )


frozen_ids = transition_ids_from(
    FROZEN39
)

analysis_ids = transition_ids_from(
    ANALYSIS42
)

rescued_ids = transition_ids_from(
    RESCUED
)


u[
    "in_frozen39"
] = (
    u[
        "transition_id"
    ]
    .astype(str)
    .isin(
        frozen_ids
    )
)

u[
    "in_analysis42"
] = (
    u[
        "transition_id"
    ]
    .astype(str)
    .isin(
        analysis_ids
    )
)

u[
    "in_rescued_v2"
] = (
    u[
        "transition_id"
    ]
    .astype(str)
    .isin(
        rescued_ids
    )
)


# ============================================================
# Quarantine pair signatures
# ============================================================

quarantine_keys = set()

if QUARANTINE.exists():

    q = pd.read_csv(
        QUARANTINE,
        low_memory=False
    )

    for _, r in q.iterrows():

        quarantine_keys.add(
            pair_key(
                r[
                    "year"
                ],
                r[
                    "car_number"
                ],
                r[
                    "driver_name"
                ],
                r[
                    "before_speed_mph"
                ],
                r[
                    "after_speed_mph"
                ],
            )
        )


u[
    "in_quarantine"
] = u[
    "pair_signature"
].isin(
    quarantine_keys
)


# ============================================================
# Previous rescued-case backtest
# ============================================================

backtest_keys = set()

if BACKTEST.exists():

    b = pd.read_csv(
        BACKTEST,
        low_memory=False
    )

    for _, r in b.iterrows():

        backtest_keys.add(
            (
                int(
                    r[
                        "year"
                    ]
                ),
                clean_driver(
                    r[
                        "driver_name"
                    ]
                ),
                speed_key(
                    r[
                        "before_speed_mph"
                    ]
                ),
                speed_key(
                    r[
                        "after_speed_mph"
                    ]
                ),
            )
        )


def already_backtested(
    r
):

    key = (
        int(
            r[
                "year"
            ]
        ),
        clean_driver(
            r[
                "driver_name"
            ]
        ),
        speed_key(
            r[
                "before_speed"
            ]
        ),
        speed_key(
            r[
                "after_speed"
            ]
        ),
    )

    return key in backtest_keys


u[
    "already_backtested"
] = u.apply(
    already_backtested,
    axis=1
)


# ============================================================
# HRRR inventory
# ============================================================

hrrr = pd.read_csv(
    HRRR,
    low_memory=False
)

hrrr_time_col = (
    detect_hrrr_timestamp_column(
        hrrr
    )
)

hrrr_temp_col = (
    detect_hrrr_temp_column(
        hrrr
    )
)

if hrrr_time_col is None:

    raise RuntimeError(
        "Could not detect HRRR timestamp column."
    )

if hrrr_temp_col is None:

    raise RuntimeError(
        "Could not detect HRRR ambient temperature column."
    )


hrrr[
    "_time"
] = pd.to_datetime(
    hrrr[
        hrrr_time_col
    ],
    utc=True,
    errors="coerce"
)

hrrr[
    "_ambient"
] = pd.to_numeric(
    hrrr[
        hrrr_temp_col
    ],
    errors="coerce"
)

hrrr = hrrr[
    hrrr[
        "_time"
    ].notna()
    &
    hrrr[
        "_ambient"
    ].notna()
].copy()

hrrr = (
    hrrr
    .sort_values(
        "_time"
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# Forecast coverage function
# ============================================================

def assess_forecast(
    start,
    end
):

    if (
        pd.isna(
            start
        )
        or
        pd.isna(
            end
        )
    ):

        return {
            "forecast_rows":
                0,

            "forecast_start_distance_min":
                np.nan,

            "forecast_end_distance_min":
                np.nan,

            "forecast_covers_actual_wait":
                False,
        }

    year_rows = hrrr[
        hrrr[
            "_time"
        ].dt.year
        ==
        start.year
    ].copy()

    if year_rows.empty:

        return {
            "forecast_rows":
                0,

            "forecast_start_distance_min":
                np.nan,

            "forecast_end_distance_min":
                np.nan,

            "forecast_covers_actual_wait":
                False,
        }

    start_dist = (
        year_rows[
            "_time"
        ]
        -
        start
    ).abs().dt.total_seconds() / 60.0

    end_dist = (
        year_rows[
            "_time"
        ]
        -
        end
    ).abs().dt.total_seconds() / 60.0

    nearest_start = float(
        start_dist.min()
    )

    nearest_end = float(
        end_dist.min()
    )

    between = year_rows[
        (
            year_rows[
                "_time"
            ]
            >=
            start
        )
        &
        (
            year_rows[
                "_time"
            ]
            <=
            end
        )
    ]

    covered = (
        nearest_start
        <=
        MAX_FORECAST_EDGE_DISTANCE_MIN
        and
        nearest_end
        <=
        MAX_FORECAST_EDGE_DISTANCE_MIN
        and
        len(
            between
        )
        >= 2
    )

    return {
        "forecast_rows":
            int(
                len(
                    between
                )
            ),

        "forecast_start_distance_min":
            nearest_start,

        "forecast_end_distance_min":
            nearest_end,

        "forecast_covers_actual_wait":
            bool(
                covered
            ),
    }


forecast_audit = u.apply(
    lambda r:
        pd.Series(
            assess_forecast(
                r[
                    "before_time_parsed"
                ],
                r[
                    "after_time_parsed"
                ],
            )
        ),
    axis=1
)

u = pd.concat(
    [
        u,
        forecast_audit,
    ],
    axis=1
)


# ============================================================
# Eligibility dimensions
# ============================================================

u[
    "has_real_outcome"
] = (
    u[
        "before_speed"
    ].notna()
    &
    u[
        "after_speed"
    ].notna()
)

u[
    "has_exact_chronology"
] = (
    u[
        "before_time_parsed"
    ].notna()
    &
    u[
        "after_time_parsed"
    ].notna()
    &
    (
        u[
            "actual_wait_min"
        ]
        >
        0
    )
)

u[
    "within_120_min"
] = (
    u[
        "actual_wait_min"
    ]
    .between(
        0.0001,
        MAX_INFERENCE_HORIZON_MIN,
        inclusive="both"
    )
)

u[
    "has_start_track"
] = u[
    "inference_current_track_c"
].notna()

u[
    "has_start_ambient"
] = u[
    "inference_current_ambient_c"
].notna()

u[
    "lineage_clean"
] = ~(
    u[
        "in_frozen39"
    ]
    |
    u[
        "in_analysis42"
    ]
    |
    u[
        "in_rescued_v2"
    ]
    |
    u[
        "in_quarantine"
    ]
    |
    u[
        "already_backtested"
    ]
)


# ============================================================
# Final readiness classification
# ============================================================

def classify(
    r
):

    if not r[
        "lineage_clean"
    ]:

        return (
            "MODEL_TOUCHED_OR_QUARANTINED"
        )

    if not r[
        "has_real_outcome"
    ]:

        return (
            "MISSING_REAL_OUTCOME"
        )

    if not r[
        "has_exact_chronology"
    ]:

        return (
            "MISSING_EXACT_CHRONOLOGY"
        )

    if not r[
        "within_120_min"
    ]:

        return (
            "OUTSIDE_120_MIN_HORIZON"
        )

    if not r[
        "has_start_track"
    ]:

        return (
            "MISSING_START_TRACK_TEMP"
        )

    if not r[
        "has_start_ambient"
    ]:

        return (
            "MISSING_START_AMBIENT"
        )

    if not r[
        "forecast_covers_actual_wait"
    ]:

        return (
            "INSUFFICIENT_HRRR_TRAJECTORY"
        )

    return (
        "STRICT_HOLDOUT_READY"
    )


u[
    "holdout_status"
] = u.apply(
    classify,
    axis=1
)


# ============================================================
# Save
# ============================================================

FULL_OUT = (
    OUT /
    "strict_inference_holdout_audit_v2.csv"
)

READY_OUT = (
    OUT /
    "strict_inference_holdout_ready_v2.csv"
)

SUMMARY_OUT = (
    OUT /
    "strict_inference_holdout_summary_v2.csv"
)

u.to_csv(
    FULL_OUT,
    index=False
)

ready = u[
    u[
        "holdout_status"
    ]
    ==
    "STRICT_HOLDOUT_READY"
].copy()

ready.to_csv(
    READY_OUT,
    index=False
)

summary = (
    u.groupby(
        [
            "year",
            "holdout_status",
        ]
    )
    .size()
    .rename(
        "rows"
    )
    .reset_index()
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)
print(
    "PART 1 — HRRR DETECTION"
)
print(
    "=" * 170
)

print(
    "timestamp column:",
    hrrr_time_col
)

print(
    "ambient column:",
    hrrr_temp_col
)

print(
    "usable HRRR rows:",
    len(
        hrrr
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 2 — HOLDOUT STATUS SUMMARY"
)
print(
    "=" * 170
)

print(
    summary.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 3 — STRICT HOLDOUT READY"
)
print(
    "=" * 170
)

if ready.empty:

    print(
        "NONE"
    )

else:

    cols = [
        "transition_id",
        "year",
        "car_number",
        "driver_name",
        "before_speed",
        "after_speed",
        "actual_delta_speed_mph",
        "before_time_parsed",
        "after_time_parsed",
        "actual_wait_min",
        "inference_current_track_c",
        "inference_current_ambient_c",
        "forecast_rows",
        "forecast_start_distance_min",
        "forecast_end_distance_min",
    ]

    print(
        ready[
            cols
        ]
        .sort_values(
            [
                "year",
                "actual_wait_min",
            ]
        )
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 170
)
print(
    "PART 4 — CLEAN BUT NOT READY"
)
print(
    "=" * 170
)

clean_not_ready = u[
    (
        u[
            "lineage_clean"
        ]
    )
    &
    (
        u[
            "holdout_status"
        ]
        !=
        "STRICT_HOLDOUT_READY"
    )
].copy()

if clean_not_ready.empty:

    print(
        "NONE"
    )

else:

    print(
        clean_not_ready[
            [
                "transition_id",
                "year",
                "car_number",
                "driver_name",
                "actual_wait_min",
                "has_real_outcome",
                "has_exact_chronology",
                "within_120_min",
                "has_start_track",
                "has_start_ambient",
                "forecast_covers_actual_wait",
                "holdout_status",
            ]
        ]
        .sort_values(
            [
                "year",
                "holdout_status",
            ]
        )
        .to_string(
            index=False
        )
    )


print(
    "\nOUTPUTS:"
)

for p in [
    FULL_OUT,
    READY_OUT,
    SUMMARY_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nSTRICT_INFERENCE_HOLDOUT_CANDIDATES_V2_COMPLETE"
)
