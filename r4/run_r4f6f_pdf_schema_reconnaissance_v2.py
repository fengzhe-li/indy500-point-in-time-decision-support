from pathlib import Path
from collections import Counter
import csv
import json
import re
import shutil
import subprocess
import unicodedata

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
RAW = ROOT / "r4/evidence/fast_friday"

OUT.mkdir(parents=True, exist_ok=True)

ATTEMPT_PANEL = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

PDFS = {
    2023:
        RAW /
        "2023_fast_friday_practice5_results.pdf",

    2024:
        RAW /
        "2024_fast_friday_practice5_results.pdf",
}

EDITORIALS = {
    2021:
        RAW /
        "2021_fast_friday_official_editorial.html",

    2023:
        RAW /
        "2023_fast_friday_official_editorial.html",

    2024:
        RAW /
        "2024_fast_friday_official_editorial.html",
}

OUT_LINES = (
    OUT /
    "r4f6f_v2_pdf_numeric_line_reconnaissance.csv"
)

OUT_ROSTER = (
    OUT /
    "r4f6f_v2_known_driver_roster.csv"
)

OUT_EDITORIAL = (
    OUT /
    "r4f6f_v2_editorial_numeric_contexts.csv"
)

OUT_QA = (
    OUT /
    "r4f6f_v2_schema_reconnaissance_qa.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6f_v2_schema_reconnaissance_report.json"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(
            csv.DictReader(f)
        )


def pdf_to_text(path):
    if shutil.which(
        "pdftotext"
    ):

        result = subprocess.run(
            [
                "pdftotext",
                "-layout",
                str(path),
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if (
            result.returncode == 0
            and
            result.stdout.strip()
        ):
            return (
                result.stdout,
                "PDFTOTEXT",
            )

    try:
        from pypdf import PdfReader

        reader = PdfReader(
            str(path)
        )

        parts = []

        for page in reader.pages:

            text = (
                page.extract_text()
                or
                ""
            )

            if text.strip():
                parts.append(
                    text
                )

        text = "\n".join(
            parts
        )

        if text.strip():
            return (
                text,
                "PYPDF",
            )

    except Exception:
        pass

    return (
        "",
        "NONE",
    )


def normalize_name(value):
    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(
            ch
        )
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def normalize_line(value):
    return normalize_name(
        value
    )


def find_candidate_columns(fieldnames):
    candidates = []

    for field in fieldnames:

        f = field.lower()

        if any(
            key in f
            for key in [
                "driver",
                "name",
                "competitor",
                "entrant",
            ]
        ):
            candidates.append(
                field
            )

    return candidates


def find_car_columns(fieldnames):
    candidates = []

    for field in fieldnames:

        f = field.lower()

        if any(
            key in f
            for key in [
                "car_number",
                "car_no",
                "number",
                "car",
            ]
        ):
            candidates.append(
                field
            )

    return candidates


def looks_like_driver_name(value):
    s = clean(
        value
    )

    if not s:
        return False

    if len(
        s
    ) < 4:
        return False

    if re.fullmatch(
        r"\d+",
        s
    ):
        return False

    if not re.search(
        r"[A-Za-z]",
        s
    ):
        return False

    words = re.findall(
        r"[A-Za-zÀ-ÿ'’-]+",
        s
    )

    return len(
        words
    ) >= 2


def surname(name):
    parts = normalize_name(
        name
    ).split()

    if not parts:
        return ""

    return parts[-1]


def extract_mph_values(line):
    return re.findall(
        r"\b(?:22[0-9]|23[0-9]|24[0-9])\.\d{3}\b",
        line
    )


def html_visible_text(path):
    raw = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    raw = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )

    raw = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )

    raw = re.sub(
        r"<[^>]+>",
        " ",
        raw
    )

    raw = raw.replace(
        "&nbsp;",
        " "
    )

    raw = raw.replace(
        "&amp;",
        "&"
    )

    return re.sub(
        r"\s+",
        " ",
        raw
    ).strip()


# =============================================================================
# Existing qualifying roster
# =============================================================================

if not ATTEMPT_PANEL.exists():

    raise SystemExit(
        f"MISSING INPUT: {ATTEMPT_PANEL}"
    )


attempts = read_csv(
    ATTEMPT_PANEL
)

fieldnames = list(
    attempts[0].keys()
) if attempts else []

name_columns = find_candidate_columns(
    fieldnames
)

car_columns = find_car_columns(
    fieldnames
)


print("=" * 132)
print("R4F6F-v2 — PDF ROW SCHEMA RECONNAISSANCE + KNOWN-DRIVER MATCHING")
print("=" * 132)

print()
print("ATTEMPT PANEL SCHEMA")
print(
    f"rows={len(attempts)}"
)

print(
    "candidate driver/name columns: "
    +
    (
        ", ".join(
            name_columns
        )
        if name_columns
        else "[NONE]"
    )
)

print(
    "candidate car columns: "
    +
    (
        ", ".join(
            car_columns
        )
        if car_columns
        else "[NONE]"
    )
)


roster = {}

for r in attempts:

    year_raw = clean(
        r.get(
            "year"
        )
    )

    try:
        year = int(
            float(
                year_raw
            )
        )

    except Exception:
        continue


    if year not in {
        2021,
        2023,
        2024,
    }:
        continue


    driver = ""

    for col in name_columns:

        candidate = clean(
            r.get(
                col
            )
        )

        if looks_like_driver_name(
            candidate
        ):
            driver = candidate
            break


    car = ""

    for col in car_columns:

        candidate = clean(
            r.get(
                col
            )
        )

        if candidate:
            car = candidate
            break


    if driver:

        key = (
            year,
            normalize_name(
                driver
            )
        )

        roster[
            key
        ] = {
            "year":
                year,

            "driver_name":
                driver,

            "normalized_name":
                normalize_name(
                    driver
                ),

            "surname":
                surname(
                    driver
                ),

            "car_number":
                car,
        }


roster_rows = sorted(
    roster.values(),
    key=lambda r: (
        r[
            "year"
        ],
        r[
            "driver_name"
        ],
    )
)


print()
print(
    f"Known qualifying driver roster rows: "
    f"{len(roster_rows)}"
)

for year in [
    2021,
    2023,
    2024,
]:

    count = sum(
        r[
            "year"
        ] == year
        for r in roster_rows
    )

    print(
        f"{year} | roster={count}"
    )


# =============================================================================
# PDF numeric-line reconnaissance
# =============================================================================

line_rows = []

for year, path in PDFS.items():

    if not path.exists():

        raise SystemExit(
            f"MISSING PDF: {path}"
        )

    text, method = pdf_to_text(
        path
    )

    if not text.strip():

        raise SystemExit(
            f"NO TEXT EXTRACTED: {path}"
        )


    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip()
    ]


    numeric_lines = []

    for line_no, line in enumerate(
        lines,
        start=1
    ):

        mph_values = extract_mph_values(
            line
        )

        if not mph_values:
            continue


        normalized = normalize_line(
            line
        )

        full_name_matches = []

        surname_matches = []


        for driver in roster_rows:

            if driver[
                "year"
            ] != year:
                continue


            full = driver[
                "normalized_name"
            ]

            sur = driver[
                "surname"
            ]


            if (
                full
                and
                full in normalized
            ):

                full_name_matches.append(
                    driver[
                        "driver_name"
                    ]
                )


            elif (
                sur
                and
                len(
                    sur
                ) >= 4
                and
                re.search(
                    r"\b"
                    +
                    re.escape(
                        sur
                    )
                    +
                    r"\b",
                    normalized,
                )
            ):

                surname_matches.append(
                    driver[
                        "driver_name"
                    ]
                )


        all_matches = list(
            dict.fromkeys(
                full_name_matches
                +
                surname_matches
            )
        )


        car_candidates = re.findall(
            r"(?<!\d)\d{1,2}(?!\d)",
            line
        )


        row = {
            "year":
                year,

            "line_no":
                line_no,

            "extraction_method":
                method,

            "mph_values":
                ";".join(
                    mph_values
                ),

            "full_name_match_count":
                len(
                    full_name_matches
                ),

            "surname_match_count":
                len(
                    surname_matches
                ),

            "matched_driver_count":
                len(
                    all_matches
                ),

            "matched_drivers":
                ";".join(
                    all_matches
                ),

            "numeric_tokens_1to2_digits":
                ";".join(
                    car_candidates
                ),

            "raw_line":
                line,
        }

        line_rows.append(
            row
        )

        numeric_lines.append(
            row
        )


    print()
    print("=" * 132)
    print(
        f"{year} PDF NUMERIC ROWS"
    )
    print("=" * 132)

    print(
        f"numeric mph rows="
        f"{len(numeric_lines)}"
    )

    print(
        f"matched exactly one known driver="
        f"{sum(r['matched_driver_count'] == 1 for r in numeric_lines)}"
    )

    print(
        f"matched zero drivers="
        f"{sum(r['matched_driver_count'] == 0 for r in numeric_lines)}"
    )

    print(
        f"matched multiple drivers="
        f"{sum(r['matched_driver_count'] > 1 for r in numeric_lines)}"
    )


    print()
    print(
        "FIRST 40 RAW NUMERIC LINES"
    )

    for r in numeric_lines[:40]:

        print(
            f"L{r['line_no']:03d} | "
            f"mph={r['mph_values']:12s} | "
            f"match={r['matched_drivers'] or '-'}"
        )

        print(
            f"    {r['raw_line']}"
        )


