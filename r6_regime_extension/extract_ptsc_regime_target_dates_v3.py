from pathlib import Path
from datetime import datetime, date, time
import re
import math

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

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "ptsc_regime_target_dates_v3"
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

# ============================================================
# Basic helpers
# ============================================================

def norm_text(x):

    if pd.isna(x):
        return ""

    return str(x).strip()


def safe_date(x):
    """
    Parse only things that really look like dates.
    Avoid dateutil warnings on strings such as 'St. Pete'.
    """

    if pd.isna(x):
        return None

    if isinstance(
        x,
        pd.Timestamp
    ):

        return x.normalize()

    if isinstance(
        x,
        datetime
    ):

        return pd.Timestamp(
            x
        ).normalize()

    if isinstance(
        x,
        date
    ) and not isinstance(
        x,
        time
    ):

        return pd.Timestamp(
            x
        ).normalize()

    s = str(x).strip()

    if not s:
        return None

    patterns = [
        r"^\d{4}-\d{1,2}-\d{1,2}(?:\s.*)?$",
        r"^\d{1,2}/\d{1,2}/\d{4}(?:\s.*)?$",
        r"^\d{1,2}-\d{1,2}-\d{4}(?:\s.*)?$",
    ]

    if not any(
        re.match(
            p,
            s
        )
        for p in patterns
    ):

        return None

    try:

        return pd.to_datetime(
            s,
            errors="raise"
        ).normalize()

    except Exception:

        return None


def safe_time(x):

    if pd.isna(x):
        return None

    if isinstance(
        x,
        time
    ):

        return x

    if isinstance(
        x,
        datetime
    ):

        return x.time()

    if isinstance(
        x,
        pd.Timestamp
    ):

        return x.time()

    # Excel time sometimes comes as fraction of day
    if isinstance(
        x,
        (
            int,
            float,
            np.number
        )
    ):

        try:

            v = float(
                x
            )

            if (
                0 <= v < 1
            ):

                total_seconds = int(
                    round(
                        v
                        * 86400
                    )
                )

                h = (
                    total_seconds
                    //
                    3600
                ) % 24

                m = (
                    total_seconds
                    % 3600
                ) // 60

                s = (
                    total_seconds
                    % 60
                )

                return time(
                    h,
                    m,
                    s
                )

        except Exception:
            pass

    s = str(x).strip()

    for fmt in [
        "%H:%M:%S",
        "%H:%M",
        "%I:%M:%S %p",
        "%I:%M %p",
    ]:

        try:

            return datetime.strptime(
                s,
                fmt
            ).time()

        except Exception:
            continue

    return None


def combine_date_time(
    d,
    t
):

    if d is None:
        return pd.NaT

    tt = safe_time(
        t
    )

    if tt is None:
        return pd.NaT

    return pd.Timestamp(
        datetime.combine(
            d.date(),
            tt
        )
    )


def numeric(x):

    return pd.to_numeric(
        pd.Series(
            [x]
        ),
        errors="coerce"
    ).iloc[0]


def fahrenheit_to_celsius(x):

    if pd.isna(x):
        return np.nan

    return (
        float(x)
        - 32.0
    ) * 5.0 / 9.0


# ============================================================
# Raw sheet scanning
# ============================================================

def read_raw_sheet(
    sheet
):

    return pd.read_excel(
        BOOK,
        sheet_name=sheet,
        header=None
    )


def find_date_cells(
    raw,
    target_date
):

    hits = []

    target = target_date.normalize()

    for r in range(
        len(raw)
    ):

        for c in range(
            raw.shape[1]
        ):

            d = safe_date(
                raw.iat[
                    r,
                    c
                ]
            )

            if (
                d is not None
                and
                d == target
            ):

                hits.append({
                    "row":
                        r,

                    "col":
                        c,

                    "raw_value":
                        raw.iat[
                            r,
                            c
                        ],
                })

    return hits


