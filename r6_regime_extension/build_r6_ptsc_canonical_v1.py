from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

BOOK = (
    ROOT /
    "weather/evidence/ptsc/"
    "FirestoneTemperatures_current.xlsx"
)

PTSC_2025 = (
    ROOT /
    "r6_regime_extension/output/"
    "ptsc_regime_target_dates_v3/"
    "ptsc_indy500_day1_2025_normalized_v3.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_ptsc_canonical_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

INDY_TZ = ZoneInfo(
    "America/Indiana/Indianapolis"
)

UTC_TZ = ZoneInfo(
    "UTC"
)


def to_numeric(s):
    return pd.to_numeric(
        s,
        errors="coerce"
    )


def parse_time_value(x):

    if pd.isna(x):
        return None

    if isinstance(x, time):
        return x

    if isinstance(x, pd.Timestamp):
        return x.time()

    if isinstance(x, datetime):
        return x.time()

    s = str(x).strip()

    for fmt in [
        "%H:%M:%S",
        "%H:%M",
    ]:

        try:
            return datetime.strptime(
                s,
                fmt
            ).time()
        except Exception:
            pass

    return None


def local_to_utc(
    local_naive
):

    if pd.isna(local_naive):
        return pd.NaT

    dt = pd.Timestamp(
        local_naive
    ).to_pydatetime()

    aware = dt.replace(
        tzinfo=INDY_TZ
    )

    return pd.Timestamp(
        aware.astimezone(
            UTC_TZ
        )
    )


# ============================================================
# 2019 — standard sheet columns + Date forward-fill
# ============================================================

raw19 = pd.read_excel(
    BOOK,
    sheet_name="2019 Temp Archive"
)

raw19.columns = [
    str(c).strip()
    for c in raw19.columns
]

required19 = [
    "Date",
    "Time",
    "Ambient",
    "Track",
    "Humidity",
    "Wind",
    "Direction",
    "Barometer",
]

missing19 = [
    c
    for c in required19
    if c not in raw19.columns
]

if missing19:
    raise RuntimeError(
        "2019 missing expected columns: "
        + ", ".join(
            missing19
        )
    )

# Only genuinely parse date-looking cells;
# Excel datetime values are already readable.
dates19 = pd.to_datetime(
    raw19["Date"],
    errors="coerce"
)

dates19 = dates19.ffill()

raw19[
    "_date_ffill"
] = dates19

target19 = raw19[
    raw19[
        "_date_ffill"
    ].dt.normalize()
    ==
    pd.Timestamp(
        "2019-05-18"
    )
].copy()

target19[
    "_time_parsed"
] = target19[
    "Time"
].map(
    parse_time_value
)

target19 = target19[
    target19[
        "_time_parsed"
    ].notna()
].copy()

target19[
    "datetime_local"
] = target19.apply(
    lambda r:
        pd.Timestamp(
            datetime.combine(
                r[
                    "_date_ffill"
                ].date(),
                r[
                    "_time_parsed"
                ]
            )
        ),
    axis=1
)

for c in [
    "Ambient",
    "Track",
    "Humidity",
    "Wind",
    "Barometer",
]:

    target19[c] = to_numeric(
        target19[c]
    )

ptsc19 = pd.DataFrame({
    "year":
        2019,

    "datetime_local":
        target19[
            "datetime_local"
        ],

    "ambient_f":
        target19[
            "Ambient"
        ],

    "track_f":
        target19[
            "Track"
        ],

    "humidity_raw":
        target19[
            "Humidity"
        ],

    "wind_raw":
        target19[
            "Wind"
        ],

    "wind_direction":
        target19[
            "Direction"
        ],

    "pressure_raw":
        target19[
            "Barometer"
        ],

    "source_sheet":
        "2019 Temp Archive",
})

ptsc19[
    "ambient_c"
] = (
    ptsc19[
        "ambient_f"
    ]
    - 32
) * 5 / 9

ptsc19[
    "track_c"
] = (
    ptsc19[
        "track_f"
    ]
    - 32
) * 5 / 9


# ============================================================
# 2025 — already successfully extracted by V3
# ============================================================

if not PTSC_2025.exists():
    raise FileNotFoundError(
        PTSC_2025
    )

src25 = pd.read_csv(
    PTSC_2025,
    low_memory=False
)

src25[
    "datetime_local"
] = pd.to_datetime(
    src25[
        "datetime_local"
    ],
    errors="coerce"
)

ptsc25 = pd.DataFrame({
    "year":
        2025,

    "datetime_local":
        src25[
            "datetime_local"
        ],

    "ambient_f":
        to_numeric(
            src25[
                "ambient_f"
            ]
        ),

    "ambient_c":
        to_numeric(
            src25[
                "ambient_c"
            ]
        ),

    "track_f":
        to_numeric(
            src25[
                "track_f"
            ]
        ),

    "track_c":
        to_numeric(
            src25[
                "track_c"
            ]
        ),

    "humidity_raw":
        to_numeric(
            src25[
                "humidity_raw"
            ]
        ),

    "wind_raw":
        to_numeric(
            src25[
                "wind_raw"
            ]
        ),

    "wind_direction":
        src25[
            "wind_direction"
        ],

    "pressure_raw":
        to_numeric(
            src25[
                "pressure_raw"
            ]
        ),

    "source_sheet":
        "2025 Temp Archive",
})


# ============================================================
# Canonical time conversion
# ============================================================

combined = pd.concat(
    [
        ptsc19,
        ptsc25,
    ],
    ignore_index=True
)

combined = combined[
    combined[
        "datetime_local"
    ].notna()
].copy()

combined[
    "datetime_indianapolis"
] = combined[
    "datetime_local"
].map(
    lambda x:
        pd.Timestamp(x)
        .tz_localize(
            INDY_TZ
        )
)

combined[
    "datetime_utc"
] = combined[
    "datetime_indianapolis"
].dt.tz_convert(
    "UTC"
)

combined = combined.sort_values(
    [
        "year",
        "datetime_utc",
    ]
).reset_index(
    drop=True
)

combined[
    "observation_index"
] = (
    combined.groupby(
        "year"
    ).cumcount()
    + 1
)


# ============================================================
# QA
# ============================================================

summary_rows = []

gap_rows = []

for year, g in combined.groupby(
    "year"
):

    g = g.sort_values(
        "datetime_utc"
    ).reset_index(
        drop=True
    )

    gaps = (
        g[
            "datetime_utc"
        ]
        .diff()
        .dt.total_seconds()
        / 60.0
    )

    for i in range(
        1,
        len(g)
    ):

        gap_rows.append({
            "year":
                year,

            "from_utc":
                g.iloc[
                    i - 1
                ][
                    "datetime_utc"
                ],

            "to_utc":
                g.iloc[
                    i
                ][
                    "datetime_utc"
                ],

            "gap_minutes":
                gaps.iloc[
                    i
                ],
        })

    summary_rows.append({
        "year":
            year,

        "observations":
            len(g),

        "first_local":
            g[
                "datetime_local"
            ].min(),

        "last_local":
            g[
                "datetime_local"
            ].max(),

        "first_utc":
            g[
                "datetime_utc"
            ].min(),

        "last_utc":
            g[
                "datetime_utc"
            ].max(),

        "ambient_nonnull":
            int(
                g[
                    "ambient_c"
                ]
                .notna()
                .sum()
            ),

        "track_nonnull":
            int(
                g[
                    "track_c"
                ]
                .notna()
                .sum()
            ),

        "wind_nonnull":
            int(
                g[
                    "wind_raw"
                ]
                .notna()
                .sum()
            ),

        "median_gap_minutes":
            (
                float(
                    gaps.dropna()
                    .median()
                )
                if gaps.notna().any()
                else np.nan
            ),

        "max_gap_minutes":
            (
                float(
                    gaps.dropna()
                    .max()
                )
                if gaps.notna().any()
                else np.nan
            ),
    })

summary = pd.DataFrame(
    summary_rows
)

gaps_df = pd.DataFrame(
    gap_rows
)


# ============================================================
# Save
# ============================================================

CANONICAL_OUT = (
    OUT /
    "r6_ptsc_2019_2025_canonical_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "r6_ptsc_2019_2025_summary_v1.csv"
)

GAP_OUT = (
    OUT /
    "r6_ptsc_2019_2025_gap_audit_v1.csv"
)

PTSC19_OUT = (
    OUT /
    "r6_ptsc_2019_canonical_v1.csv"
)

PTSC25_OUT = (
    OUT /
    "r6_ptsc_2025_canonical_v1.csv"
)

combined.to_csv(
    CANONICAL_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

gaps_df.to_csv(
    GAP_OUT,
    index=False
)

combined[
    combined[
        "year"
    ] == 2019
].to_csv(
    PTSC19_OUT,
    index=False
)

combined[
    combined[
        "year"
    ] == 2025
].to_csv(
    PTSC25_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 160
)
print(
    "PART 1 — CANONICAL PTSC SUMMARY"
)
print(
    "=" * 160
)

print(
    summary.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 160
)
print(
    "PART 2 — 2019 PTSC TARGET DAY"
)
print(
    "=" * 160
)

print(
    combined[
        combined[
            "year"
        ] == 2019
    ][
        [
            "datetime_local",
            "datetime_utc",
            "ambient_c",
            "track_c",
            "humidity_raw",
            "wind_raw",
            "wind_direction",
            "pressure_raw",
        ]
    ]
    .to_string(
        index=False
    )
)


print(
    "\n" + "=" * 160
)
print(
    "PART 3 — LARGE GAPS > 30 MIN"
)
print(
    "=" * 160
)

large = gaps_df[
    gaps_df[
        "gap_minutes"
    ] > 30
]

if large.empty:

    print(
        "NONE"
    )

else:

    print(
        large.to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 160
)
print(
    "PART 4 — UTC CONVERSION SANITY"
)
print(
    "=" * 160
)

for year in [
    2019,
    2025,
]:

    g = combined[
        combined[
            "year"
        ] == year
    ]

    if g.empty:
        continue

    print(
        year,
        "LOCAL FIRST =",
        g.iloc[
            0
        ][
            "datetime_indianapolis"
        ],
        "UTC FIRST =",
        g.iloc[
            0
        ][
            "datetime_utc"
        ]
    )

print(
    "\nOUTPUTS:"
)

for p in [
    CANONICAL_OUT,
    SUMMARY_OUT,
    GAP_OUT,
    PTSC19_OUT,
    PTSC25_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_PTSC_CANONICAL_V1_COMPLETE"
)
