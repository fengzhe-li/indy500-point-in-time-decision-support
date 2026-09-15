from pathlib import Path
import re
import math
from datetime import datetime

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
    "ptsc_2019_2025_audit_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

TARGETS = {
    2019: pd.Timestamp("2019-05-18"),
    2025: pd.Timestamp("2025-05-17"),
}

# ============================================================
# Helpers
# ============================================================

def clean_col(x):
    return str(x).strip()


def parse_datetime_series(s):

    # Explicitly suppress hard failures; this is audit only.
    try:

        parsed = pd.to_datetime(
            s,
            errors="coerce",
            infer_datetime_format=False
        )

        return parsed

    except Exception:

        return pd.Series(
            pd.NaT,
            index=s.index
        )


def plausible_date_count(s):

    parsed = parse_datetime_series(
        s
    )

    mask = (
        parsed.notna()
        &
        (
            parsed.dt.year
            .between(
                2000,
                2030
            )
        )
    )

    return int(
        mask.sum()
    )


def detect_datetime_columns(df):

    rows = []

    for col in df.columns:

        s = df[col]

        parsed = parse_datetime_series(
            s
        )

        valid = (
            parsed.notna()
            &
            parsed.dt.year.between(
                2000,
                2030
            )
        )

        n = int(
            valid.sum()
        )

        if n == 0:
            continue

        valid_dates = parsed[
            valid
        ]

        rows.append({
            "column":
                col,

            "valid_datetime_rows":
                n,

            "min_datetime":
                valid_dates.min(),

            "max_datetime":
                valid_dates.max(),

            "years":
                " | ".join(
                    map(
                        str,
                        sorted(
                            valid_dates
                            .dt.year
                            .unique()
                        )
                    )
                ),
        })

    return pd.DataFrame(
        rows
    )


def find_target_rows(
    df,
    year,
    target_date
):

    hits = []

    for col in df.columns:

        parsed = parse_datetime_series(
            df[col]
        )

        mask = (
            parsed.notna()
            &
            (
                parsed.dt.date
                ==
                target_date.date()
            )
        )

        if not mask.any():
            continue

        temp = df.loc[
            mask
        ].copy()

        temp.insert(
            0,
            "_matched_datetime_column",
            col
        )

        temp.insert(
            1,
            "_parsed_datetime",
            parsed.loc[
                mask
            ].astype(str)
        )

        hits.append(
            temp
        )

    if not hits:

        return pd.DataFrame()

    combined = pd.concat(
        hits,
        ignore_index=True
    )

    # avoid repeated identical rows found through multiple
    # date-like columns only when absolutely identical
    return combined.drop_duplicates()


def search_cells_for_text(
    df,
    patterns
):

    hit_rows = []

    for idx, row in df.iterrows():

        row_text = " | ".join(
            row.astype(str)
            .tolist()
        )

        matched = [
            p
            for p in patterns
            if re.search(
                p,
                row_text,
                flags=re.I
            )
        ]

        if matched:

            hit_rows.append({
                "row_index":
                    idx,

                "matched_patterns":
                    " | ".join(
                        matched
                    ),

                "row_text":
                    row_text,
            })

    return pd.DataFrame(
        hit_rows
    )


# ============================================================
# Load workbook
# ============================================================

if not BOOK.exists():

    raise FileNotFoundError(
        BOOK
    )

xls = pd.ExcelFile(
    BOOK
)

print(
    "=" * 170
)
print(
    "PART 1 — SHEET INVENTORY"
)
print(
    "=" * 170
)

inventory_rows = []

sheet_frames = {}

for sheet in xls.sheet_names:

    try:

        df = pd.read_excel(
            BOOK,
            sheet_name=sheet
        )

    except Exception as e:

        print(
            sheet,
            "READ ERROR:",
            repr(e)
        )

        continue

    df.columns = [
        clean_col(c)
        for c in df.columns
    ]

    sheet_frames[
        sheet
    ] = df

    inventory_rows.append({
        "sheet":
            sheet,

        "rows":
            len(df),

        "columns":
            len(df.columns),

        "column_names":
            " | ".join(
                map(
                    str,
                    df.columns
                )
            ),
    })

inventory = pd.DataFrame(
    inventory_rows
)

print(
    inventory.to_string(
        index=False
    )
)


# ============================================================
# Inspect key sheets
# ============================================================

KEY_SHEETS = [
    "2019 Temp Archive",
    "2018 Temp Archive",
    "Temps",
]

schema_rows = []

for sheet in KEY_SHEETS:

    if sheet not in sheet_frames:
        continue

    df = sheet_frames[
        sheet
    ]

    detected = detect_datetime_columns(
        df
    )

    print(
        "\n" + "=" * 170
    )
    print(
        f"PART 2 — SHEET DETAIL: {sheet}"
    )
    print(
        "=" * 170
    )

    print(
        "ROWS =",
        len(df)
    )

    print(
        "COLUMNS =",
        list(
            df.columns
        )
    )

    print(
        "\nHEAD:"
    )

    print(
        df.head(
            20
        )
        .to_string(
            index=True
        )
    )

    print(
        "\nTAIL:"
    )

    print(
        df.tail(
            20
        )
        .to_string(
            index=True
        )
    )

    print(
        "\nDATE-LIKE COLUMNS:"
    )

    if detected.empty:

        print(
            "NONE"
        )

    else:

        print(
            detected.to_string(
                index=False
            )
        )

        for _, r in detected.iterrows():

            schema_rows.append({
                "sheet":
                    sheet,

                "column":
                    r[
                        "column"
                    ],

                "valid_datetime_rows":
                    r[
                        "valid_datetime_rows"
                    ],

                "min_datetime":
                    r[
                        "min_datetime"
                    ],

                "max_datetime":
                    r[
                        "max_datetime"
                    ],

                "years":
                    r[
                        "years"
                    ],
            })