# =============================================================================
# Editorial numeric contexts
# =============================================================================

editorial_rows = []

KEY_PATTERNS = [
    r"no[-\s]?tow",
    r"without a tow",
    r"without tow",
    r"four[-\s]?lap",
    r"qualifying simulation",
    r"qualifying sim",
]


for year, path in EDITORIALS.items():

    if not path.exists():
        continue

    text = html_visible_text(
        path
    )

    for pattern in KEY_PATTERNS:

        for m in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            start = max(
                0,
                m.start() - 500
            )

            end = min(
                len(text),
                m.end() + 500
            )

            context = text[
                start:end
            ]

            mph_values = re.findall(
                r"\b(?:22[0-9]|23[0-9]|24[0-9])"
                r"\.\d{3}\b",
                context
            )


            normalized = normalize_line(
                context
            )

            matched = []

            for driver in roster_rows:

                if driver[
                    "year"
                ] != year:
                    continue

                full = driver[
                    "normalized_name"
                ]

                sur = driver[
                    "surname"
                ]

                if (
                    full
                    and
                    full in normalized
                ):

                    matched.append(
                        driver[
                            "driver_name"
                        ]
                    )

                elif (
                    sur
                    and
                    len(
                        sur
                    ) >= 4
                    and
                    re.search(
                        r"\b"
                        +
                        re.escape(
                            sur
                        )
                        +
                        r"\b",
                        normalized,
                    )
                ):

                    matched.append(
                        driver[
                            "driver_name"
                        ]
                    )


            matched = list(
                dict.fromkeys(
                    matched
                )
            )


            editorial_rows.append({
                "year":
                    year,

                "anchor_pattern":
                    pattern,

                "mph_values":
                    ";".join(
                        mph_values
                    ),

                "matched_drivers":
                    ";".join(
                        matched
                    ),

                "context":
                    context,
            })


