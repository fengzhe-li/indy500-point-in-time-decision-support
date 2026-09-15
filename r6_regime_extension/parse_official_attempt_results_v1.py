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
    "r6_regime_extension/output/attempt_pdf_parse"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

FILES = {
    2018:
        "2018_5320_indycar-qualresults-Day1.pdf",

    2019:
        "2019_5565_indycar-qualresults.pdf",

    2025:
        "2025_6656_indycar-results-quals-day1.pdf",

    2026:
        "2026_6835_indycar-results-quals-poleday.pdf",
}

# ------------------------------------------------------------
# Patterns
# ------------------------------------------------------------

# four lap times like 39.3460
LAP_RE = re.compile(
    r"\b(\d{2}\.\d{4})\b"
)

# total qualifying time like 02:37.2607
TOTAL_RE = re.compile(
    r"\b(\d{2}:\d{2}\.\d{4})\b"
)

# average speed normally ~220-235 mph
SPEED_RE = re.compile(
    r"\b(1\d{2}\.\d{3}|2\d{2}\.\d{3})\b"
)

STATUS_TERMS = [
    "Withdrawn",
    "Retired",
    "Failed Attempt",
    "Waved Off",
    "No Attempt",
    "On Bubble",
    "Qualified",
]

def normalize_spaces(s):
    return re.sub(
        r"\s+",
        " ",
        s
    ).strip()


def extract_layout_text(pdf_path):

    reader = PdfReader(
        str(pdf_path)
    )

    texts = []

    for page in reader.pages:

        try:
            text = page.extract_text(
                extraction_mode="layout"
            ) or ""
        except Exception:
            text = page.extract_text() or ""

        texts.append(text)

    return "\n".join(texts)


def detect_status(line):

    low = line.lower()

    for status in STATUS_TERMS:

        if status.lower() in low:
            return status

    return None


all_lines = []
candidate_rows = []

print("=" * 150)
print("PART 1 — RAW LAYOUT EXTRACTION")
print("=" * 150)

for year, filename in FILES.items():

    pdf = SRC / filename

    print("\nYEAR", year)
    print("FILE", filename)

    if not pdf.exists():

        print("MISSING")
        continue

    text = extract_layout_text(
        pdf
    )

    TXT_OUT = (
        OUT /
        f"{year}_results_layout.txt"
    )

    TXT_OUT.write_text(
        text,
        encoding="utf-8"
    )

    lines = [
        normalize_spaces(x)
        for x in text.splitlines()
        if normalize_spaces(x)
    ]

    print(
        "nonempty lines =",
        len(lines)
    )

    # print full lines likely containing qualifying records
    for line_no, line in enumerate(
        lines,
        start=1
    ):

        laps = LAP_RE.findall(
            line
        )

        totals = TOTAL_RE.findall(
            line
        )

        speeds = SPEED_RE.findall(
            line
        )

        rec = {
            "year": year,
            "line_no": line_no,
            "raw_line": line,
            "lap_token_count":
                len(laps),
            "total_token_count":
                len(totals),
            "speed_token_count":
                len(speeds),
            "status":
                detect_status(line),
        }

        all_lines.append(rec)

        # qualifying row candidate:
        # usually ≥4 lap tokens or explicit attempt status
        if (
            len(laps) >= 4
            or detect_status(line)
            is not None
        ):

            candidate_rows.append(
                rec
            )

    print(
        "candidate rows =",
        sum(
            x["year"] == year
            for x in candidate_rows
        )
    )


lines_df = pd.DataFrame(
    all_lines
)

cand_df = pd.DataFrame(
    candidate_rows
)

LINES_OUT = (
    OUT /
    "official_results_all_layout_lines_v1.csv"
)

CAND_OUT = (
    OUT /
    "official_results_attempt_row_candidates_v1.csv"
)

lines_df.to_csv(
    LINES_OUT,
    index=False
)

cand_df.to_csv(
    CAND_OUT,
    index=False
)

# ------------------------------------------------------------
# diagnostic printing
# ------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 2 — ATTEMPT ROW CANDIDATES BY YEAR")
print("=" * 150)

for year in FILES:

    x = cand_df[
        cand_df["year"]
        == year
    ]

    print(
        "\nYEAR",
        year,
        "candidate rows =",
        len(x)
    )

    print(
        x[
            [
                "line_no",
                "lap_token_count",
                "total_token_count",
                "speed_token_count",
                "status",
                "raw_line",
            ]
        ]
        .head(120)
        .to_string(
            index=False
        )
    )


# ------------------------------------------------------------
# status inventory
# ------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 3 — STATUS INVENTORY")
print("=" * 150)

status_df = (
    cand_df[
        cand_df["status"]
        .notna()
    ]
)

if status_df.empty:

    print(
        "NO EXPLICIT STATUS ROWS"
    )

else:

    print(
        status_df.groupby(
            [
                "year",
                "status"
            ]
        )
        .size()
        .reset_index(
            name="rows"
        )
        .to_string(
            index=False
        )
    )

    print(
        "\nSTATUS ROW DETAILS:"
    )

    print(
        status_df[
            [
                "year",
                "line_no",
                "status",
                "raw_line",
            ]
        ]
        .to_string(
            index=False
        )
    )


# ------------------------------------------------------------
# count likely complete four-lap rows
# ------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 4 — FOUR-LAP ROW COUNTS")
print("=" * 150)

fourlap = cand_df[
    cand_df[
        "lap_token_count"
    ]
    >= 4
].copy()

summary = (
    fourlap.groupby(
        "year"
    )
    .size()
    .reset_index(
        name="rows_with_4plus_lap_tokens"
    )
)

print(
    summary.to_string(
        index=False
    )
)

SUMMARY_OUT = (
    OUT /
    "official_results_fourlap_row_summary_v1.csv"
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

print("\nOUTPUTS:")
print(
    LINES_OUT.relative_to(ROOT)
)
print(
    CAND_OUT.relative_to(ROOT)
)
print(
    SUMMARY_OUT.relative_to(ROOT)
)

print(
    "\nR6_OFFICIAL_ATTEMPT_RESULTS_PARSE_V1_COMPLETE"
)
