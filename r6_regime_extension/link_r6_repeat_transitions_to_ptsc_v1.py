from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

PTSC = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_ptsc_canonical_v1/"
    "r6_ptsc_2019_2025_canonical_v1.csv"
)

TRANS_2019 = (
    ROOT /
    "r6_regime_extension/output/"
    "timing71_legacy_run_overlap_qa_v1/"
    "legacy_verified_nonoverlap_repeat_transitions_v1.csv"
)

TRANS_2025 = (
    ROOT /
    "r6_regime_extension/output/"
    "timing71_2025_clean_chronology_v1/"
    "timing71_2025_clean_repeat_transitions_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_repeat_ptsc_linkage_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

MAX_SAFE_BRACKET_MINUTES = 30.0

PHYSICAL_FIELDS = [
    "ambient_c",
    "track_c",
    "humidity_raw",
    "wind_raw",
    "pressure_raw",
]


# ============================================================
# Load PTSC
# ============================================================

ptsc = pd.read_csv(
    PTSC,
    low_memory=False
)

ptsc[
    "datetime_utc"
] = pd.to_datetime(
    ptsc[
        "datetime_utc"
    ],
    utc=True,
    errors="coerce"
)

ptsc = ptsc[
    ptsc[
        "datetime_utc"
    ].notna()
].copy()

for c in PHYSICAL_FIELDS:

    ptsc[c] = pd.to_numeric(
        ptsc[c],
        errors="coerce"
    )

ptsc = ptsc.sort_values(
    [
        "year",
        "datetime_utc",
    ]
).reset_index(
    drop=True
)


# ============================================================
# Load 2019 transitions
# ============================================================

t19 = pd.read_csv(
    TRANS_2019,
    low_memory=False
)

t19[
    "from_timestamp_utc"
] = pd.to_datetime(
    t19[
        "from_mid_utc"
    ]
    if "from_mid_utc" in t19.columns
    else t19[
        "from_timestamp_utc"
    ],
    utc=True,
    errors="coerce"
)

t19[
    "to_timestamp_utc"
] = pd.to_datetime(
    t19[
        "to_mid_utc"
    ]
    if "to_mid_utc" in t19.columns
    else t19[
        "to_timestamp_utc"
    ],
    utc=True,
    errors="coerce"
)

t19[
    "technical_regime"
] = "UNIVERSAL_AERO_KIT_PRE_AEROSCREEN"

t19[
    "regime_code"
] = "A"

t19[
    "chronology_source"
] = "TIMING71_LEGACY_CLEAN_NONOVERLAP"


# ============================================================
# Load 2025 transitions
# ============================================================

t25 = pd.read_csv(
    TRANS_2025,
    low_memory=False
)

# clean_2025 script stores midpoint timestamps in milliseconds
t25[
    "from_timestamp_utc"
] = pd.to_datetime(
    t25[
        "from_timestamp_ms"
    ],
    unit="ms",
    utc=True,
    errors="coerce"
)

t25[
    "to_timestamp_utc"
] = pd.to_datetime(
    t25[
        "to_timestamp_ms"
    ],
    unit="ms",
    utc=True,
    errors="coerce"
)

t25[
    "technical_regime"
] = "AEROSCREEN_HYBRID"

t25[
    "regime_code"
] = "C"

t25[
    "chronology_source"
] = "TIMING71_2025_GLOBAL_ONE_TO_ONE_CLEAN"


# ============================================================
# Normalize transition columns
# ============================================================

KEEP = [
    "year",
    "regime_code",
    "technical_regime",
    "chronology_source",
    "car_number",
    "driver_name",
    "from_source_rank",
    "to_source_rank",
    "from_timestamp_utc",
    "to_timestamp_utc",
    "from_speed_mph",
    "to_speed_mph",
    "delta_speed_mph",
]

for df in [
    t19,
    t25,
]:

    for c in KEEP:

        if c not in df.columns:
            df[c] = np.nan


transitions = pd.concat(
    [
        t19[KEEP],
        t25[KEEP],
    ],
    ignore_index=True
)

transitions[
    "transition_id"
] = (
    transitions[
        "year"
    ].astype(str)
    +
    "_"
    +
    transitions[
        "car_number"
    ].astype(str)
    +
    "_"
    +
    transitions[
        "from_source_rank"
    ].astype(str)
    +
    "_TO_"
    +
    transitions[
        "to_source_rank"
    ].astype(str)
)


# ============================================================
# Interpolation
# ============================================================

def interpolate_state(
    year,
    timestamp
):

    g = ptsc[
        ptsc[
            "year"
        ]
        == year
    ].copy()

    if g.empty:

        return {
            "link_quality":
                "NO_YEAR_DATA"
        }

    g = g.sort_values(
        "datetime_utc"
    ).reset_index(
        drop=True
    )

    if pd.isna(
        timestamp
    ):

        return {
            "link_quality":
                "NO_TIMESTAMP"
        }

    # --------------------------------------------------------
    # Exact hit
    # --------------------------------------------------------

    exact = g[
        g[
            "datetime_utc"
        ]
        == timestamp
    ]

    if not exact.empty:

        row = exact.iloc[0]

        result = {
            "link_quality":
                "EXACT",

            "before_time":
                row[
                    "datetime_utc"
                ],

            "after_time":
                row[
                    "datetime_utc"
                ],

            "bracket_minutes":
                0.0,

            "interp_fraction":
                0.0,
        }

        for field in PHYSICAL_FIELDS:

            result[
                field
            ] = row[
                field
            ]

        return result

    # --------------------------------------------------------
    # Outside range
    # --------------------------------------------------------

    if (
        timestamp
        <
        g[
            "datetime_utc"
        ].min()
        or
        timestamp
        >
        g[
            "datetime_utc"
        ].max()
    ):

        return {
            "link_quality":
                "OUTSIDE_RANGE"
        }

    before = g[
        g[
            "datetime_utc"
        ]
        <
        timestamp
    ].tail(1)

    after = g[
        g[
            "datetime_utc"
        ]
        >
        timestamp
    ].head(1)

    if before.empty or after.empty:

        return {
            "link_quality":
                "UNBRACKETED"
        }

    b = before.iloc[0]
    a = after.iloc[0]

    total_seconds = (
        a[
            "datetime_utc"
        ]
        -
        b[
            "datetime_utc"
        ]
    ).total_seconds()

    if total_seconds <= 0:

        return {
            "link_quality":
                "INVALID_BRACKET"
        }

    bracket_minutes = (
        total_seconds
        /
        60.0
    )

    fraction = (
        (
            timestamp
            -
            b[
                "datetime_utc"
            ]
        ).total_seconds()
        /
        total_seconds
    )

    if (
        bracket_minutes
        >
        MAX_SAFE_BRACKET_MINUTES
    ):

        quality = "UNSAFE_GAP"

    else:

        quality = "INTERPOLATED"

    result = {
        "link_quality":
            quality,

        "before_time":
            b[
                "datetime_utc"
            ],

        "after_time":
            a[
                "datetime_utc"
            ],

        "bracket_minutes":
            bracket_minutes,

        "interp_fraction":
            fraction,
    }

    for field in PHYSICAL_FIELDS:

        bv = b[
            field
        ]

        av = a[
            field
        ]

        if (
            pd.isna(
                bv
            )
            or
            pd.isna(
                av
            )
        ):

            result[
                field
            ] = np.nan

        else:

            result[
                field
            ] = (
                float(
                    bv
                )
                +
                fraction
                *
                (
                    float(
                        av
                    )
                    -
                    float(
                        bv
                    )
                )
            )

    return result


# ============================================================
# Link both endpoints
# ============================================================

linked_rows = []

for _, tr in transitions.iterrows():

    year = int(
        tr[
            "year"
        ]
    )

    from_state = interpolate_state(
        year,
        tr[
            "from_timestamp_utc"
        ]
    )

    to_state = interpolate_state(
        year,
        tr[
            "to_timestamp_utc"
        ]
    )

    row = tr.to_dict()

    for key, value in from_state.items():

        row[
            "from_" + key
        ] = value

    for key, value in to_state.items():

        row[
            "to_" + key
        ] = value

    # --------------------------------------------------------
    # Transition-level linkage status
    # --------------------------------------------------------

    safe_endpoint_qualities = {
        "EXACT",
        "INTERPOLATED",
    }

    from_ok = (
        from_state.get(
            "link_quality"
        )
        in
        safe_endpoint_qualities
    )

    to_ok = (
        to_state.get(
            "link_quality"
        )
        in
        safe_endpoint_qualities
    )

    if from_ok and to_ok:

        transition_quality = (
            "PRIMARY_SAFE"
        )

    else:

        transition_quality = (
            "EXCLUDED_PHYSICAL_LINKAGE"
        )

    row[
        "physical_linkage_quality"
    ] = transition_quality

    # --------------------------------------------------------
    # Deltas
    # --------------------------------------------------------

    for field in PHYSICAL_FIELDS:

        fv = from_state.get(
            field,
            np.nan
        )

        tv = to_state.get(
            field,
            np.nan
        )

        if (
            pd.notna(
                fv
            )
            and
            pd.notna(
                tv
            )
        ):

            row[
                "delta_" + field
            ] = (
                float(
                    tv
                )
                -
                float(
                    fv
                )
            )

        else:

            row[
                "delta_" + field
            ] = np.nan

    linked_rows.append(
        row
    )


linked = pd.DataFrame(
    linked_rows
)


# ============================================================
# Primary analysis set
# ============================================================

primary = linked[
    linked[
        "physical_linkage_quality"
    ]
    ==
    "PRIMARY_SAFE"
].copy()

primary = primary[
    primary[
        [
            "delta_track_c",
            "delta_ambient_c",
            "delta_speed_mph",
        ]
    ]
    .notna()
    .all(
        axis=1
    )
].copy()


# ============================================================
# QA
# ============================================================

summary_rows = []

for year in [
    2019,
    2025,
]:

    y = linked[
        linked[
            "year"
        ]
        == year
    ]

    p = primary[
        primary[
            "year"
        ]
        == year
    ]

    summary_rows.append({
        "year":
            year,

        "input_clean_transitions":
            len(
                y
            ),

        "primary_safe_transitions":
            len(
                p
            ),

        "excluded_transitions":
            len(
                y
            )
            -
            len(
                p
            ),

        "from_exact":
            int(
                (
                    y[
                        "from_link_quality"
                    ]
                    ==
                    "EXACT"
                ).sum()
            ),

        "from_interpolated":
            int(
                (
                    y[
                        "from_link_quality"
                    ]
                    ==
                    "INTERPOLATED"
                ).sum()
            ),

        "from_unsafe_gap":
            int(
                (
                    y[
                        "from_link_quality"
                    ]
                    ==
                    "UNSAFE_GAP"
                ).sum()
            ),

        "from_outside_range":
            int(
                (
                    y[
                        "from_link_quality"
                    ]
                    ==
                    "OUTSIDE_RANGE"
                ).sum()
            ),

        "to_exact":
            int(
                (
                    y[
                        "to_link_quality"
                    ]
                    ==
                    "EXACT"
                ).sum()
            ),

        "to_interpolated":
            int(
                (
                    y[
                        "to_link_quality"
                    ]
                    ==
                    "INTERPOLATED"
                ).sum()
            ),

        "to_unsafe_gap":
            int(
                (
                    y[
                        "to_link_quality"
                    ]
                    ==
                    "UNSAFE_GAP"
                ).sum()
            ),

        "to_outside_range":
            int(
                (
                    y[
                        "to_link_quality"
                    ]
                    ==
                    "OUTSIDE_RANGE"
                ).sum()
            ),
    })


summary = pd.DataFrame(
    summary_rows
)


# ============================================================
# Save
# ============================================================

LINKED_OUT = (
    OUT /
    "r6_repeat_transitions_ptsc_linked_v1.csv"
)

PRIMARY_OUT = (
    OUT /
    "r6_repeat_transitions_primary_physics_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "r6_repeat_ptsc_linkage_summary_v1.csv"
)

EXCLUDED_OUT = (
    OUT /
    "r6_repeat_ptsc_linkage_excluded_v1.csv"
)

linked.to_csv(
    LINKED_OUT,
    index=False
)

primary.to_csv(
    PRIMARY_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

linked[
    linked[
        "physical_linkage_quality"
    ]
    !=
    "PRIMARY_SAFE"
].to_csv(
    EXCLUDED_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)
print(
    "PART 1 — PTSC LINKAGE SUMMARY"
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
    "PART 2 — EXCLUDED TRANSITIONS"
)
print(
    "=" * 170
)

excluded = linked[
    linked[
        "physical_linkage_quality"
    ]
    !=
    "PRIMARY_SAFE"
]

if excluded.empty:

    print(
        "NONE"
    )

else:

    print(
        excluded[
            [
                "year",
                "car_number",
                "driver_name",
                "from_source_rank",
                "to_source_rank",
                "from_timestamp_utc",
                "to_timestamp_utc",
                "from_link_quality",
                "from_bracket_minutes",
                "to_link_quality",
                "to_bracket_minutes",
            ]
        ]
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 170
)
print(
    "PART 3 — PRIMARY PHYSICAL TRANSITIONS"
)
print(
    "=" * 170
)

if primary.empty:

    print(
        "NONE"
    )

else:

    print(
        primary[
            [
                "year",
                "regime_code",
                "car_number",
                "driver_name",
                "from_source_rank",
                "to_source_rank",
                "delta_track_c",
                "delta_ambient_c",
                "delta_wind_raw",
                "delta_speed_mph",
                "from_bracket_minutes",
                "to_bracket_minutes",
            ]
        ]
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 170
)
print(
    "PART 4 — REGIME DELTA SUMMARY"
)
print(
    "=" * 170
)

if primary.empty:

    print(
        "NONE"
    )

else:

    regime_summary = (
        primary.groupby(
            [
                "regime_code",
                "year",
            ]
        )
        .agg(
            n=(
                "transition_id",
                "size"
            ),

            mean_delta_track_c=(
                "delta_track_c",
                "mean"
            ),

            sd_delta_track_c=(
                "delta_track_c",
                "std"
            ),

            mean_delta_ambient_c=(
                "delta_ambient_c",
                "mean"
            ),

            sd_delta_ambient_c=(
                "delta_ambient_c",
                "std"
            ),

            mean_delta_speed_mph=(
                "delta_speed_mph",
                "mean"
            ),

            sd_delta_speed_mph=(
                "delta_speed_mph",
                "std"
            ),
        )
        .reset_index()
    )

    print(
        regime_summary.to_string(
            index=False
        )
    )


print(
    "\nOUTPUTS:"
)

for p in [
    LINKED_OUT,
    PRIMARY_OUT,
    SUMMARY_OUT,
    EXCLUDED_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_REPEAT_PTSC_LINKAGE_V1_COMPLETE"
)
