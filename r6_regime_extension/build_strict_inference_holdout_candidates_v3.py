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
    "strict_inference_holdout_candidates_v3"
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

TIMING_GENERAL = (
    ROOT /
    "weather/output/"
    "performance_grade_attempt_timing.csv"
)

TIMING_2024 = (
    ROOT /
    "weather/output/"
    "performance_grade_attempt_timing_2024_supported.csv"
)

ENV_GENERAL = (
    ROOT /
    "weather/output/"
    "performance_grade_attempt_realized_environment.csv"
)

ENV_2024 = (
    ROOT /
    "weather/output/"
    "performance_grade_attempt_realized_environment_2024_supported.csv"
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

MAX_HORIZON_MIN = 120.0

MAX_HRRR_EDGE_DISTANCE_MIN = 30.0


# ============================================================
# Helpers
# ============================================================

def boolish(
    x
):

    if isinstance(
        x,
        bool
    ):
        return x

    if pd.isna(
        x
    ):
        return False

    s = str(
        x
    ).strip().lower()

    return s in {
        "true",
        "1",
        "yes",
        "y",
        "pass",
        "usable",
    }


def clean_driver(
    x
):

    if pd.isna(
        x
    ):
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(
            x
        ).lower()
    )


def clean_car(
    x
):

    if pd.isna(
        x
    ):
        return ""

    s = str(
        x
    ).strip().upper()

    if re.fullmatch(
        r"\d+\.0+",
        s
    ):

        s = str(
            int(
                float(
                    s
                )
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

    try:

        return f"{float(x):.3f}"

    except Exception:

        return ""


def pair_signature(
    year,
    car,
    driver,
    before_speed,
    after_speed,
):

    return "|".join([
        str(
            int(
                year
            )
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


def load_if_exists(
    path
):

    if not path.exists():

        return pd.DataFrame()

    return pd.read_csv(
        path,
        low_memory=False
    )


# ============================================================
# Load transition universe
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
    "pair_signature"
] = u.apply(
    lambda r:
        pair_signature(
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
# Lineage gates
# ============================================================

def transition_id_set(
    path
):

    df = load_if_exists(
        path
    )

    if (
        df.empty
        or
        "transition_id"
        not in df.columns
    ):

        return set()

    return set(
        df[
            "transition_id"
        ]
        .dropna()
        .astype(str)
    )


frozen_ids = transition_id_set(
    FROZEN39
)

analysis_ids = transition_id_set(
    ANALYSIS42
)

rescued_ids = transition_id_set(
    RESCUED
)


u[
    "in_frozen39"
] = u[
    "transition_id"
].astype(
    str
).isin(
    frozen_ids
)

u[
    "in_analysis42"
] = u[
    "transition_id"
].astype(
    str
).isin(
    analysis_ids
)

u[
    "in_rescued_v2"
] = u[
    "transition_id"
].astype(
    str
).isin(
    rescued_ids
)


# ------------------------------------------------------------
# Quarantine by pair signature
# ------------------------------------------------------------

quarantine_signatures = set()

q = load_if_exists(
    QUARANTINE
)

if not q.empty:

    for _, r in q.iterrows():

        quarantine_signatures.add(
            pair_signature(
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
    quarantine_signatures
)


# ------------------------------------------------------------
# Previous rescued-case backtest
# ------------------------------------------------------------

backtest_signatures = set()

b = load_if_exists(
    BACKTEST
)

if not b.empty:

    for _, r in b.iterrows():

        backtest_signatures.add(
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

    return (
        key
        in
        backtest_signatures
    )


u[
    "already_backtested"
] = u.apply(
    already_backtested,
    axis=1
)

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
# Build canonical attempt timing table
# ============================================================

timing_frames = []

for path, source in [
    (
        TIMING_GENERAL,
        "GENERAL"
    ),
    (
        TIMING_2024,
        "SUPPORTED_2024"
    ),
]:

    df = load_if_exists(
        path
    )

    if df.empty:
        continue

    if (
        "attempt_id"
        not in df.columns
        or
        "mapped_capture_time_utc"
        not in df.columns
    ):

        continue

    temp = df.copy()

    temp[
        "_timing_source"
    ] = source

    temp[
        "_timestamp"
    ] = pd.to_datetime(
        temp[
            "mapped_capture_time_utc"
        ],
        utc=True,
        errors="coerce"
    )

    if "chronology_usable" in temp.columns:

        temp[
            "_chronology_usable"
        ] = temp[
            "chronology_usable"
        ].map(
            boolish
        )

    else:

        temp[
            "_chronology_usable"
        ] = temp[
            "_timestamp"
        ].notna()

    if "performance_alignment_usable" in temp.columns:

        temp[
            "_performance_alignment_usable"
        ] = temp[
            "performance_alignment_usable"
        ].map(
            boolish
        )

    else:

        temp[
            "_performance_alignment_usable"
        ] = True

    timing_frames.append(
        temp
    )


timing = pd.concat(
    timing_frames,
    ignore_index=True
)

timing = timing[
    timing[
        "_timestamp"
    ].notna()
].copy()

# Prefer explicitly supported 2024 row when duplicate attempt_id exists.
timing[
    "_source_priority"
] = timing[
    "_timing_source"
].map({
    "SUPPORTED_2024":
        0,

    "GENERAL":
        1,
}).fillna(
    9
)

timing = (
    timing
    .sort_values(
        [
            "attempt_id",
            "_source_priority",
        ]
    )
    .drop_duplicates(
        subset=[
            "attempt_id"
        ],
        keep="first"
    )
    .reset_index(
        drop=True
    )
)


timing_lookup = (
    timing.set_index(
        "attempt_id"
    )
)


# ============================================================
# Build canonical realized-environment table
# ============================================================

env_frames = []

for path, source in [
    (
        ENV_GENERAL,
        "GENERAL"
    ),
    (
        ENV_2024,
        "SUPPORTED_2024"
    ),
]:

    df = load_if_exists(
        path
    )

    if df.empty:
        continue

    if "attempt_id" not in df.columns:
        continue

    temp = df.copy()

    temp[
        "_env_source"
    ] = source

    if "ptsc_track_c" in temp.columns:

        temp[
            "_track_c"
        ] = pd.to_numeric(
            temp[
                "ptsc_track_c"
            ],
            errors="coerce"
        )

    else:

        temp[
            "_track_c"
        ] = np.nan

    if "ptsc_ambient_c" in temp.columns:

        temp[
            "_ambient_c"
        ] = pd.to_numeric(
            temp[
                "ptsc_ambient_c"
            ],
            errors="coerce"
        )

    else:

        temp[
            "_ambient_c"
        ] = np.nan

    if "ptsc_alignment_status" in temp.columns:

        temp[
            "_ptsc_alignment_status"
        ] = temp[
            "ptsc_alignment_status"
        ].astype(
            str
        )

    else:

        temp[
            "_ptsc_alignment_status"
        ] = ""

    if "ptsc_gap_minutes" in temp.columns:

        temp[
            "_ptsc_gap_minutes"
        ] = pd.to_numeric(
            temp[
                "ptsc_gap_minutes"
            ],
            errors="coerce"
        )

    else:

        temp[
            "_ptsc_gap_minutes"
        ] = np.nan

    env_frames.append(
        temp
    )


env = pd.concat(
    env_frames,
    ignore_index=True
)

env[
    "_source_priority"
] = env[
    "_env_source"
].map({
    "SUPPORTED_2024":
        0,

    "GENERAL":
        1,
}).fillna(
    9
)

env = (
    env
    .sort_values(
        [
            "attempt_id",
            "_source_priority",
        ]
    )
    .drop_duplicates(
        subset=[
            "attempt_id"
        ],
        keep="first"
    )
    .reset_index(
        drop=True
    )
)

env_lookup = env.set_index(
    "attempt_id"
)


# ============================================================
# Join timing / start environment to transitions
# ============================================================

def timing_value(
    attempt_id,
    field
):

    if (
        pd.isna(
            attempt_id
        )
        or
        attempt_id
        not in timing_lookup.index
    ):

        return np.nan

    return timing_lookup.loc[
        attempt_id,
        field
    ]


def env_value(
    attempt_id,
    field
):

    if (
        pd.isna(
            attempt_id
        )
        or
        attempt_id
        not in env_lookup.index
    ):

        return np.nan

    return env_lookup.loc[
        attempt_id,
        field
    ]


u[
    "before_time_joined_utc"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        timing_value(
            x,
            "_timestamp"
        )
)

u[
    "after_time_joined_utc"
] = u[
    "after_attempt_id"
].map(
    lambda x:
        timing_value(
            x,
            "_timestamp"
        )
)

u[
    "before_chronology_usable"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        timing_value(
            x,
            "_chronology_usable"
        )
)

u[
    "after_chronology_usable"
] = u[
    "after_attempt_id"
].map(
    lambda x:
        timing_value(
            x,
            "_chronology_usable"
        )
)

u[
    "before_timing_source"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        timing_value(
            x,
            "_timing_source"
        )
)

u[
    "after_timing_source"
] = u[
    "after_attempt_id"
].map(
    lambda x:
        timing_value(
            x,
            "_timing_source"
        )
)

u[
    "start_track_c"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        env_value(
            x,
            "_track_c"
        )
)

u[
    "start_ambient_c"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        env_value(
            x,
            "_ambient_c"
        )
)

u[
    "start_ptsc_status"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        env_value(
            x,
            "_ptsc_alignment_status"
        )
)

u[
    "start_ptsc_gap_minutes"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        env_value(
            x,
            "_ptsc_gap_minutes"
        )
)

u[
    "start_env_source"
] = u[
    "before_attempt_id"
].map(
    lambda x:
        env_value(
            x,
            "_env_source"
        )
)


u[
    "actual_wait_min"
] = (
    (
        u[
            "after_time_joined_utc"
        ]
        -
        u[
            "before_time_joined_utc"
        ]
    )
    .dt.total_seconds()
    /
    60.0
)


# ============================================================
# HRRR future trajectory coverage
# ============================================================

hrrr = pd.read_csv(
    HRRR,
    low_memory=False
)

if "valid_time_utc" not in hrrr.columns:

    raise RuntimeError(
        "Expected HRRR valid_time_utc column missing."
    )

if "temp_c" not in hrrr.columns:

    raise RuntimeError(
        "Expected HRRR temp_c column missing."
    )

hrrr[
    "_time"
] = pd.to_datetime(
    hrrr[
        "valid_time_utc"
    ],
    utc=True,
    errors="coerce"
)

hrrr[
    "_ambient"
] = pd.to_numeric(
    hrrr[
        "temp_c"
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


def assess_hrrr(
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
            "hrrr_rows_between":
                0,

            "hrrr_start_distance_min":
                np.nan,

            "hrrr_end_distance_min":
                np.nan,

            "hrrr_covers_actual_wait":
                False,
        }

    g = hrrr[
        hrrr[
            "_time"
        ].dt.year
        ==
        start.year
    ].copy()

    if g.empty:

        return {
            "hrrr_rows_between":
                0,

            "hrrr_start_distance_min":
                np.nan,

            "hrrr_end_distance_min":
                np.nan,

            "hrrr_covers_actual_wait":
                False,
        }

    start_distance = (
        g[
            "_time"
        ]
        -
        start
    ).abs().dt.total_seconds() / 60.0

    end_distance = (
        g[
            "_time"
        ]
        -
        end
    ).abs().dt.total_seconds() / 60.0

    between = g[
        (
            g[
                "_time"
            ]
            >=
            start
        )
        &
        (
            g[
                "_time"
            ]
            <=
            end
        )
    ]

    start_min = float(
        start_distance.min()
    )

    end_min = float(
        end_distance.min()
    )

    usable = (
        start_min
        <=
        MAX_HRRR_EDGE_DISTANCE_MIN
        and
        end_min
        <=
        MAX_HRRR_EDGE_DISTANCE_MIN
        and
        len(
            between
        )
        >= 2
    )

    return {
        "hrrr_rows_between":
            int(
                len(
                    between
                )
            ),

        "hrrr_start_distance_min":
            start_min,

        "hrrr_end_distance_min":
            end_min,

        "hrrr_covers_actual_wait":
            bool(
                usable
            ),
    }


hrrr_audit = u.apply(
    lambda r:
        pd.Series(
            assess_hrrr(
                r[
                    "before_time_joined_utc"
                ],
                r[
                    "after_time_joined_utc"
                ],
            )
        ),
    axis=1
)

u = pd.concat(
    [
        u,
        hrrr_audit,
    ],
    axis=1
)


# ============================================================
# Eligibility
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
    "has_joined_chronology"
] = (
    u[
        "before_time_joined_utc"
    ].notna()
    &
    u[
        "after_time_joined_utc"
    ].notna()
)

u[
    "chronology_marked_usable"
] = (
    u[
        "before_chronology_usable"
    ].map(
        boolish
    )
    &
    u[
        "after_chronology_usable"
    ].map(
        boolish
    )
)

u[
    "wait_positive"
] = (
    u[
        "actual_wait_min"
    ]
    >
    0
)

u[
    "within_120_min"
] = (
    u[
        "actual_wait_min"
    ].between(
        0.0001,
        MAX_HORIZON_MIN,
        inclusive="both"
    )
)

u[
    "has_start_track"
] = u[
    "start_track_c"
].notna()

u[
    "has_start_ambient"
] = u[
    "start_ambient_c"
].notna()


# ============================================================
# Classification
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
        "has_joined_chronology"
    ]:

        return (
            "TIMING_JOIN_INCOMPLETE"
        )

    if not r[
        "chronology_marked_usable"
    ]:

        return (
            "TIMING_PRESENT_NOT_USABLE"
        )

    if not r[
        "wait_positive"
    ]:

        return (
            "INVALID_CHRONOLOGY_ORDER"
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
        "hrrr_covers_actual_wait"
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
    "strict_inference_holdout_audit_v3.csv"
)

READY_OUT = (
    OUT /
    "strict_inference_holdout_ready_v3.csv"
)

SUMMARY_OUT = (
    OUT /
    "strict_inference_holdout_summary_v3.csv"
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
    "PART 1 — ATTEMPT TIMING JOIN COVERAGE"
)
print(
    "=" * 170
)

coverage = (
    u.groupby(
        "year"
    )
    .agg(
        transitions=(
            "transition_id",
            "size"
        ),

        before_time_joined=(
            "before_time_joined_utc",
            lambda x:
                int(
                    x.notna().sum()
                )
        ),

        after_time_joined=(
            "after_time_joined_utc",
            lambda x:
                int(
                    x.notna().sum()
                )
        ),

        both_time_joined=(
            "has_joined_chronology",
            "sum"
        ),

        usable_chronology=(
            "chronology_marked_usable",
            "sum"
        ),

        start_track=(
            "has_start_track",
            "sum"
        ),

        start_ambient=(
            "has_start_ambient",
            "sum"
        ),
    )
    .reset_index()
)

print(
    coverage.to_string(
        index=False
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

    print(
        ready[
            [
                "transition_id",
                "year",
                "car_number",
                "driver_name",
                "before_speed",
                "after_speed",
                "actual_delta_speed_mph",
                "before_time_joined_utc",
                "after_time_joined_utc",
                "actual_wait_min",
                "start_track_c",
                "start_ambient_c",
                "before_timing_source",
                "after_timing_source",
                "start_env_source",
                "hrrr_rows_between",
                "hrrr_start_distance_min",
                "hrrr_end_distance_min",
            ]
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
    "PART 4 — CLEAN HOLDOUTS BLOCKED BY ONE OR MORE GATES"
)
print(
    "=" * 170
)

blocked = u[
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

if blocked.empty:

    print(
        "NONE"
    )

else:

    print(
        blocked[
            [
                "year",
                "car_number",
                "driver_name",
                "before_attempt_id",
                "after_attempt_id",
                "before_time_joined_utc",
                "after_time_joined_utc",
                "actual_wait_min",
                "start_track_c",
                "start_ambient_c",
                "hrrr_covers_actual_wait",
                "holdout_status",
            ]
        ]
        .sort_values(
            [
                "year",
                "holdout_status",
                "driver_name",
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
    "\nSTRICT_INFERENCE_HOLDOUT_CANDIDATES_V3_COMPLETE"
)