def header_score(
    row_values
):

    values = [
        norm_text(x)
        .lower()
        for x in row_values
    ]

    tokens = {
        "date":
            False,

        "time":
            False,

        "ambient":
            False,

        "track":
            False,

        "humidity":
            False,

        "wind":
            False,

        "direction":
            False,

        "barometer":
            False,

        "pressure":
            False,
    }

    for val in values:

        compact = re.sub(
            r"\s+",
            " ",
            val
        )

        if compact == "date":
            tokens["date"] = True

        if compact == "time":
            tokens["time"] = True

        if compact in {
            "ambient",
            "amb",
            "ambient temp",
        }:

            tokens[
                "ambient"
            ] = True

        if compact in {
            "track",
            "track temp",
            "track temperature",
        }:

            tokens[
                "track"
            ] = True

        if "humidity" in compact:
            tokens[
                "humidity"
            ] = True

        if compact == "wind":
            tokens[
                "wind"
            ] = True

        if compact in {
            "direction",
            "dir",
        }:

            tokens[
                "direction"
            ] = True

        if "barometer" in compact:
            tokens[
                "barometer"
            ] = True

        if "pressure" in compact:
            tokens[
                "pressure"
            ] = True

    score = (
        3 * int(
            tokens["time"]
        )
        +
        3 * int(
            tokens["ambient"]
        )
        +
        3 * int(
            tokens["track"]
        )
        +
        int(
            tokens["date"]
        )
        +
        int(
            tokens["humidity"]
        )
        +
        int(
            tokens["wind"]
        )
        +
        int(
            tokens["direction"]
        )
        +
        int(
            tokens["barometer"]
        )
        +
        int(
            tokens["pressure"]
        )
    )

    return score


def find_candidate_header_rows(
    raw,
    target_row
):

    rows = []

    lo = max(
        0,
        target_row - 25
    )

    hi = min(
        len(raw),
        target_row + 10
    )

    for r in range(
        lo,
        hi
    ):

        score = header_score(
            raw.iloc[
                r
            ].tolist()
        )

        if score >= 8:

            rows.append({
                "row":
                    r,

                "score":
                    score,

                "values":
                    raw.iloc[
                        r
                    ].tolist(),
            })

    return sorted(
        rows,
        key=lambda x: (
            abs(
                x["row"]
                - target_row
            ),
            -x["score"],
        )
    )


def identify_header_columns(
    header_values
):

    result = {}

    for c, value in enumerate(
        header_values
    ):

        s = norm_text(
            value
        ).lower()

        s = re.sub(
            r"\s+",
            " ",
            s
        )

        if (
            "date" not in result
            and
            s == "date"
        ):

            result[
                "date"
            ] = c

        elif (
            "time" not in result
            and
            s == "time"
        ):

            result[
                "time"
            ] = c

        elif (
            "ambient" not in result
            and
            s in {
                "ambient",
                "amb",
                "ambient temp",
            }
        ):

            result[
                "ambient"
            ] = c

        elif (
            "track" not in result
            and
            s in {
                "track",
                "track temp",
                "track temperature",
            }
        ):

            result[
                "track"
            ] = c

        elif (
            "humidity" not in result
            and
            "humidity" in s
        ):

            result[
                "humidity"
            ] = c

        elif (
            "wind" not in result
            and
            s == "wind"
        ):

            result[
                "wind"
            ] = c

        elif (
            "direction" not in result
            and
            s in {
                "direction",
                "dir",
            }
        ):

            result[
                "direction"
            ] = c

        elif (
            "pressure" not in result
            and
            (
                "barometer" in s
                or
                "pressure" in s
            )
        ):

            result[
                "pressure"
            ] = c

    return result


def row_preview(
    raw,
    center_row,
    radius=8
):

    lo = max(
        0,
        center_row - radius
    )

    hi = min(
        len(raw),
        center_row + radius + 1
    )

    return raw.iloc[
        lo:hi
    ].copy()


# ============================================================
# Block extractor
# ============================================================

