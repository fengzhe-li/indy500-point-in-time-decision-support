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
    "holdout_attempt_identity_reconciliation_v4"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

UNIVERSE = (
    ROOT /
    "r5_1/output/"
    "day1_same_car_repeat_inventory_v1.csv"
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

TARGET_YEARS = {
    2022,
    2024,
}


def clean_driver(x):

    if pd.isna(x):
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(x).lower()
    )


def clean_car(x):

    if pd.isna(x):
        return ""

    s = str(x).strip().upper()

    try:
        if re.fullmatch(
            r"\d+\.0+",
            s
        ):
            s = str(
                int(
                    float(s)
                )
            )
    except Exception:
        pass

    return re.sub(
        r"[^A-Z0-9]",
        "",
        s
    )


# ============================================================
# Load repeat universe endpoints
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

endpoint_rows = []

for _, r in u.iterrows():

    for side in [
        "before",
        "after",
    ]:

        endpoint_rows.append({
            "transition_id":
                r[
                    "transition_id"
                ],

            "year":
                int(
                    r[
                        "year"
                    ]
                ),

            "side":
                side,

            "car_number":
                r[
                    "car_number"
                ],

            "driver_name":
                r[
                    "driver_name"
                ],

            "car_key":
                clean_car(
                    r[
                        "car_number"
                    ]
                ),

            "driver_key":
                clean_driver(
                    r[
                        "driver_name"
                    ]
                ),

            "run_index":
                pd.to_numeric(
                    r[
                        f"{side}_run_index"
                    ],
                    errors="coerce"
                ),

            "inventory_attempt_id":
                r[
                    f"{side}_attempt_id"
                ],

            "speed_mph":
                pd.to_numeric(
                    r[
                        (
                            "before_four_lap_average_speed_mph"
                            if side == "before"
                            else
                            "after_four_lap_average_speed_mph"
                        )
                    ],
                    errors="coerce"
                ),
        })


endpoints = pd.DataFrame(
    endpoint_rows
)


# ============================================================
# Load realized environment attempt-level rows
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

    if not path.exists():
        continue

    df = pd.read_csv(
        path,
        low_memory=False
    )

    if "year" not in df.columns:
        continue

    df = df[
        df[
            "year"
        ].isin(
            TARGET_YEARS
        )
    ].copy()

    df[
        "source"
    ] = source

    df[
        "car_key"
    ] = df[
        "car_number"
    ].map(
        clean_car
    )

    df[
        "driver_key"
    ] = df[
        "driver_name"
    ].map(
        clean_driver
    )

    df[
        "car_attempt_index_num"
    ] = pd.to_numeric(
        df[
            "car_attempt_index"
        ],
        errors="coerce"
    )

    df[
        "timestamp_utc"
    ] = pd.to_datetime(
        df[
            "mapped_capture_time_utc"
        ],
        utc=True,
        errors="coerce"
    )

    df[
        "track_c"
    ] = pd.to_numeric(
        df[
            "ptsc_track_c"
        ],
        errors="coerce"
    )

    df[
        "ambient_c"
    ] = pd.to_numeric(
        df[
            "ptsc_ambient_c"
        ],
        errors="coerce"
    )

    env_frames.append(
        df
    )


env = pd.concat(
    env_frames,
    ignore_index=True
)

# Prefer supported 2024 when duplicate semantic attempt exists.
env[
    "source_priority"
] = env[
    "source"
].map({
    "SUPPORTED_2024":
        0,

    "GENERAL":
        1,
}).fillna(
    9
)

env = env.sort_values(
    [
        "year",
        "car_key",
        "driver_key",
        "car_attempt_index_num",
        "source_priority",
    ]
).reset_index(
    drop=True
)


# ============================================================
# Test run-index offsets
# ============================================================

offset_results = []

