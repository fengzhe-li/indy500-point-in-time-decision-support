from pathlib import Path
import re
import pandas as pd
import fitz  # PyMuPDF

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/official_reports_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/section_results_rotation_safe_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

FILES = {
    2018:
        "2018_5320_indycar-sectionresults-quals-day1.pdf",

    2019:
        "2019_5565_indycar-sectionresults-quals-day1.pdf",

    2025:
        "2025_6656_indycar-sectionresults-quals-day1.pdf",
}

KEYWORDS = [
    "elapsed",
    "session",
    "time of day",
    "timestamp",
    "clock",
    "lap",
    "time",
    "start",
    "finish",
    "rank",
    "car",
    "driver",
    "section",
    "speed",
]

# deliberately broad:
# do NOT interpret semantics yet.
TIME_TOKEN_RE = re.compile(
    r"\b\d{1,3}:\d{2}(?:\.\d{1,4})?\b"
)

header_rows = []
time_rows = []
page_rows = []

for year, filename in FILES.items():

    pdf_path = SRC / filename

    print("\n" + "=" * 160)
    print("YEAR", year)
    print("FILE", filename)
    print("=" * 160)

    if not pdf_path.exists():
        print("MISSING")
        continue

    doc = fitz.open(
        str(pdf_path)
    )

    full_dump = []

    for page_index in range(
        len(doc)
    ):

        page = doc[
            page_index
        ]

        page_no = (
            page_index + 1
        )

        # ----------------------------------------------------
        # Rotation-safe extraction
        # ----------------------------------------------------

        words = page.get_text(
            "words",
            sort=True
        )

        blocks = page.get_text(
            "blocks",
            sort=True
        )

        # sorted text
        text = page.get_text(
            "text",
            sort=True
        )

        lines = [
            re.sub(
                r"\s+",
                " ",
                x
            ).strip()
            for x in text.splitlines()
            if x.strip()
        ]

        full_dump.append(
            "\n"
            + "=" * 100
            + f"\nPAGE {page_no}\n"
            + "=" * 100
            + "\n"
            + "\n".join(lines)
        )

        page_rows.append({
            "year":
                year,

            "file":
                filename,

            "page":
                page_no,

            "page_rotation":
                page.rotation,

            "word_count":
                len(words),

            "block_count":
                len(blocks),

            "line_count":
                len(lines),

            "char_count":
                len(text),
        })

        # ----------------------------------------------------
        # Header / semantic clues
        # ----------------------------------------------------

        for line_no, line in enumerate(
            lines,
            start=1
        ):

            low = line.lower()

            hits = [
                kw
                for kw in KEYWORDS
                if kw in low
            ]

            if hits:

                header_rows.append({
                    "year":
                        year,

                    "file":
                        filename,

                    "page":
                        page_no,

                    "line_no":
                        line_no,

                    "keyword_hits":
                        " | ".join(
                            hits
                        ),

                    "raw_line":
                        line,
                })

            tokens = TIME_TOKEN_RE.findall(
                line
            )

            if tokens:

                time_rows.append({
                    "year":
                        year,

                    "file":
                        filename,

                    "page":
                        page_no,

                    "line_no":
                        line_no,

                    "time_tokens":
                        " | ".join(
                            tokens
                        ),

                    "raw_line":
                        line,
                })

    txt_path = (
        OUT /
        f"{year}_sectionresults_rotation_safe.txt"
    )

    txt_path.write_text(
        "\n".join(
            full_dump
        ),
        encoding="utf-8"
    )

    print(
        "pages =",
        len(doc)
    )

    doc.close()


headers = pd.DataFrame(
    header_rows
)

times = pd.DataFrame(
    time_rows
)

pages = pd.DataFrame(
    page_rows
)

HEADER_OUT = (
    OUT /
    "sectionresults_header_semantic_candidates_v1.csv"
)

TIME_OUT = (
    OUT /
    "sectionresults_time_token_candidates_v1.csv"
)

PAGE_OUT = (
    OUT /
    "sectionresults_page_inventory_v1.csv"
)

headers.to_csv(
    HEADER_OUT,
    index=False
)

times.to_csv(
    TIME_OUT,
    index=False
)

pages.to_csv(
    PAGE_OUT,
    index=False
)

# ============================================================
# Console
# ============================================================

print("\n" + "=" * 160)
print("PART 1 — ROTATION-SAFE PAGE INVENTORY")
print("=" * 160)

print(
    pages.to_string(
        index=False
    )
)


print("\n" + "=" * 160)
print("PART 2 — UNIQUE HEADER / SEMANTIC LINES")
print("=" * 160)

if headers.empty:

    print("NONE")

else:

    unique_headers = (
        headers[
            [
                "year",
                "keyword_hits",
                "raw_line",
            ]
        ]
        .drop_duplicates()
    )

    print(
        unique_headers
        .head(250)
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 160)
print("PART 3 — TIME-LIKE TOKEN COUNTS")
print("=" * 160)

if times.empty:

    print("NO TIME-LIKE TOKENS")

else:

    print(
        times.groupby(
            [
                "year",
                "file"
            ]
        )
        .size()
        .reset_index(
            name="time_token_lines"
        )
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 160)
print("PART 4 — TIME-LIKE TOKEN EXAMPLES")
print("=" * 160)

if times.empty:

    print("NONE")

else:

    print(
        times[
            [
                "year",
                "page",
                "line_no",
                "time_tokens",
                "raw_line",
            ]
        ]
        .head(250)
        .to_string(
            index=False
        )
    )


print("\n" + "=" * 160)
print("PART 5 — FIRST PAGE TEXT BY YEAR")
print("=" * 160)

for year in FILES:

    txt_path = (
        OUT /
        f"{year}_sectionresults_rotation_safe.txt"
    )

    if not txt_path.exists():
        continue

    text = txt_path.read_text(
        encoding="utf-8"
    )

    # print only first page block
    chunks = text.split(
        "=" * 100
    )

    print(
        "\nYEAR",
        year
    )

    print(
        "\n".join(
            chunks[:3]
        )[:8000]
    )


print("\nOUTPUTS:")
print(
    HEADER_OUT.relative_to(
        ROOT
    )
)
print(
    TIME_OUT.relative_to(
        ROOT
    )
)
print(
    PAGE_OUT.relative_to(
        ROOT
    )
)

print(
    "\nR6_SECTION_RESULTS_ROTATION_SAFE_AUDIT_V1_COMPLETE"
)
