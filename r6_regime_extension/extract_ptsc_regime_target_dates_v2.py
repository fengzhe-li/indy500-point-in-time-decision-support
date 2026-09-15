from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

BOOK = (
    ROOT /
    "weather/evidence/ptsc/"
    "FirestoneTemperatures_current.xlsx"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "ptsc_regime_target_dates_v2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

TARGETS = {
    2019: {
        "sheet":
            "2019 Temp Archive",

        "date":
            pd.Timestamp(
                "2019-05-18"
            ),
    },

    2025: {
        "sheet":
            "2025 Temp Archive",

        "date":
            pd.Timestamp(
                "2025-05-17"
            ),
    },
}


def clean_numeric(s):

    return pd.to_numeric(
        s,
        errors="coerce"
    )


def normalize_sheet(
    df,
    year,
    target_date
):

    df = df.copy()

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    if "Date" not in df.columns:
        raise RuntimeError(
            f"{year}: Date column missing"
        )

    if "Time" not in df.columns:
        raise RuntimeError(
            f"{year}: Time column missing"
        )

    # --------------------------------------------------------
    # Critical workbook rule:
    # Date appears only at the beginning of a session/day block.
    # Forward-fill it through following time rows.
    # --------------------------------------------------------

    raw_date = df[
        "Date"
    ]

    parsed_date = pd.to_datetime(
        raw_date,
        errors="coerce"
    )

    parsed_date = parsed_date.ffill()

    df[
        "_date_ffill"
    ] = parsed_date

    # time may already be datetime.time or string
    time_text = (
        df[
            "Time"
        ]
        .astype(str)
        .str.strip()
    )

    # remove meaningless NaN strings
    time_text = time_text.where(
        ~time_text.str.lower().isin(
            [
                "nan",
                "nat",
                "none",
                "",
            ]
        )
    )

    combined = pd.to_datetime(
        (
            df[
                "_date_ffill"
            ]
            .dt.strftime(
                "%Y-%m-%d"
            )
            +
            " "
            +
            time_text
        ),
        errors="coerce"
    )

    df[
        "_datetime_local"
    ] = combined

    # --------------------------------------------------------
    # Target day only
    # --------------------------------------------------------

    mask = (
        df[
            "_date_ffill"
        ]
        .dt.normalize()
        ==
        target_date.normalize()
    )

    target = df.loc[
        mask
    ].copy()

    # only retain actual weather-observation rows
    target = target[
        target[
            "_datetime_local"
        ]
        .notna()
    ].copy()

    # --------------------------------------------------------
    # Normalize numeric weather fields
    # --------------------------------------------------------

    for col in [
        "Ambient",
        "Track",
        "Humidity",
        "Wind",
        "Barometer",
        "Pressure",
    ]:

        if col in target.columns:

            target[
                col
            ] = clean_numeric(
                target[
                    col
                ]
            )

    # Convert Fahrenheit to Celsius.
    # Archive Ambient/Track fields are Fahrenheit.
    if "Ambient" in target.columns:

        target[
            "ambient_f"
        ] = target[
            "Ambient"
        ]

        target[
            "ambient_c"
        ] = (
            target[
                "ambient_f"
            ]
            - 32.0
        ) * 5.0 / 9.0

    if "Track" in target.columns:

        target[
            "track_f"
        ] = target[
            "Track"
        ]

        target[
            "track_c"
        ] = (
            target[
                "track_f"
            ]
            - 32.0
        ) * 5.0 / 9.0

    if "Humidity" in target.columns:

        target[
            "humidity_raw"
        ] = target[
            "Humidity"
        ]

    if "Wind" in target.columns:

        target[
            "wind_raw"
        ] = target[
            "Wind"
        ]

    if "Direction" in target.columns:

        target[
            "wind_direction"
        ] = (
            target[
                "Direction"
            ]
            .astype(str)
            .replace(
                "nan",
                np.nan
            )
        )

    pressure_col = None

    if "Barometer" in target.columns:

        pressure_col = (
            "Barometer"
        )

    elif "Pressure" in target.columns:

        pressure_col = (
            "Pressure"
        )

    if pressure_col:

        target[
            "pressure_raw"
        ] = clean_numeric(
            target[
                pressure_col
            ]
        )

    # --------------------------------------------------------
    # QA
    # --------------------------------------------------------

    target = target.sort_values(
        "_datetime_local"
    )

    target[
        "year"
    ] = year

    target[
        "source_sheet"
    ] = TARGETS[
        year
    ][
        "sheet"
    ]

    target[
        "observation_index"
    ] = range(
        1,
        len(target) + 1
    )

    return target


# ============================================================
# Extract
# ============================================================

all_outputs = {}
summary_rows = []

xls = pd.ExcelFile(
    BOOK
)

print(
    "=" * 160
)
print(
    "PART 1 — TARGET SHEET AVAILABILITY"
)
print(
    "=" * 160
)

for year, cfg in TARGETS.items():

    sheet = cfg[
        "sheet"
    ]

    exists = (
        sheet
        in
        xls.sheet_names
    )

    print(
        year,
        sheet,
        "FOUND"
        if exists
        else
        "MISSING"
    )

    if not exists:

        continue

    raw = pd.read_excel(
        BOOK,
        sheet_name=sheet
    )

    target = normalize_sheet(
        raw,
        year,
        cfg[
            "date"
        ]
    )

    all_outputs[
        year
    ] = target

    summary_rows.append({
        "year":
            year,

        "sheet":
            sheet,

        "target_date":
            cfg[
                "date"
            ].date(),

        "rows":
            len(
                target
            ),

        "first_time":
            (
                target[
                    "_datetime_local"
                ].min()
                if not target.empty
                else None
            ),

        "last_time":
            (
                target[
                    "_datetime_local"
                ].max()
                if not target.empty
                else None
            ),

        "ambient_nonnull":
            (
                int(
                    target[
                        "ambient_c"
                    ]
                    .notna()
                    .sum()
                )
                if (
                    not target.empty
                    and
                    "ambient_c"
                    in target.columns
                )
                else 0
            ),

        "track_nonnull":
            (
                int(
                    target[
                        "track_c"
                    ]
                    .notna()
                    .sum()
                )
                if (
                    not target.empty
                    and
                    "track_c"
                    in target.columns
                )
                else 0
            ),

        "wind_nonnull":
            (
                int(
                    target[
                        "wind_raw"
                    ]
                    .notna()
                    .sum()
                )
                if (
                    not target.empty
                    and
                    "wind_raw"
                    in target.columns
                )
                else 0
            ),
    })


summary = pd.DataFrame(
    summary_rows
)


# ============================================================
# Console detail
# ============================================================

print(
    "\n" + "=" * 160
)
print(
    "PART 2 — TARGET DATE EXTRACTION SUMMARY"
)
print(
    "=" * 160
)

print(
    summary.to_string(
        index=False
    )
)


for year in [
    2019,
    2025,
]:

    print(
        "\n" + "=" * 160
    )
    print(
        f"PART 3 — {year} TARGET WEATHER ROWS"
    )
    print(
        "=" * 160
    )

    df = all_outputs.get(
        year,
        pd.DataFrame()
    )

    if df.empty:

        print(
            "NONE"
        )

        continue

    display = [
        c
        for c in [
            "_datetime_local",
            "ambient_f",
            "ambient_c",
            "track_f",
            "track_c",
            "humidity_raw",
            "wind_raw",
            "wind_direction",
            "pressure_raw",
        ]
        if c in df.columns
    ]

    print(
        df[
            display
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# Coverage gap QA
# ============================================================

print(
    "\n" + "=" * 160
)
print(
    "PART 4 — OBSERVATION GAP QA"
)
print(
    "=" * 160
)

gap_rows = []

for year, df in all_outputs.items():

    if df.empty:
        continue

    times = (
        df[
            "_datetime_local"
        ]
        .dropna()
        .sort_values()
        .reset_index(
            drop=True
        )
    )

    if len(
        times
    ) < 2:
        continue

    gaps = (
        times.diff()
        .dt.total_seconds()
        / 60.0
    )

    for i in range(
        1,
        len(times)
    ):

        gap_rows.append({
            "year":
                year,

            "from_time":
                times.iloc[
                    i - 1
                ],

            "to_time":
                times.iloc[
                    i
                ],

            "gap_minutes":
                gaps.iloc[
                    i
                ],
        })


gaps_df = pd.DataFrame(
    gap_rows
)

if gaps_df.empty:

    print(
        "NONE"
    )

else:

    gap_summary = (
        gaps_df.groupby(
            "year"
        )
        .agg(
            observations_gaps=(
                "gap_minutes",
                "size"
            ),

            median_gap_minutes=(
                "gap_minutes",
                "median"
            ),

            max_gap_minutes=(
                "gap_minutes",
                "max"
            ),
        )
        .reset_index()
    )

    print(
        gap_summary.to_string(
            index=False
        )
    )

    print(
        "\nGAPS > 30 MINUTES:"
    )

    large = gaps_df[
        gaps_df[
            "gap_minutes"
        ]
        > 30
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


# ============================================================
# Save
# ============================================================

for year, df in all_outputs.items():

    path = (
        OUT /
        f"ptsc_indy500_day1_{year}_raw_normalized_v2.csv"
    )

    df.to_csv(
        path,
        index=False
    )

SUMMARY_OUT = (
    OUT /
    "ptsc_regime_target_date_summary_v2.csv"
)

GAPS_OUT = (
    OUT /
    "ptsc_regime_target_date_gap_audit_v2.csv"
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

gaps_df.to_csv(
    GAPS_OUT,
    index=False
)


print(
    "\nOUTPUTS:"
)

for year in all_outputs:

    print(
        (
            OUT /
            f"ptsc_indy500_day1_{year}_raw_normalized_v2.csv"
        ).relative_to(
            ROOT
        )
    )

print(
    SUMMARY_OUT.relative_to(
        ROOT
    )
)

print(
    GAPS_OUT.relative_to(
        ROOT
    )
)

print(
    "\nR6_PTSC_REGIME_TARGET_DATES_V2_COMPLETE"
)