for offset in [
    -2,
    -1,
    0,
    1,
    2,
]:

    matched = 0
    unique = 0
    ambiguous = 0

    detail_rows = []

    for _, ep in endpoints.iterrows():

        if pd.isna(
            ep[
                "run_index"
            ]
        ):
            continue

        target_index = (
            float(
                ep[
                    "run_index"
                ]
            )
            +
            offset
        )

        hits = env[
            (
                env[
                    "year"
                ]
                ==
                ep[
                    "year"
                ]
            )
            &
            (
                env[
                    "car_key"
                ]
                ==
                ep[
                    "car_key"
                ]
            )
            &
            (
                env[
                    "driver_key"
                ]
                ==
                ep[
                    "driver_key"
                ]
            )
            &
            (
                env[
                    "car_attempt_index_num"
                ]
                ==
                target_index
            )
        ].copy()

        # Deduplicate GENERAL/SUPPORTED duplicate of same attempt semantics
        if not hits.empty:

            hits = hits.sort_values(
                "source_priority"
            )

            semantic_subset = [
                c
                for c in [
                    "year",
                    "car_key",
                    "driver_key",
                    "car_attempt_index_num",
                    "timestamp_utc",
                ]
                if c in hits.columns
            ]

            hits = hits.drop_duplicates(
                subset=semantic_subset,
                keep="first"
            )

        n = len(
            hits
        )

        if n > 0:
            matched += 1

        if n == 1:
            unique += 1

        if n > 1:
            ambiguous += 1

        detail_rows.append({
            "offset":
                offset,

            "transition_id":
                ep[
                    "transition_id"
                ],

            "year":
                ep[
                    "year"
                ],

            "side":
                ep[
                    "side"
                ],

            "car_number":
                ep[
                    "car_number"
                ],

            "driver_name":
                ep[
                    "driver_name"
                ],

            "run_index":
                ep[
                    "run_index"
                ],

            "target_car_attempt_index":
                target_index,

            "match_count":
                n,
        })

    offset_results.append({
        "offset":
            offset,

        "total_endpoints":
            len(
                endpoints
            ),

        "matched_endpoints":
            matched,

        "unique_endpoints":
            unique,

        "ambiguous_endpoints":
            ambiguous,

        "coverage":
            (
                unique
                /
                len(
                    endpoints
                )
                if len(
                    endpoints
                )
                else 0
            ),
    })


offset_summary = pd.DataFrame(
    offset_results
)

best = offset_summary.sort_values(
    [
        "unique_endpoints",
        "ambiguous_endpoints",
    ],
    ascending=[
        False,
        True,
    ]
).iloc[0]

BEST_OFFSET = int(
    best[
        "offset"
    ]
)


# ============================================================
# Build canonical endpoint mapping using best offset
# ============================================================

mapping_rows = []

for _, ep in endpoints.iterrows():

    if pd.isna(
        ep[
            "run_index"
        ]
    ):

        mapping_rows.append({
            **ep.to_dict(),

            "selected_offset":
                BEST_OFFSET,

            "target_car_attempt_index":
                np.nan,

            "match_status":
                "NO_RUN_INDEX",
        })

        continue

    target_index = (
        float(
            ep[
                "run_index"
            ]
        )
        +
        BEST_OFFSET
    )

    hits = env[
        (
            env[
                "year"
            ]
            ==
            ep[
                "year"
            ]
        )
        &
        (
            env[
                "car_key"
            ]
            ==
            ep[
                "car_key"
            ]
        )
        &
        (
            env[
                "driver_key"
            ]
            ==
            ep[
                "driver_key"
            ]
        )
        &
        (
            env[
                "car_attempt_index_num"
            ]
            ==
            target_index
        )
    ].copy()

    if not hits.empty:

        hits = hits.sort_values(
            "source_priority"
        )

        hits = hits.drop_duplicates(
            subset=[
                "year",
                "car_key",
                "driver_key",
                "car_attempt_index_num",
                "timestamp_utc",
            ],
            keep="first"
        )

    if len(
        hits
    ) == 0:

        mapping_rows.append({
            **ep.to_dict(),

            "selected_offset":
                BEST_OFFSET,

            "target_car_attempt_index":
                target_index,

            "match_status":
                "NO_MATCH",
        })

        continue

    if len(
        hits
    ) > 1:

        mapping_rows.append({
            **ep.to_dict(),

            "selected_offset":
                BEST_OFFSET,

            "target_car_attempt_index":
                target_index,

            "match_status":
                "AMBIGUOUS",
        })

        continue

    hit = hits.iloc[
        0
    ]

    mapping_rows.append({
        **ep.to_dict(),

        "selected_offset":
            BEST_OFFSET,

        "target_car_attempt_index":
            target_index,

        "match_status":
            "UNIQUE_MATCH",

        "mapped_attempt_id":
            hit.get(
                "attempt_id",
                np.nan
            ),

        "mapped_timestamp_utc":
            hit.get(
                "timestamp_utc",
                pd.NaT
            ),

        "mapped_chronology_usable":
            hit.get(
                "chronology_usable",
                np.nan
            ),

        "mapped_performance_alignment_usable":
            hit.get(
                "performance_alignment_usable",
                np.nan
            ),

        "mapped_track_c":
            hit.get(
                "track_c",
                np.nan
            ),

        "mapped_ambient_c":
            hit.get(
                "ambient_c",
                np.nan
            ),

        "mapped_ptsc_status":
            hit.get(
                "ptsc_alignment_status",
                np.nan
            ),

        "mapped_ptsc_gap_minutes":
            hit.get(
                "ptsc_gap_minutes",
                np.nan
            ),

        "mapped_source":
            hit.get(
                "source",
                np.nan
            ),
    })


mapping = pd.DataFrame(
    mapping_rows
)


# ============================================================
# Pair-level QA
# ============================================================

pair_rows = []