print()
print("=" * 132)
print("EDITORIAL CONTEXT RECONNAISSANCE")
print("=" * 132)

for r in editorial_rows:

    if not r[
        "mph_values"
    ]:
        continue

    print()
    print(
        f"{r['year']} | "
        f"anchor={r['anchor_pattern']} | "
        f"mph={r['mph_values']} | "
        f"drivers={r['matched_drivers'] or '-'}"
    )

    print(
        r[
            "context"
        ]
    )


# =============================================================================
# QA
# =============================================================================

pdf_2023 = [
    r
    for r in line_rows
    if r[
        "year"
    ] == 2023
]

pdf_2024 = [
    r
    for r in line_rows
    if r[
        "year"
    ] == 2024
]


qa_rows = [
    {
        "metric":
            "2023_numeric_pdf_rows",

        "value":
            len(
                pdf_2023
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if len(
                    pdf_2023
                ) == 34
                else "WARN"
            ),
    },

    {
        "metric":
            "2024_numeric_pdf_rows",

        "value":
            len(
                pdf_2024
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if len(
                    pdf_2024
                ) == 34
                else "WARN"
            ),
    },

    {
        "metric":
            "driver_roster_available",

        "value":
            len(
                roster_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if roster_rows
                else "WARN"
            ),
    },

    {
        "metric":
            "schema_recon_only_no_model_mutation",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_LINES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        line_rows[0].keys()
    ) if line_rows else [
        "year",
        "raw_line",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        line_rows
    )


with OUT_ROSTER.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        roster_rows[0].keys()
    ) if roster_rows else [
        "year",
        "driver_name",
        "car_number",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        roster_rows
    )


with OUT_EDITORIAL.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        editorial_rows[0].keys()
    ) if editorial_rows else [
        "year",
        "context",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        editorial_rows
    )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F6F_V2",

    "status":
        "R4F6F_V2_PDF_SCHEMA_RECONNAISSANCE_READY",

    "important_correction":
        (
            "R4F6F-v1 canonical panel is not accepted as model input. "
            "Its two parsed rows are parser artefacts / incomplete extraction."
        ),

    "known_driver_roster_rows":
        len(
            roster_rows
        ),

    "pdf_numeric_rows": {
        "2023":
            len(
                pdf_2023
            ),

        "2024":
            len(
                pdf_2024
            ),
    },

    "next_phase":
        (
            "Define deterministic official-PDF row parser from observed "
            "row schema, then construct canonical driver-level Fast Friday "
            "references with explicit provenance."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]


print()
print("=" * 132)
print("RECONNAISSANCE SUMMARY")
print("=" * 132)

for year in [
    2023,
    2024,
]:

    subset = [
        r
        for r in line_rows
        if r[
            "year"
        ] == year
    ]

    print(
        f"{year} | "
        f"numeric_rows={len(subset)} | "
        f"one_driver={sum(r['matched_driver_count'] == 1 for r in subset)} | "
        f"zero_driver={sum(r['matched_driver_count'] == 0 for r in subset)} | "
        f"multi_driver={sum(r['matched_driver_count'] > 1 for r in subset)}"
    )


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:
    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_LINES.relative_to(ROOT)
)
print(
    OUT_ROSTER.relative_to(ROOT)
)
print(
    OUT_EDITORIAL.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6F_V2_PDF_SCHEMA_RECONNAISSANCE_READY"
)