def extract_target_block(
    raw,
    year,
    target_date,
    date_hit
):

    target_row = date_hit[
        "row"
    ]

    target_col = date_hit[
        "col"
    ]

    candidate_headers = (
        find_candidate_header_rows(
            raw,
            target_row
        )
    )

    if not candidate_headers:

        return {
            "status":
                "NO_HEADER_FOUND",

            "target_row":
                target_row,

            "target_col":
                target_col,

            "header_row":
                None,

            "data":
                pd.DataFrame(),
        }

    header = candidate_headers[
        0
    ]

    header_row = header[
        "row"
    ]

    columns = (
        identify_header_columns(
            header[
                "values"
            ]
        )
    )

    required = {
        "time",
        "ambient",
        "track",
    }

    if not required.issubset(
        set(
            columns.keys()
        )
    ):

        return {
            "status":
                "HEADER_MISSING_REQUIRED_FIELDS",

            "target_row":
                target_row,

            "target_col":
                target_col,

            "header_row":
                header_row,

            "header_columns":
                columns,

            "data":
                pd.DataFrame(),
        }

    # --------------------------------------------------------
    # Determine current date while walking downward.
    #
    # In many PTSC sheets the Date cell occurs once and then
    # following rows are blank until the next event/day.
    # --------------------------------------------------------

    current_date = None

    extracted = []

    blank_streak = 0

    # Usually data starts immediately after header.
    # But if target date cell is before/after header, start from
    # whichever occurs first within the local block.
    start_row = min(
        header_row + 1,
        target_row
    )

    start_row = max(
        0,
        start_row
    )

    for r in range(
        start_row,
        len(raw)
    ):

        row = raw.iloc[
            r
        ]

        # detect any date cell in the row
        dates_in_row = []

        for c in range(
            raw.shape[1]
        ):

            d = safe_date(
                row.iloc[
                    c
                ]
            )

            if d is not None:

                dates_in_row.append(
                    d
                )

        if dates_in_row:

            current_date = (
                dates_in_row[
                    0
                ]
            )

        # target row itself establishes the target date even if
        # date column is not part of the local header.
        if r == target_row:

            current_date = (
                target_date.normalize()
            )

        # Once we have passed target block and encounter a new
        # explicit date, stop.
        if (
            current_date is not None
            and
            current_date
            != target_date.normalize()
            and
            r > target_row
        ):

            if extracted:
                break

        time_value = row.iloc[
            columns[
                "time"
            ]
        ]

        t = safe_time(
            time_value
        )

        ambient = numeric(
            row.iloc[
                columns[
                    "ambient"
                ]
            ]
        )

        track = numeric(
            row.iloc[
                columns[
                    "track"
                ]
            ]
        )

        # rows without actual observation values are ignored
        if (
            t is None
            or
            pd.isna(
                ambient
            )
            or
            pd.isna(
                track
            )
        ):

            if (
                r > target_row
                and
                extracted
            ):

                blank_streak += 1

            if (
                blank_streak >= 8
                and
                extracted
            ):

                break

            continue

        blank_streak = 0

        if (
            current_date is None
        ):

            # If the date hit is above and no other date has
            # appeared, propagate target date.
            if r >= target_row:

                current_date = (
                    target_date.normalize()
                )

        if (
            current_date
            != target_date.normalize()
        ):

            continue

        humidity = (
            numeric(
                row.iloc[
                    columns[
                        "humidity"
                    ]
                ]
            )
            if "humidity" in columns
            else np.nan
        )

        wind = (
            numeric(
                row.iloc[
                    columns[
                        "wind"
                    ]
                ]
            )
            if "wind" in columns
            else np.nan
        )

        direction = (
            norm_text(
                row.iloc[
                    columns[
                        "direction"
                    ]
                ]
            )
            if "direction" in columns
            else ""
        )

        pressure = (
            numeric(
                row.iloc[
                    columns[
                        "pressure"
                    ]
                ]
            )
            if "pressure" in columns
            else np.nan
        )

        dt = combine_date_time(
            target_date,
            t
        )

        extracted.append({
            "year":
                year,

            "source_sheet":
                TARGETS[
                    year
                ][
                    "sheet"
                ],

            "source_row":
                r,

            "datetime_local":
                dt,

            "time_local":
                t.strftime(
                    "%H:%M:%S"
                ),

            "ambient_f":
                ambient,

            "ambient_c":
                fahrenheit_to_celsius(
                    ambient
                ),

            "track_f":
                track,

            "track_c":
                fahrenheit_to_celsius(
                    track
                ),

            "humidity_raw":
                humidity,

            "wind_raw":
                wind,

            "wind_direction":
                direction
                if direction
                else np.nan,

            "pressure_raw":
                pressure,

            "date_hit_row":
                target_row,

            "date_hit_col":
                target_col,

            "header_row":
                header_row,
        })

    df = pd.DataFrame(
        extracted
    )

    if not df.empty:

        df = (
            df
            .drop_duplicates(
                subset=[
                    "datetime_local",
                    "ambient_f",
                    "track_f",
                    "wind_raw",
                ]
            )
            .sort_values(
                "datetime_local"
            )
            .reset_index(
                drop=True
            )
        )

    return {
        "status":
            (
                "PASS"
                if not df.empty
                else
                "NO_OBSERVATIONS_EXTRACTED"
            ),

        "target_row":
            target_row,

        "target_col":
            target_col,

        "header_row":
            header_row,

        "header_columns":
            columns,

        "data":
            df,
    }