for transition_id, g in mapping.groupby(
    "transition_id"
):

    before = g[
        g[
            "side"
        ]
        ==
        "before"
    ]

    after = g[
        g[
            "side"
        ]
        ==
        "after"
    ]

    if before.empty or after.empty:
        continue

    b = before.iloc[
        0
    ]

    a = after.iloc[
        0
    ]

    bt = pd.to_datetime(
        b.get(
            "mapped_timestamp_utc"
        ),
        utc=True,
        errors="coerce"
    )

    at = pd.to_datetime(
        a.get(
            "mapped_timestamp_utc"
        ),
        utc=True,
        errors="coerce"
    )

    wait_min = (
        (
            at
            -
            bt
        ).total_seconds()
        /
        60.0
        if (
            pd.notna(
                bt
            )
            and
            pd.notna(
                at
            )
        )
        else np.nan
    )

    pair_rows.append({
        "transition_id":
            transition_id,

        "year":
            int(
                b[
                    "year"
                ]
            ),

        "car_number":
            b[
                "car_number"
            ],

        "driver_name":
            b[
                "driver_name"
            ],

        "before_run_index":
            b[
                "run_index"
            ],

        "after_run_index":
            a[
                "run_index"
            ],

        "before_match_status":
            b[
                "match_status"
            ],

        "after_match_status":
            a[
                "match_status"
            ],

        "before_timestamp_utc":
            bt,

        "after_timestamp_utc":
            at,

        "actual_wait_min":
            wait_min,

        "before_track_c":
            b.get(
                "mapped_track_c"
            ),

        "before_ambient_c":
            b.get(
                "mapped_ambient_c"
            ),

        "before_source":
            b.get(
                "mapped_source"
            ),

        "after_source":
            a.get(
                "mapped_source"
            ),

        "both_unique":
            (
                b[
                    "match_status"
                ]
                ==
                "UNIQUE_MATCH"
                and
                a[
                    "match_status"
                ]
                ==
                "UNIQUE_MATCH"
            ),

        "positive_time_order":
            (
                pd.notna(
                    wait_min
                )
                and
                wait_min
                >
                0
            ),

        "within_120_min":
            (
                pd.notna(
                    wait_min
                )
                and
                0
                <
                wait_min
                <=
                120
            ),
    })


pairs = pd.DataFrame(
    pair_rows
)


# ============================================================
# Save
# ============================================================

OFFSET_OUT = (
    OUT /
    "attempt_index_offset_audit_v4.csv"
)

MAPPING_OUT = (
    OUT /
    "endpoint_identity_mapping_v4.csv"
)

PAIR_OUT = (
    OUT /
    "transition_identity_mapping_v4.csv"
)

offset_summary.to_csv(
    OFFSET_OUT,
    index=False
)

mapping.to_csv(
    MAPPING_OUT,
    index=False
)

pairs.to_csv(
    PAIR_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)
print(
    "PART 1 — RUN INDEX OFFSET AUDIT"
)
print(
    "=" * 170
)

print(
    offset_summary.to_string(
        index=False
    )
)

print(
    "\nSELECTED OFFSET =",
    BEST_OFFSET
)


print(
    "\n" + "=" * 170
)
print(
    "PART 2 — ENDPOINT MAPPING COVERAGE"
)
print(
    "=" * 170
)

endpoint_summary = (
    mapping.groupby(
        [
            "year",
            "match_status",
        ]
    )
    .size()
    .rename(
        "rows"
    )
    .reset_index()
)

print(
    endpoint_summary.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 3 — PAIR-LEVEL MAPPING SUMMARY"
)
print(
    "=" * 170
)

pair_summary = (
    pairs.groupby(
        "year"
    )
    .agg(
        transitions=(
            "transition_id",
            "size"
        ),

        both_unique=(
            "both_unique",
            "sum"
        ),

        positive_time_order=(
            "positive_time_order",
            "sum"
        ),

        within_120_min=(
            "within_120_min",
            "sum"
        ),

        start_track_available=(
            "before_track_c",
            lambda x:
                int(
                    pd.Series(
                        x
                    ).notna().sum()
                )
        ),

        start_ambient_available=(
            "before_ambient_c",
            lambda x:
                int(
                    pd.Series(
                        x
                    ).notna().sum()
                )
        ),
    )
    .reset_index()
)

print(
    pair_summary.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 4 — UNIQUELY MAPPED PAIRS"
)
print(
    "=" * 170
)

good = pairs[
    pairs[
        "both_unique"
    ]
].copy()

if good.empty:

    print(
        "NONE"
    )

else:

    print(
        good[
            [
                "transition_id",
                "year",
                "car_number",
                "driver_name",
                "before_run_index",
                "after_run_index",
                "before_timestamp_utc",
                "after_timestamp_utc",
                "actual_wait_min",
                "before_track_c",
                "before_ambient_c",
                "within_120_min",
                "before_source",
                "after_source",
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
    "\nOUTPUTS:"
)

for p in [
    OFFSET_OUT,
    MAPPING_OUT,
    PAIR_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nHOLDOUT_ATTEMPT_IDENTITY_RECONCILIATION_V4_COMPLETE"
)
