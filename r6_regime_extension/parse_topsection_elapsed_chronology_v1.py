from pathlib import Path
import re
import pandas as pd
from pypdf import PdfReader

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/official_reports_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/topsection_elapsed_chronology_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

FILES = {
    2018:
        "2018_5320_indycar-topsectiontimes-quals-day1.pdf",

    2019:
        "2019_5565_indycar-topsectiontimes-quals-day1.pdf",

    2025:
        "2025_6656_indycar-topsectiontimes-quals-day1.pdf",
}

# ------------------------------------------------------------
# Example row:
#
# 5 5 Hinchcliffe, James D/H/F 19:38.9855 0.133 4
#
# Interpret first time-like value as session-relative elapsed
# candidate, NOT time-of-day.
# ------------------------------------------------------------

ROW_RE = re.compile(
    r"^\s*"
    r"(?P<rank>\d+)\s+"
    r"(?P<car>[A-Za-z0-9]+)\s+"
    r"(?P<driver>.+?)\s+"
    r"(?P<cet>[A-Z]/[A-Z]/[A-Z])\s+"
    r"(?P<elapsed>\d{2}:\d{2}\.\d{4})\s+"
    r"(?P<section_value>\d+\.\d{3})\s+"
    r"(?P<lap>\d+)"
    r"\s*$"
)

SECTION_RE = re.compile(
    r"Section:\s*(.+?)\s+Length:\s*([0-9.]+)\s*mile",
    flags=re.I
)

def elapsed_to_seconds(token):

    mm, ss = token.split(":")

    return (
        int(mm) * 60
        + float(ss)
    )


records = []
page_inventory = []

for year, filename in FILES.items():

    pdf = SRC / filename

    print("\n" + "=" * 150)
    print(year, filename)
    print("=" * 150)

    reader = PdfReader(
        str(pdf)
    )

    for page_no, page in enumerate(
        reader.pages,
        start=1
    ):

        try:

            text = page.extract_text(
                extraction_mode="layout"
            ) or ""

        except Exception:

            text = page.extract_text() or ""

        lines = [
            re.sub(
                r"\s+",
                " ",
                line
            ).strip()
            for line in text.splitlines()
            if line.strip()
        ]

        section_name = None
        section_length_miles = None

        for line in lines:

            sm = SECTION_RE.search(
                line
            )

            if sm:

                section_name = (
                    sm.group(1)
                    .strip()
                )

                section_length_miles = float(
                    sm.group(2)
                )

                break

        parsed_here = 0

        for line_no, line in enumerate(
            lines,
            start=1
        ):

            m = ROW_RE.match(
                line
            )

            if not m:
                continue

            x = m.groupdict()

            elapsed_s = elapsed_to_seconds(
                x["elapsed"]
            )

            records.append({
                "year":
                    year,

                "file":
                    filename,

                "page":
                    page_no,

                "line_no":
                    line_no,

                "section":
                    section_name,

                "section_length_miles":
                    section_length_miles,

                "section_rank":
                    int(
                        x["rank"]
                    ),

                "car_number":
                    x["car"],

                "driver_name":
                    re.sub(
                        r"\s+",
                        " ",
                        x["driver"]
                    ).strip(),

                "cet":
                    x["cet"],

                "session_elapsed":
                    x["elapsed"],

                "session_elapsed_s":
                    elapsed_s,

                "reported_section_value":
                    float(
                        x["section_value"]
                    ),

                "lap_number":
                    int(
                        x["lap"]
                    ),

                "raw_line":
                    line,
            })

            parsed_here += 1

        page_inventory.append({
            "year":
                year,

            "file":
                filename,

            "page":
                page_no,

            "section":
                section_name,

            "section_length_miles":
                section_length_miles,

            "parsed_rows":
                parsed_here,
        })

data = pd.DataFrame(
    records
)

pages = pd.DataFrame(
    page_inventory
)

if data.empty:
    raise RuntimeError(
        "No Top Section Times rows parsed"
    )

# ------------------------------------------------------------
# Driver normalization
# ------------------------------------------------------------

data[
    "driver_key"
] = (
    data[
        "driver_name"
    ]
    .astype(str)
    .str.lower()
    .str.replace(
        r"\(r\)",
        "",
        regex=True
    )
    .str.replace(
        r"[^a-z0-9]+",
        "",
        regex=True
    )
)

data[
    "car_key"
] = (
    data[
        "car_number"
    ]
    .astype(str)
    .str.upper()
    .str.strip()
)

data[
    "entrant_key"
] = (
    data[
        "driver_key"
    ]
    + "__"
    + data[
        "car_key"
    ]
)

# ------------------------------------------------------------
# Basic chronology diagnostics
# ------------------------------------------------------------

data[
    "elapsed_order_within_year"
] = (
    data.groupby(
        "year"
    )[
        "session_elapsed_s"
    ]
    .rank(
        method="dense"
    )
    .astype(int)
)

