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
    "r6_regime_extension/output/chronology_audit_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

FILES = {
    2018: [
        "2018_5320_indycar-sectionresults-quals-day1.pdf",
        "2018_5320_indycar-topsectiontimes-quals-day1.pdf",
    ],
    2019: [
        "2019_5565_indycar-sectionresults-quals-day1.pdf",
        "2019_5565_indycar-topsectiontimes-quals-day1.pdf",
    ],
    2025: [
        "2025_6656_indycar-sectionresults-quals-day1.pdf",
        "2025_6656_indycar-topsectiontimes-quals-day1.pdf",
    ],
}

# ------------------------------------------------------------
# Local daytime-looking clock
# ------------------------------------------------------------
#
# deliberately exclude 00:39 / 02:37 qualifying elapsed times
#
CLOCK_RE = re.compile(
    r"\b(?:0?[8-9]|1[0-9]|20):[0-5]\d"
    r"(?::[0-5]\d(?:\.\d+)?)?"
    r"(?:\s*(?:AM|PM))?\b",
    flags=re.I
)

HEADER_TERMS = [
    "time of day",
    "timeofday",
    "clock",
    "elapsed",
    "session time",
    "time",
    "lap time",
    "section time",
    "start",
    "finish",
    "timestamp",
]

# high-value repeat drivers
DRIVERS = [
    # 2018
    "Daly",
    "Dixon",
    "Hunter-Reay",
    "Mann",
    "Rahal",
    "Rossi",

    # 2019
    "Alonso",
    "Castroneves",
    "Chilton",
    "Hanley",
    "Herta",
    "Hildebrand",
    "Hinchcliffe",
    "Karam",
    "King",
    "Leist",
    "O'Ward",
    "Rosenqvist",
    "Veach",

    # 2025
    "Andretti",
    "Carpenter",
    "DeFrancesco",
    "Ferrucci",
    "Foster",
    "Harvey",
    "Ilott",
    "Kirkwood",
    "Larson",
    "Lundgaard",
    "Malukas",
    "Power",
    "Rasmussen",
    "Robb",
    "Sato",
    "Siegel",
    "Veekay",
]

clock_rows = []
header_rows = []
driver_rows = []
page_rows = []

for year, files in FILES.items():

    for filename in files:

        pdf = SRC / filename

        print("\n" + "=" * 150)
        print(year, filename)
        print("=" * 150)

        if not pdf.exists():

            print("MISSING")
            continue

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
                    x
                ).strip()
                for x in text.splitlines()
                if x.strip()
            ]

            page_rows.append({
                "year": year,
                "file": filename,
                "page": page_no,
                "line_count": len(lines),
                "char_count": len(text),
            })

            # ------------------------------------------------
            # first lines = header clues
            # ------------------------------------------------

            for line_no, line in enumerate(
                lines[:25],
                start=1
            ):

                low = line.lower()

                if any(
                    term in low
                    for term in HEADER_TERMS
                ):

                    header_rows.append({
                        "year": year,
                        "file": filename,
                        "page": page_no,
                        "line_no": line_no,
                        "raw_line": line,
                    })

            # ------------------------------------------------
            # every line: clock-looking values
            # ------------------------------------------------

            for line_no, line in enumerate(
                lines,
                start=1
            ):

                clocks = CLOCK_RE.findall(
                    line
                )

                if clocks:

                    clock_rows.append({
                        "year": year,
                        "file": filename,
                        "page": page_no,
                        "line_no": line_no,
                        "clock_tokens":
                            " | ".join(clocks),
                        "raw_line": line,
                    })

            # ------------------------------------------------
            # repeat-driver contexts
            # ------------------------------------------------

            for line_no, line in enumerate(
                lines,
                start=1
            ):

                hits = [
                    d
                    for d in DRIVERS
                    if d.lower()
                    in line.lower()
                ]

                if hits:

                    lo = max(
                        0,
                        line_no - 3
                    )

                    hi = min(
                        len(lines),
                        line_no + 2
                    )

                    context = " || ".join(
                        lines[lo:hi]
                    )

                    driver_rows.append({
                        "year": year,
                        "file": filename,
                        "page": page_no,
                        "line_no": line_no,
                        "drivers":
                            " | ".join(hits),
                        "clock_tokens":
                            " | ".join(
                                CLOCK_RE.findall(
                                    context
                                )
                            ),
                        "context":
                            context,
                    })

clock_df = pd.DataFrame(
    clock_rows
)

header_df = pd.DataFrame(
    header_rows
)

driver_df = pd.DataFrame(
    driver_rows
)

page_df = pd.DataFrame(
    page_rows
)

CLOCK_OUT = (
    OUT /
    "chronology_daytime_clock_candidates_v1.csv"
)

HEADER_OUT = (
    OUT /
    "chronology_header_candidates_v1.csv"
)

DRIVER_OUT = (
    OUT /
    "chronology_repeat_driver_contexts_v1.csv"
)

PAGE_OUT = (
    OUT /
    "chronology_page_inventory_v1.csv"
)

clock_df.to_csv(
    CLOCK_OUT,
    index=False
)

header_df.to_csv(
    HEADER_OUT,
    index=False
)

driver_df.to_csv(
    DRIVER_OUT,
    index=False
)

page_df.to_csv(
    PAGE_OUT,
    index=False
)

print("\n" + "=" * 150)
print("PART 1 — DAYTIME CLOCK CANDIDATE COUNTS")
print("=" * 150)

if clock_df.empty:

    print("NO DAYTIME CLOCK CANDIDATES")

else:

    print(
        clock_df.groupby(
            [
                "year",
                "file"
            ]
        )
        .size()
        .reset_index(
            name="clock_candidate_lines"
        )
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 150)
print("PART 2 — DAYTIME CLOCK EXAMPLES")
print("=" * 150)

if clock_df.empty:

    print("NONE")

else:

    print(
        clock_df[
            [
                "year",
                "file",
                "page",
                "line_no",
                "clock_tokens",
                "raw_line",
            ]
        ]
        .head(150)
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 150)
print("PART 3 — HEADER / TIME FIELD CANDIDATES")
print("=" * 150)

if header_df.empty:

    print("NONE")

else:

    print(
        header_df[
            [
                "year",
                "file",
                "page",
                "line_no",
                "raw_line",
            ]
        ]
        .head(150)
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 150)
print("PART 4 — REPEAT DRIVER CONTEXTS WITH CLOCK TOKENS")
print("=" * 150)

if driver_df.empty:

    print("NONE")

else:

    x = driver_df[
        driver_df[
            "clock_tokens"
        ]
        .astype(str)
        .str.len()
        > 0
    ]

    if x.empty:

        print(
            "REPEAT DRIVERS FOUND, "
            "BUT NO DAYTIME CLOCK TOKENS "
            "IN LOCAL CONTEXT"
        )

    else:

        print(
            x[
                [
                    "year",
                    "file",
                    "page",
                    "line_no",
                    "drivers",
                    "clock_tokens",
                    "context",
                ]
            ]
            .head(200)
            .to_string(
                index=False
            )
        )


print("\nOUTPUTS:")
print(
    CLOCK_OUT.relative_to(ROOT)
)
print(
    HEADER_OUT.relative_to(ROOT)
)
print(
    DRIVER_OUT.relative_to(ROOT)
)
print(
    PAGE_OUT.relative_to(ROOT)
)

print(
    "\nR6_CHRONOLOGY_TIMEOFDAY_AUDIT_V1_COMPLETE"
)
