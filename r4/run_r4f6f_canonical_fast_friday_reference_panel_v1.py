from pathlib import Path
from html.parser import HTMLParser
import csv
import json
import re
import shutil
import subprocess

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
RAW = ROOT / "r4/evidence/fast_friday"

OUT.mkdir(parents=True, exist_ok=True)

OUT_PANEL = (
    OUT /
    "r4f6f_canonical_fast_friday_reference_panel_v1.csv"
)

OUT_DIAG = (
    OUT /
    "r4f6f_fast_friday_extraction_diagnostics_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f6f_fast_friday_reference_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6f_fast_friday_reference_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6f_fast_friday_reference_report_v1.json"
)


SOURCES = [
    {
        "year": 2021,
        "path":
            RAW /
            "2021_fast_friday_official_editorial.html",
        "source_type":
            "OFFICIAL_EDITORIAL_HTML",
        "reference_type":
            "NO_TOW_SINGLE_LAP",
        "source_quality":
            "HIGH",
        "model_role":
            "CORE_DEVELOPMENT",
    },

    {
        "year": 2023,
        "path":
            RAW /
            "2023_fast_friday_practice5_results.pdf",
        "source_type":
            "OFFICIAL_RESULTS_PDF",
        "reference_type":
            "GENERAL_FAST_FRIDAY_BEST_SPEED",
        "source_quality":
            "HIGH",
        "model_role":
            "CORE_DEVELOPMENT",
    },

    {
        "year": 2023,
        "path":
            RAW /
            "2023_fast_friday_official_editorial.html",
        "source_type":
            "OFFICIAL_EDITORIAL_HTML",
        "reference_type":
            "FOUR_LAP_QUALIFYING_SIM",
        "source_quality":
            "VERY_HIGH",
        "model_role":
            "CORE_DEVELOPMENT",
    },

    {
        "year": 2024,
        "path":
            RAW /
            "2024_fast_friday_practice5_results.pdf",
        "source_type":
            "OFFICIAL_RESULTS_PDF",
        "reference_type":
            "GENERAL_FAST_FRIDAY_BEST_SPEED",
        "source_quality":
            "HIGH",
        "model_role":
            "VALIDATION_ONLY",
    },

    {
        "year": 2024,
        "path":
            RAW /
            "2024_fast_friday_official_editorial.html",
        "source_type":
            "OFFICIAL_EDITORIAL_HTML",
        "reference_type":
            "FOUR_LAP_QUALIFYING_SIM",
        "source_quality":
            "VERY_HIGH",
        "model_role":
            "VALIDATION_ONLY",
    },
]


REFERENCE_PRIORITY = {
    "FOUR_LAP_QUALIFYING_SIM": 3,
    "NO_TOW_SINGLE_LAP": 2,
    "GENERAL_FAST_FRIDAY_BEST_SPEED": 1,
}


class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False
        self.skip_tag = None

    def handle_starttag(
        self,
        tag,
        attrs
    ):
        if tag in {
            "script",
            "style",
            "noscript",
        }:
            self.skip = True
            self.skip_tag = tag

    def handle_endtag(
        self,
        tag
    ):
        if (
            self.skip
            and
            tag == self.skip_tag
        ):
            self.skip = False
            self.skip_tag = None

    def handle_data(
        self,
        data
    ):
        if not self.skip:
            text = data.strip()

            if text:
                self.parts.append(
                    text
                )

    def text(self):
        return "\n".join(
            self.parts
        )


def html_to_text(path):
    raw = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    parser = VisibleTextParser()
    parser.feed(
        raw
    )

    return parser.text()


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

        return (
            "\n".join(
                parts
            ),
            "PYPDF",
        )

    except Exception:
        return (
            "",
            "NONE",
        )


def normalize_spaces(text):
    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def extract_speed_values(text):
    matches = re.findall(
        r"\b(?:22[0-9]|23[0-9]|24[0-9])\.\d{3}\b",
        text,
    )

    return [
        float(
            x
        )
        for x in matches
    ]