# Same entrant may appear multiple times at different elapsed times.
entrant_elapsed = (
    data[
        [
            "year",
            "entrant_key",
            "driver_name",
            "car_number",
            "session_elapsed",
            "session_elapsed_s",
            "lap_number",
            "section",
            "page",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        [
            "year",
            "entrant_key",
            "session_elapsed_s",
            "lap_number",
        ]
    )
)

# ------------------------------------------------------------
# Candidate timing events:
# unique entrant + elapsed + lap
# ------------------------------------------------------------

events = (
    data.groupby(
        [
            "year",
            "entrant_key",
            "driver_name",
            "car_number",
            "session_elapsed",
            "session_elapsed_s",
            "lap_number",
        ],
        as_index=False
    )
    .agg(
        section_count=(
            "section",
            "nunique"
        ),

        page_count=(
            "page",
            "nunique"
        ),
    )
)

events = events.sort_values(
    [
        "year",
        "session_elapsed_s",
        "driver_name",
        "lap_number",
    ]
)

# ------------------------------------------------------------
# Per-year coverage
# ------------------------------------------------------------

summary_rows = []

for year, g in data.groupby(
    "year"
):

    e = events[
        events[
            "year"
        ]
        == year
    ]

    summary_rows.append({
        "year":
            int(year),

        "parsed_topsection_rows":
            len(g),

        "unique_sections":
            g[
                "section"
            ].nunique(),

        "unique_drivers":
            g[
                "driver_key"
            ].nunique(),

        "unique_driver_car":
            g[
                "entrant_key"
            ].nunique(),

        "unique_elapsed_tokens":
            g[
                "session_elapsed_s"
            ].nunique(),

        "unique_driver_elapsed_lap_events":
            len(e),

        "min_elapsed_s":
            g[
                "session_elapsed_s"
            ].min(),

        "max_elapsed_s":
            g[
                "session_elapsed_s"
            ].max(),
    })

summary = pd.DataFrame(
    summary_rows
)

# ------------------------------------------------------------
# Repeat-driver timing inventory
# ------------------------------------------------------------

repeat_event_counts = (
    events.groupby(
        [
            "year",
            "entrant_key",
            "driver_name",
            "car_number",
        ]
    )
    .size()
    .reset_index(
        name="timing_event_rows"
    )
)

repeat_event_counts = (
    repeat_event_counts[
        repeat_event_counts[
            "timing_event_rows"
        ]
        >= 2
    ]
    .sort_values(
        [
            "year",
            "timing_event_rows",
        ],
        ascending=[
            True,
            False,
        ]
    )
)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

DATA_OUT = (
    OUT /
    "topsection_elapsed_rows_v1.csv"
)

EVENT_OUT = (
    OUT /
    "topsection_elapsed_events_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "topsection_elapsed_summary_v1.csv"
)

REPEAT_OUT = (
    OUT /
    "topsection_repeat_timing_inventory_v1.csv"
)

PAGE_OUT = (
    OUT /
    "topsection_page_parse_inventory_v1.csv"
)

data.to_csv(
    DATA_OUT,
    index=False
)

events.to_csv(
    EVENT_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

repeat_event_counts.to_csv(
    REPEAT_OUT,
    index=False
)

pages.to_csv(
    PAGE_OUT,
    index=False
)

# ------------------------------------------------------------
# Console
# ------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 1 — TOP SECTION ELAPSED SUMMARY")
print("=" * 150)

print(
    summary.to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 2 — EARLIEST/LATEST ELAPSED EVENTS")
print("=" * 150)

for year in FILES:

    x = events[
        events[
            "year"
        ]
        == year
    ]

    print(
        f"\nYEAR {year} EARLIEST"
    )

    print(
        x[
            [
                "session_elapsed",
                "driver_name",
                "car_number",
                "lap_number",
                "section_count",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    print(
        f"\nYEAR {year} LATEST"
    )

    print(
        x[
            [
                "session_elapsed",
                "driver_name",
                "car_number",
                "lap_number",
                "section_count",
            ]
        ]
        .tail(20)
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 150)
print("PART 3 — REPEAT DRIVER TIMING EVENT INVENTORY")
print("=" * 150)

print(
    repeat_event_counts
    .head(150)
    .to_string(
        index=False
    )
)

print("\nOUTPUTS:")
print(
    DATA_OUT.relative_to(
        ROOT
    )
)
print(
    EVENT_OUT.relative_to(
        ROOT
    )
)
print(
    SUMMARY_OUT.relative_to(
        ROOT
    )
)
print(
    REPEAT_OUT.relative_to(
        ROOT
    )
)
print(
    PAGE_OUT.relative_to(
        ROOT
    )
)

print(
    "\nR6_TOPSECTION_ELAPSED_CHRONOLOGY_V1_COMPLETE"
)
