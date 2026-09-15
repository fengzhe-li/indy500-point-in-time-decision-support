from pathlib import Path
import json
import re

import pandas as pd

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

WEATHER = ROOT / "weather"

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_weather_source_availability_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

TARGET_YEARS = {
    "2018",
    "2019",
    "2025",
    "2026",
}

WEATHER_TERMS = [
    "track",
    "track_temp",
    "track temperature",
    "asphalt",
    "ambient",
    "air_temp",
    "temperature",
    "wind",
    "gust",
    "shortwave",
    "radiation",
    "cloud",
    "pressure",
    "humidity",
    "dewpoint",
    "dew_point",
]

inventory_rows = []
table_rows = []
year_hit_rows = []

print(
    "=" * 160
)
print(
    "PART 1 — WEATHER FILE INVENTORY"
)
print(
    "=" * 160
)

if not WEATHER.exists():
    raise FileNotFoundError(
        f"Weather directory missing: {WEATHER}"
    )

files = sorted(
    p
    for p in WEATHER.rglob("*")
    if p.is_file()
)

for p in files:

    rel = str(
        p.relative_to(ROOT)
    )

    suffix = p.suffix.lower()

    size = p.stat().st_size

    filename_years = sorted(
        y
        for y in TARGET_YEARS
        if y in rel
    )

    inventory_rows.append({
        "path":
            rel,

        "suffix":
            suffix,

        "bytes":
            size,

        "filename_target_year_hits":
            " | ".join(
                filename_years
            ),
    })

inventory = pd.DataFrame(
    inventory_rows
)

print(
    inventory[
        inventory[
            "filename_target_year_hits"
        ]
        != ""
    ]
    .to_string(
        index=False
    )
)

# ============================================================
# Inspect structured files
# ============================================================

for p in files:

    suffix = p.suffix.lower()

    if suffix not in {
        ".csv",
        ".xlsx",
        ".xls",
        ".json",
    }:
        continue

    rel = str(
        p.relative_to(ROOT)
    )

    try:

        tables = {}

        if suffix == ".csv":

            df = pd.read_csv(
                p,
                low_memory=False
            )

            tables["CSV"] = df

        elif suffix in {
            ".xlsx",
            ".xls",
        }:

            xls = pd.ExcelFile(
                p
            )

            for sheet in xls.sheet_names:

                try:

                    df = pd.read_excel(
                        p,
                        sheet_name=sheet
                    )

                    tables[
                        str(sheet)
                    ] = df

                except Exception:
                    continue

        elif suffix == ".json":

            payload = json.loads(
                p.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            )

            if isinstance(
                payload,
                list
            ):

                try:
                    tables["JSON"] = pd.DataFrame(
                        payload
                    )
                except Exception:
                    pass

            elif isinstance(
                payload,
                dict
            ):

                # only simple dict/list tables
                for k, v in payload.items():

                    if isinstance(
                        v,
                        list
                    ):

                        try:

                            tables[
                                str(k)
                            ] = pd.DataFrame(
                                v
                            )

                        except Exception:
                            pass

        for table_name, df in tables.items():

            if not isinstance(
                df,
                pd.DataFrame
            ):
                continue

            cols = [
                str(c)
                for c in df.columns
            ]

            cols_low = [
                c.lower()
                for c in cols
            ]

            weather_cols = [
                cols[i]
                for i, c in enumerate(
                    cols_low
                )
                if any(
                    term in c
                    for term in WEATHER_TERMS
                )
            ]

            text_sample = (
                df.head(500)
                .astype(str)
                .to_string()
            )

            year_hits = sorted(
                y
                for y in TARGET_YEARS
                if (
                    y in text_sample
                    or
                    y in table_name
                    or
                    y in rel
                )
            )

            table_rows.append({
                "path":
                    rel,

                "table":
                    table_name,

                "rows":
                    len(df),

                "columns":
                    len(df.columns),

                "weather_columns":
                    " | ".join(
                        weather_cols
                    ),

                "target_year_hits":
                    " | ".join(
                        year_hits
                    ),
            })

            for y in year_hits:

                year_hit_rows.append({
                    "year":
                        int(y),

                    "path":
                        rel,

                    "table":
                        table_name,

                    "rows":
                        len(df),

                    "weather_columns":
                        " | ".join(
                            weather_cols
                        ),
                })

    except Exception as e:

        table_rows.append({
            "path":
                rel,

            "table":
                "READ_ERROR",

            "rows":
                None,

            "columns":
                None,

            "weather_columns":
                None,

            "target_year_hits":
                None,

            "error":
                repr(e),
        })


tables = pd.DataFrame(
    table_rows
)

year_hits = pd.DataFrame(
    year_hit_rows
)

# ============================================================
# Save
# ============================================================

INVENTORY_OUT = (
    OUT /
    "weather_file_inventory_v1.csv"
)

TABLE_OUT = (
    OUT /
    "weather_structured_table_inventory_v1.csv"
)

YEAR_OUT = (
    OUT /
    "weather_target_year_hits_v1.csv"
)

inventory.to_csv(
    INVENTORY_OUT,
    index=False
)

tables.to_csv(
    TABLE_OUT,
    index=False
)

year_hits.to_csv(
    YEAR_OUT,
    index=False
)

# ============================================================
# Console
# ============================================================

print(
    "\n" + "=" * 160
)
print(
    "PART 2 — STRUCTURED TABLES WITH TARGET YEARS"
)
print(
    "=" * 160
)

target_tables = tables[
    tables[
        "target_year_hits"
    ]
    .fillna("")
    != ""
]

if target_tables.empty:

    print(
        "NONE"
    )

else:

    print(
        target_tables[
            [
                "path",
                "table",
                "rows",
                "columns",
                "weather_columns",
                "target_year_hits",
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
    "PART 3 — TARGET-YEAR WEATHER SOURCE SUMMARY"
)
print(
    "=" * 160
)

if year_hits.empty:

    print(
        "NONE"
    )

else:

    print(
        year_hits[
            [
                "year",
                "path",
                "table",
                "rows",
                "weather_columns",
            ]
        ]
        .sort_values(
            [
                "year",
                "path",
                "table",
            ]
        )
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 160
)
print(
    "PART 4 — TRACK / ASPHALT TEMPERATURE CANDIDATES"
)
print(
    "=" * 160
)

track_mask = (
    tables[
        "weather_columns"
    ]
    .fillna("")
    .str.contains(
        r"track|asphalt",
        case=False,
        regex=True
    )
)

track_tables = tables[
    track_mask
]

if track_tables.empty:

    print(
        "NONE"
    )

else:

    print(
        track_tables[
            [
                "path",
                "table",
                "rows",
                "weather_columns",
                "target_year_hits",
            ]
        ]
        .to_string(
            index=False
        )
    )


print(
    "\nOUTPUTS:"
)

for p in [
    INVENTORY_OUT,
    TABLE_OUT,
    YEAR_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_WEATHER_SOURCE_AVAILABILITY_V1_COMPLETE"
)