def likely_driver_name(text):
    # Broad but conservative:
    # two or more capitalized name tokens.
    matches = re.findall(
        r"\b[A-Z][a-zA-Z'’-]+"
        r"(?:\s+[A-Z][a-zA-Z'’-]+)+\b",
        text,
    )

    banned = {
        "Fast Friday",
        "Indianapolis Motor Speedway",
        "NTT INDYCAR SERIES",
        "Indianapolis 500",
        "Practice Results",
        "Fast Six",
    }

    for name in matches:

        if name not in banned:
            return name

    return ""


def extract_car_number(text):
    patterns = [
        r"#\s*(\d{1,2})\b",
        r"\bNo\.\s*(\d{1,2})\b",
        r"\bCar\s+(\d{1,2})\b",
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if m:
            return m.group(
                1
            )

    return ""


def context_windows(
    text,
    keyword_patterns,
    radius=260,
):
    contexts = []

    for pattern in keyword_patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            start = max(
                0,
                match.start() - radius
            )

            end = min(
                len(text),
                match.end() + radius
            )

            contexts.append(
                normalize_spaces(
                    text[start:end]
                )
            )

    return contexts


panel_candidates = []
diag_rows = []


for source in SOURCES:

    path = source[
        "path"
    ]

    if not path.exists():

        diag_rows.append({
            "year":
                source[
                    "year"
                ],

            "source_file":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "status":
                "MISSING_SOURCE",

            "detail":
                "",
        })

        continue


    if path.suffix.lower() == ".pdf":

        text, extraction_method = (
            pdf_to_text(
                path
            )
        )

    else:

        text = html_to_text(
            path
        )

        extraction_method = (
            "HTML_VISIBLE_TEXT"
        )


    if not text.strip():

        diag_rows.append({
            "year":
                source[
                    "year"
                ],

            "source_file":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "status":
                "NO_EXTRACTABLE_TEXT",

            "detail":
                extraction_method,
        })

        continue


    # =========================================================================
    # Editorial extraction
    # =========================================================================

    if source[
        "source_type"
    ] == "OFFICIAL_EDITORIAL_HTML":

        if source[
            "reference_type"
        ] == "NO_TOW_SINGLE_LAP":

            contexts = context_windows(
                text,
                [
                    r"no[-\s]?tow",
                    r"without a tow",
                    r"without tow",
                ],
                radius=420,
            )

        else:

            contexts = context_windows(
                text,
                [
                    r"four[-\s]?lap",
                    r"qualifying simulation",
                    r"qualifying sim",
                ],
                radius=420,
            )


        for context in contexts:

            speeds = extract_speed_values(
                context
            )

            if not speeds:
                continue


            # Attempt to identify all nearby capitalized names.
            names = re.findall(
                r"\b[A-Z][a-zA-Z'’-]+"
                r"(?:\s+[A-Z][a-zA-Z'’-]+)+\b",
                context,
            )

            banned = {
                "Fast Friday",
                "Indianapolis Motor Speedway",
                "NTT INDYCAR SERIES",
                "Indianapolis 500",
                "Fast Six",
                "Practice Results",
            }

            names = [
                name
                for name in names
                if name not in banned
            ]


            # Conservative rule:
            # only auto-create rows when there is exactly one plausible
            # driver name and at least one speed in the same context.
            if len(
                names
            ) == 1:

                driver = names[
                    0
                ]

                # For editorial context, choose the first speed nearest
                # the statement. We preserve the full context for audit.
                speed = speeds[
                    0
                ]

                panel_candidates.append({
                    "year":
                        source[
                            "year"
                        ],

                    "driver_name":
                        driver,

                    "car_number":
                        extract_car_number(
                            context
                        ),

                    "reference_speed_mph":
                        speed,

                    "reference_type":
                        source[
                            "reference_type"
                        ],

                    "reference_priority":
                        REFERENCE_PRIORITY[
                            source[
                                "reference_type"
                            ]
                        ],

                    "source_quality":
                        source[
                            "source_quality"
                        ],

                    "source_type":
                        source[
                            "source_type"
                        ],

                    "source_file":
                        str(
                            path.relative_to(
                                ROOT
                            )
                        ),

                    "extraction_method":
                        extraction_method,

                    "model_role":
                        source[
                            "model_role"
                        ],

                    "context":
                        context,
                })

            else:

                diag_rows.append({
                    "year":
                        source[
                            "year"
                        ],

                    "source_file":
                        str(
                            path.relative_to(
                                ROOT
                            )
                        ),

                    "status":
                        "AMBIGUOUS_EDITORIAL_CONTEXT",

                    "detail":
                        context,
                })


    # =========================================================================
    # Official PDF session result extraction
    # =========================================================================

    else:

        lines = [
            line.rstrip()
            for line in text.splitlines()
            if line.strip()
        ]


        for line in lines:

            speeds = extract_speed_values(
                line
            )

            if not speeds:
                continue


            # Most official timing-result rows contain position/car/name/speed.
            driver = likely_driver_name(
                line
            )

            car = extract_car_number(
                line
            )


            if not driver:

                diag_rows.append({
                    "year":
                        source[
                            "year"
                        ],

                    "source_file":
                        str(
                            path.relative_to(
                                ROOT
                            )
                        ),

                    "status":
                        "NUMERIC_PDF_ROW_NO_DRIVER_PARSED",

                    "detail":
                        normalize_spaces(
                            line
                        ),
                })

                continue


            speed = speeds[
                -1
            ]


            panel_candidates.append({
                "year":
                    source[
                        "year"
                    ],

                "driver_name":
                    driver,

                "car_number":
                    car,

                "reference_speed_mph":
                    speed,

                "reference_type":
                    source[
                        "reference_type"
                    ],

                "reference_priority":
                    REFERENCE_PRIORITY[
                        source[
                            "reference_type"
                        ]
                    ],

                "source_quality":
                    source[
                        "source_quality"
                    ],

                "source_type":
                    source[
                        "source_type"
                    ],

                "source_file":
                    str(
                        path.relative_to(
                            ROOT
                        )
                    ),

                "extraction_method":
                    extraction_method,

                "model_role":
                    source[
                        "model_role"
                    ],

                "context":
                    normalize_spaces(
                        line
                    ),
            })


# =============================================================================
# Deduplicate exact repeats
# =============================================================================

dedup = {}

for row in panel_candidates:

    key = (
        row[
            "year"
        ],
        row[
            "driver_name"
        ],
        row[
            "reference_type"
        ],
        row[
            "reference_speed_mph"
        ],
        row[
            "source_file"
        ],
    )

    dedup[
        key
    ] = row


panel_candidates = list(
    dedup.values()
)


# =============================================================================
# Canonical best reference per year + driver
#
# Highest reference priority wins.
# Within same priority, higher source quality is preserved by source ordering.
# No attempt is made to average qualitatively different reference types.
# =============================================================================

QUALITY_SCORE = {
    "VERY_HIGH": 3,
    "HIGH": 2,
    "MEDIUM": 1,
}


best_by_driver = {}

for row in panel_candidates:

    key = (
        row[
            "year"
        ],
        row[
            "driver_name"
        ],
    )

    current = best_by_driver.get(
        key
    )

    row_score = (
        row[
            "reference_priority"
        ],
        QUALITY_SCORE.get(
            row[
                "source_quality"
            ],
            0,
        ),
    )


    if current is None:

        best_by_driver[
            key
        ] = row

    else:

        current_score = (
            current[
                "reference_priority"
            ],
            QUALITY_SCORE.get(
                current[
                    "source_quality"
                ],
                0,
            ),
        )

        if row_score > current_score:

            best_by_driver[
                key
            ] = row


canonical = sorted(
    best_by_driver.values(),
    key=lambda r: (
        r[
            "year"
        ],
        r[
            "driver_name"
        ],
    )
)


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in [
    2021,
    2023,
    2024,
]:

    subset = [
        r
        for r in canonical
        if r[
            "year"
        ] == year
    ]

    summary_rows.append({
        "year":
            year,

        "canonical_driver_references":
            len(
                subset
            ),

        "four_lap_refs":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "FOUR_LAP_QUALIFYING_SIM"
                for r in subset
            ),

        "no_tow_refs":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "NO_TOW_SINGLE_LAP"
                for r in subset
            ),

        "general_fast_friday_refs":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "GENERAL_FAST_FRIDAY_BEST_SPEED"
                for r in subset
            ),

        "model_role":
            (
                "VALIDATION_ONLY"
                if year == 2024
                else
                "CORE_DEVELOPMENT"
            ),
    })


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "candidate_rows_extracted",

        "value":
            len(
                panel_candidates
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if panel_candidates
                else "FAIL"
            ),
    },

    {
        "metric":
            "canonical_rows_created",

        "value":
            len(
                canonical
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if canonical
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_role_preserved",

        "value":
            all(
                r[
                    "model_role"
                ]
                ==
                "VALIDATION_ONLY"
                for r in canonical
                if r[
                    "year"
                ] == 2024
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if all(
                    r[
                        "model_role"
                    ]
                    ==
                    "VALIDATION_ONLY"
                    for r in canonical
                    if r[
                        "year"
                    ] == 2024
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "reference_priority_valid",

        "value":
            all(
                r[
                    "reference_type"
                ]
                in REFERENCE_PRIORITY
                for r in canonical
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if all(
                    r[
                        "reference_type"
                    ]
                    in REFERENCE_PRIORITY
                    for r in canonical
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

panel_fields = [
    "year",
    "driver_name",
    "car_number",
    "reference_speed_mph",
    "reference_type",
    "reference_priority",
    "source_quality",
    "source_type",
    "source_file",
    "extraction_method",
    "model_role",
    "context",
]


with OUT_PANEL.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=panel_fields
    )

    writer.writeheader()
    writer.writerows(
        canonical
    )


with OUT_DIAG.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "year",
            "source_file",
            "status",
            "detail",
        ]
    )

    writer.writeheader()
    writer.writerows(
        diag_rows
    )


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
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
        "R4F6F",

    "status":
        "R4F6F_CANONICAL_FAST_FRIDAY_REFERENCE_PANEL_READY",

    "candidate_rows":
        len(
            panel_candidates
        ),

    "canonical_rows":
        len(
            canonical
        ),

    "reference_hierarchy": [
        "FOUR_LAP_QUALIFYING_SIM",
        "NO_TOW_SINGLE_LAP",
        "GENERAL_FAST_FRIDAY_BEST_SPEED",
    ],

    "summary":
        summary_rows,

    "important_constraint":
        (
            "Automatic parsing is intentionally conservative. "
            "Ambiguous editorial/PDF contexts are retained in "
            "diagnostics and are not silently promoted."
        ),

    "next_phase":
        (
            "Audit canonical driver coverage against Day1 qualifying "
            "entries, repair missing driver/car joins, then construct "
            "hierarchical pre-session entry references."
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


# =============================================================================
# Console
# =============================================================================

print("=" * 126)
print("R4F6F — CANONICAL FAST FRIDAY REFERENCE PANEL")
print("=" * 126)

print()
print(
    f"Candidate extracted rows: "
    f"{len(panel_candidates)}"
)

print(
    f"Canonical driver references: "
    f"{len(canonical)}"
)


print()
print("=" * 126)
print("YEAR REFERENCE COVERAGE")
print("=" * 126)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"drivers={r['canonical_driver_references']:2d} | "
        f"4lap={r['four_lap_refs']:2d} | "
        f"no_tow={r['no_tow_refs']:2d} | "
        f"general={r['general_fast_friday_refs']:2d} | "
        f"{r['model_role']}"
    )


print()
print("=" * 126)
print("CANONICAL REFERENCES")
print("=" * 126)

for r in canonical:

    print(
        f"{r['year']} | "
        f"{r['driver_name'][:24]:24s} | "
        f"car={r['car_number'] or '-':>3s} | "
        f"{r['reference_speed_mph']:.3f} | "
        f"{r['reference_type']} | "
        f"{r['source_quality']}"
    )


print()
print("=" * 126)
print("DIAGNOSTIC SUMMARY")
print("=" * 126)

from collections import Counter

diag_counts = Counter(
    r[
        "status"
    ]
    for r in diag_rows
)

for key in sorted(
    diag_counts
):

    print(
        f"{key:36s} | "
        f"{diag_counts[key]}"
    )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)}/"
    f"{len(qa_rows)} PASS"
)

if fails:
    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_PANEL.relative_to(ROOT)
)
print(
    OUT_DIAG.relative_to(ROOT)
)
print(
    OUT_SUMMARY.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6F_CANONICAL_FAST_FRIDAY_REFERENCE_PANEL_READY"
)