# ============================================================
# Main
# ============================================================

xls = pd.ExcelFile(
    BOOK
)

all_year_data = {}
audit_rows = []

print(
    "=" * 170
)
print(
    "PART 1 — TARGET DATE CELL DISCOVERY"
)
print(
    "=" * 170
)

for year, cfg in TARGETS.items():

    sheet = cfg[
        "sheet"
    ]

    if sheet not in xls.sheet_names:

        print(
            year,
            sheet,
            "SHEET_MISSING"
        )

        continue

    raw = read_raw_sheet(
        sheet
    )

    hits = find_date_cells(
        raw,
        cfg[
            "date"
        ]
    )

    print(
        "\nYEAR",
        year,
        "SHEET",
        sheet,
        "TARGET",
        cfg[
            "date"
        ].date(),
        "DATE_HITS",
        len(
            hits
        )
    )

    for hit in hits:

        print(
            "  row=",
            hit[
                "row"
            ],
            "col=",
            hit[
                "col"
            ],
            "value=",
            repr(
                hit[
                    "raw_value"
                ]
            )
        )

    if not hits:

        all_year_data[
            year
        ] = pd.DataFrame()

        audit_rows.append({
            "year":
                year,

            "status":
                "TARGET_DATE_NOT_FOUND",

            "date_hits":
                0,
        })

        continue

    # Try every target-date occurrence because workbooks can
    # contain duplicate date cells for charts/side panels.
    results = []

    for hit in hits:

        result = extract_target_block(
            raw,
            year,
            cfg[
                "date"
            ],
            hit
        )

        results.append(
            result
        )

    # Select extraction with most valid observations.
    results = sorted(
        results,
        key=lambda x:
            len(
                x[
                    "data"
                ]
            ),
        reverse=True
    )

    best = results[
        0
    ]

    data = best[
        "data"
    ]

    all_year_data[
        year
    ] = data

    audit_rows.append({
        "year":
            year,

        "status":
            best[
                "status"
            ],

        "date_hits":
            len(
                hits
            ),

        "selected_date_hit_row":
            best.get(
                "target_row"
            ),

        "selected_date_hit_col":
            best.get(
                "target_col"
            ),

        "header_row":
            best.get(
                "header_row"
            ),

        "observations":
            len(
                data
            ),

        "first_time":
            (
                data[
                    "datetime_local"
                ].min()
                if not data.empty
                else None
            ),

        "last_time":
            (
                data[
                    "datetime_local"
                ].max()
                if not data.empty
                else None
            ),
    })

    print(
        "SELECTED STATUS =",
        best[
            "status"
        ]
    )

    print(
        "HEADER ROW =",
        best.get(
            "header_row"
        )
    )

    print(
        "HEADER COLUMNS =",
        best.get(
            "header_columns"
        )
    )

    # Diagnostic local raw block
    print(
        "\nRAW LOCAL PREVIEW AROUND TARGET DATE:"
    )

    preview = row_preview(
        raw,
        best[
            "target_row"
        ],
        radius=8
    )

    print(
        preview
        .iloc[
            :,
            :min(
                16,
                preview.shape[1]
            )
        ]
        .to_string(
            index=True,
            header=False
        )
    )