schema = pd.DataFrame(
    schema_rows
)


# ============================================================
# Extract 2019 target date
# ============================================================

print(
    "\n" + "=" * 170
)
print(
    "PART 3 — 2019 MAY 18 TARGET ROWS"
)
print(
    "=" * 170
)

df2019 = sheet_frames.get(
    "2019 Temp Archive"
)

if df2019 is None:

    target2019 = pd.DataFrame()

    print(
        "2019 Temp Archive missing"
    )

else:

    target2019 = find_target_rows(
        df2019,
        2019,
        TARGETS[
            2019
        ]
    )

    if target2019.empty:

        print(
            "NONE FOUND BY DATETIME PARSING"
        )

    else:

        print(
            target2019.to_string(
                index=False
            )
        )


# ============================================================
# Audit current Temps sheet for 2025
# ============================================================

print(
    "\n" + "=" * 170
)
print(
    "PART 4 — CURRENT TEMPS SHEET / 2025 AUDIT"
)
print(
    "=" * 170
)

temps = sheet_frames.get(
    "Temps"
)

if temps is None:

    target2025 = pd.DataFrame()
    current_text_hits = pd.DataFrame()

    print(
        "Temps sheet missing"
    )

else:

    target2025 = find_target_rows(
        temps,
        2025,
        TARGETS[
            2025
        ]
    )

    current_text_hits = search_cells_for_text(
        temps,
        [
            r"2025",
            r"5/17",
            r"05/17",
            r"17/05",
            r"May\s*17",
            r"May",
        ]
    )

    print(
        "TARGET-DATE ROWS:"
    )

    if target2025.empty:

        print(
            "NONE FOUND BY DATETIME PARSING"
        )

    else:

        print(
            target2025.to_string(
                index=False
            )
        )

    print(
        "\nTEXTUAL DATE/YEAR HITS:"
    )

    if current_text_hits.empty:

        print(
            "NONE"
        )

    else:

        print(
            current_text_hits.to_string(
                index=False
            )
        )


# ============================================================
# Search ALL workbook sheets for 2025 evidence
# ============================================================

print(
    "\n" + "=" * 170
)
print(
    "PART 5 — ALL-SHEET 2025 SEARCH"
)
print(
    "=" * 170
)

all_2025_rows = []

for sheet, df in sheet_frames.items():

    date_hits = find_target_rows(
        df,
        2025,
        TARGETS[
            2025
        ]
    )

    text_hits = search_cells_for_text(
        df,
        [
            r"2025",
            r"5/17/2025",
            r"05/17/2025",
            r"17/05/2025",
            r"2025-05-17",
        ]
    )

    if not date_hits.empty:

        all_2025_rows.append({
            "sheet":
                sheet,

            "hit_type":
                "PARSED_TARGET_DATE",

            "count":
                len(
                    date_hits
                ),
        })

    if not text_hits.empty:

        all_2025_rows.append({
            "sheet":
                sheet,

            "hit_type":
                "TEXT_2025_OR_TARGET_DATE",

            "count":
                len(
                    text_hits
                ),
        })

all_2025 = pd.DataFrame(
    all_2025_rows
)

if all_2025.empty:

    print(
        "NO 2025 EVIDENCE FOUND IN WORKBOOK"
    )

else:

    print(
        all_2025.to_string(
            index=False
        )
    )


# ============================================================
# Save
# ============================================================

INVENTORY_OUT = (
    OUT /
    "ptsc_workbook_sheet_inventory_v1.csv"
)

SCHEMA_OUT = (
    OUT /
    "ptsc_datetime_column_audit_v1.csv"
)

TARGET2019_OUT = (
    OUT /
    "ptsc_2019_05_18_raw_rows_v1.csv"
)

TARGET2025_OUT = (
    OUT /
    "ptsc_2025_05_17_raw_rows_v1.csv"
)

TEXT2025_OUT = (
    OUT /
    "ptsc_current_sheet_2025_text_hits_v1.csv"
)

ALL2025_OUT = (
    OUT /
    "ptsc_all_sheet_2025_hit_summary_v1.csv"
)

inventory.to_csv(
    INVENTORY_OUT,
    index=False
)

schema.to_csv(
    SCHEMA_OUT,
    index=False
)

target2019.to_csv(
    TARGET2019_OUT,
    index=False
)

target2025.to_csv(
    TARGET2025_OUT,
    index=False
)

current_text_hits.to_csv(
    TEXT2025_OUT,
    index=False
)

all_2025.to_csv(
    ALL2025_OUT,
    index=False
)

print(
    "\nOUTPUTS:"
)

for p in [
    INVENTORY_OUT,
    SCHEMA_OUT,
    TARGET2019_OUT,
    TARGET2025_OUT,
    TEXT2025_OUT,
    ALL2025_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_PTSC_2019_2025_AUDIT_V1_COMPLETE"
)