audit = pd.DataFrame(
    audit_rows
)


# ============================================================
# Console summaries
# ============================================================

print(
    "\n" + "=" * 170
)
print(
    "PART 2 — EXTRACTION SUMMARY"
)
print(
    "=" * 170
)

print(
    audit.to_string(
        index=False
    )
)


for year in [
    2019,
    2025,
]:

    print(
        "\n" + "=" * 170
    )
    print(
        f"PART 3 — {year} EXTRACTED PTSC OBSERVATIONS"
    )
    print(
        "=" * 170
    )

    df = all_year_data.get(
        year,
        pd.DataFrame()
    )

    if df.empty:

        print(
            "NONE"
        )

        continue

    print(
        df[
            [
                "datetime_local",
                "ambient_f",
                "ambient_c",
                "track_f",
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


# ============================================================
# Gap QA
# ============================================================

gap_rows = []

for year, df in all_year_data.items():

    if df.empty:
        continue

    temp = (
        df[
            [
                "datetime_local"
            ]
        ]
        .dropna()
        .drop_duplicates()
        .sort_values(
            "datetime_local"
        )
        .reset_index(
            drop=True
        )
    )

    temp[
        "gap_minutes"
    ] = (
        temp[
            "datetime_local"
        ]
        .diff()
        .dt.total_seconds()
        /
        60.0
    )

    for i in range(
        1,
        len(
            temp
        )
    ):

        gap_rows.append({
            "year":
                year,

            "from_time":
                temp.iloc[
                    i - 1
                ][
                    "datetime_local"
                ],

            "to_time":
                temp.iloc[
                    i
                ][
                    "datetime_local"
                ],

            "gap_minutes":
                temp.iloc[
                    i
                ][
                    "gap_minutes"
                ],
        })


gaps = pd.DataFrame(
    gap_rows
)

print(
    "\n" + "=" * 170
)
print(
    "PART 4 — OBSERVATION GAP QA"
)
print(
    "=" * 170
)

if gaps.empty:

    print(
        "NONE"
    )

else:

    summary = (
        gaps.groupby(
            "year"
        )
        .agg(
            gap_count=(
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
        summary.to_string(
            index=False
        )
    )

    print(
        "\nGAPS > 30 MINUTES:"
    )

    large = gaps[
        gaps[
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

AUDIT_OUT = (
    OUT /
    "ptsc_target_date_extraction_audit_v3.csv"
)

GAP_OUT = (
    OUT /
    "ptsc_target_date_gap_audit_v3.csv"
)

audit.to_csv(
    AUDIT_OUT,
    index=False
)

gaps.to_csv(
    GAP_OUT,
    index=False
)

for year, df in all_year_data.items():

    df.to_csv(
        OUT /
        f"ptsc_indy500_day1_{year}_normalized_v3.csv",
        index=False
    )


print(
    "\nOUTPUTS:"
)

print(
    AUDIT_OUT.relative_to(
        ROOT
    )
)

print(
    GAP_OUT.relative_to(
        ROOT
    )
)

for year in all_year_data:

    print(
        (
            OUT /
            f"ptsc_indy500_day1_{year}_normalized_v3.csv"
        )
        .relative_to(
            ROOT
        )
    )

print(
    "\nR6_PTSC_REGIME_TARGET_DATES_V3_COMPLETE"
)
