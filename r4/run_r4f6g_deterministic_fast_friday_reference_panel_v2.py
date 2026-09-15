from pathlib import Path
import csv
import json
import re
import shutil
import subprocess
import unicodedata
from collections import Counter

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
RAW = ROOT / "r4/evidence/fast_friday"

OUT.mkdir(parents=True, exist_ok=True)

PDFS = {
    2023:
        RAW / "2023_fast_friday_practice5_results.pdf",
    2024:
        RAW / "2024_fast_friday_practice5_results.pdf",
}

OUT_ALL = (
    OUT /
    "r4f6g_fast_friday_all_reference_evidence_v2.csv"
)

OUT_CANONICAL = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f6g_fast_friday_reference_summary_v2.csv"
)

OUT_QA = (
    OUT /
    "r4f6g_fast_friday_reference_qa_v2.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6g_fast_friday_reference_report_v2.json"
)


REFERENCE_PRIORITY = {
    "FOUR_LAP_QUALIFYING_SIM": 3,
    "NO_TOW_SINGLE_LAP": 2,
    "GENERAL_FAST_FRIDAY_BEST_SPEED": 1,
}

QUALITY_SCORE = {
    "VERY_HIGH": 3,
    "HIGH": 2,
    "MEDIUM": 1,
}


EDITORIAL_REFERENCES = [
    {
        "year": 2021,
        "driver_name": "Alexander Rossi",
        "car_number": "27",
        "reference_speed_mph": 231.598,
        "reference_type": "NO_TOW_SINGLE_LAP",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2021_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fastest driver running alone; "
            "best no-tow lap 231.598 mph.",
    },
    {
        "year": 2021,
        "driver_name": "Graham Rahal",
        "car_number": "15",
        "reference_speed_mph": 231.518,
        "reference_type": "NO_TOW_SINGLE_LAP",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2021_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: second on no-tow list.",
    },
    {
        "year": 2021,
        "driver_name": "Pato O'Ward",
        "car_number": "5",
        "reference_speed_mph": 231.510,
        "reference_type": "NO_TOW_SINGLE_LAP",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2021_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: third on no-tow list.",
    },

    {
        "year": 2023,
        "driver_name": "Takuma Sato",
        "car_number": "11",
        "reference_speed_mph": 233.412,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fastest four-lap qualifying sim average.",
    },
    {
        "year": 2023,
        "driver_name": "Marcus Ericsson",
        "car_number": "8",
        "reference_speed_mph": 233.112,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: four-lap qualifying sim average.",
    },
    {
        "year": 2023,
        "driver_name": "Josef Newgarden",
        "car_number": "2",
        "reference_speed_mph": 233.085,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: four-lap qualifying sim average.",
    },
    {
        "year": 2023,
        "driver_name": "Will Power",
        "car_number": "12",
        "reference_speed_mph": 233.070,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "CORE_DEVELOPMENT",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: four-lap qualifying sim average.",
    },

    {
        "year": 2024,
        "driver_name": "Josef Newgarden",
        "car_number": "2",
        "reference_speed_mph": 234.063,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "VALIDATION_ONLY",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: best four-lap qualifying sim average.",
    },
    {
        "year": 2024,
        "driver_name": "Scott McLaughlin",
        "car_number": "3",
        "reference_speed_mph": 233.623,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "VALIDATION_ONLY",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: second-fastest qualifying sim.",
    },
    {
        "year": 2024,
        "driver_name": "Will Power",
        "car_number": "12",
        "reference_speed_mph": 233.451,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "VALIDATION_ONLY",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: third-fastest qualifying sim.",
    },
    {
        "year": 2024,
        "driver_name": "Alexander Rossi",
        "car_number": "7",
        "reference_speed_mph": 233.355,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "VALIDATION_ONLY",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fourth on qualifying sim chart.",
    },
    {
        "year": 2024,
        "driver_name": "Pato O'Ward",
        "car_number": "5",
        "reference_speed_mph": 233.043,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "VALIDATION_ONLY",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fifth on qualifying sim chart.",
    },
    {
        "year": 2024,
        "driver_name": "Kyle Larson",
        "car_number": "17",
        "reference_speed_mph": 232.549,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "model_role": "VALIDATION_ONLY",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: 10th on qualifying sim chart.",
    },
]


def normalize_driver_name(name):
    value = unicodedata.normalize(
        "NFKD",
        str(name)
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def pdf_driver_to_display(name):
    name = re.sub(
        r"\s+\(R\)\s*$",
        "",
        name.strip(),
    )

    if "," not in name:
        return name

    surname, given = name.split(
        ",",
        1,
    )

    return (
        given.strip()
        +
        " "
        +
        surname.strip()
    )


def pdf_to_text(path):
    if shutil.which("pdftotext"):

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
            text = page.extract_text() or ""

            if text.strip():
                parts.append(text)

        result = "\n".join(parts)

        if result.strip():
            return (
                result,
                "PYPDF",
            )

    except Exception:
        pass

    return (
        "",
        "NONE",
    )


ROW_PATTERN = re.compile(
    r"^\s*"
    r"(?P<position>\d{1,2})"
    r"\s+"
    r"(?P<car>\d{1,2})"
    r"\s+"
    r"(?P<driver>.+?)"
    r"\s+"
    r"D/[HC]/F"
    r"\s+"
    r"(?P<lap_time>\d{2}:\d{2}\.\d{4})"
    r"\s+"
    r"(?P<speed>\d{3}\.\d{3})"
    r"(?:\s+|$)"
)


pdf_rows = []
unparsed = []

for year, path in PDFS.items():

    if not path.exists():
        raise SystemExit(
            f"MISSING PDF: {path}"
        )

    text, extraction_method = pdf_to_text(
        path
    )

    if not text.strip():
        raise SystemExit(
            f"NO TEXT EXTRACTED: {path}"
        )

    for line_no, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if not re.search(
            r"\b\d{3}\.\d{3}\b",
            line,
        ):
            continue

        m = ROW_PATTERN.match(
            line
        )

        if not m:
            unparsed.append({
                "year": year,
                "line_no": line_no,
                "raw_line": line,
            })
            continue

        # IMPORTANT:
        # preserve car token EXACTLY.
        # "06" must remain distinct from "6".
        car_number = m.group(
            "car"
        )

        driver_name = pdf_driver_to_display(
            m.group(
                "driver"
            )
        )

        pdf_rows.append({
            "year":
                year,

            "driver_name":
                driver_name,

            "driver_key":
                normalize_driver_name(
                    driver_name
                ),

            "car_number":
                car_number,

            "reference_speed_mph":
                float(
                    m.group(
                        "speed"
                    )
                ),

            "reference_type":
                "GENERAL_FAST_FRIDAY_BEST_SPEED",

            "reference_priority":
                1,

            "source_quality":
                "HIGH",

            "source_type":
                "OFFICIAL_RESULTS_PDF",

            "source_file":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "extraction_method":
                extraction_method,

            "model_role":
                (
                    "VALIDATION_ONLY"
                    if year == 2024
                    else
                    "CORE_DEVELOPMENT"
                ),

            "provenance_note":
                (
                    "Deterministically parsed from official "
                    "Fast Friday session result row."
                ),

            "pdf_position":
                int(
                    m.group(
                        "position"
                    )
                ),

            "pdf_lap_time":
                m.group(
                    "lap_time"
                ),
        })


editorial_rows = []

for source in EDITORIAL_REFERENCES:

    row = dict(source)

    row[
        "driver_key"
    ] = normalize_driver_name(
        row[
            "driver_name"
        ]
    )

    # Preserve explicitly reported car number as written.
    row[
        "car_number"
    ] = str(
        row[
            "car_number"
        ]
    )

    row[
        "reference_priority"
    ] = REFERENCE_PRIORITY[
        row[
            "reference_type"
        ]
    ]

    row[
        "source_type"
    ] = "OFFICIAL_EDITORIAL_HTML"

    row[
        "extraction_method"
    ] = "EXPLICIT_VERIFIED_STATEMENT"

    row[
        "pdf_position"
    ] = ""

    row[
        "pdf_lap_time"
    ] = ""

    editorial_rows.append(row)


all_rows = (
    pdf_rows
    +
    editorial_rows
)


# =============================================================================
# Canonical identity = year + normalized driver name.
#
# Car number is retained as an attribute, never integer-normalized.
# =============================================================================

canonical_map = {}

for row in all_rows:

    key = (
        row[
            "year"
        ],
        row[
            "driver_key"
        ],
    )

    score = (
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

    current = canonical_map.get(
        key
    )

    if current is None:

        canonical_map[
            key
        ] = row
        continue

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

    if score > current_score:

        canonical_map[
            key
        ] = row


canonical = sorted(
    canonical_map.values(),
    key=lambda r: (
        r[
            "year"
        ],
        r[
            "driver_key"
        ],
    )
)


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

        "canonical_entries":
            len(
                subset
            ),

        "four_lap":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "FOUR_LAP_QUALIFYING_SIM"
                for r in subset
            ),

        "no_tow":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "NO_TOW_SINGLE_LAP"
                for r in subset
            ),

        "general":
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


def get_entry(year, driver):
    key = (
        year,
        normalize_driver_name(
            driver
        ),
    )

    return canonical_map.get(
        key
    )


r23 = get_entry(
    2023,
    "Felix Rosenqvist"
)

c23 = get_entry(
    2023,
    "Helio Castroneves"
)

i24 = get_entry(
    2024,
    "Callum Ilott"
)

c24 = get_entry(
    2024,
    "Helio Castroneves"
)


qa_rows = [
    {
        "metric":
            "2023_pdf_rows",

        "value":
            sum(
                r[
                    "year"
                ] == 2023
                for r in pdf_rows
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2023
                    for r in pdf_rows
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_pdf_rows",

        "value":
            sum(
                r[
                    "year"
                ] == 2024
                for r in pdf_rows
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2024
                    for r in pdf_rows
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "unparsed_pdf_numeric_rows",

        "value":
            len(
                unparsed
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not unparsed
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_canonical_entries",

        "value":
            sum(
                r[
                    "year"
                ] == 2023
                for r in canonical
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2023
                    for r in canonical
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_canonical_entries",

        "value":
            sum(
                r[
                    "year"
                ] == 2024
                for r in canonical
            ),

        "expected":
            34,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2024
                    for r in canonical
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_6_and_06_distinct",

        "value":
            (
                r23 is not None
                and
                c23 is not None
                and
                r23[
                    "car_number"
                ] == "6"
                and
                c23[
                    "car_number"
                ] == "06"
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if (
                    r23 is not None
                    and
                    c23 is not None
                    and
                    r23[
                        "car_number"
                    ] == "6"
                    and
                    c23[
                        "car_number"
                    ] == "06"
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_6_and_06_distinct",

        "value":
            (
                i24 is not None
                and
                c24 is not None
                and
                i24[
                    "car_number"
                ] == "6"
                and
                c24[
                    "car_number"
                ] == "06"
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if (
                    i24 is not None
                    and
                    c24 is not None
                    and
                    i24[
                        "car_number"
                    ] == "6"
                    and
                    c24[
                        "car_number"
                    ] == "06"
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_no_tow_entries",

        "value":
            sum(
                r[
                    "year"
                ] == 2021
                and
                r[
                    "reference_type"
                ]
                ==
                "NO_TOW_SINGLE_LAP"
                for r in canonical
            ),

        "expected":
            3,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2021
                    and
                    r[
                        "reference_type"
                    ]
                    ==
                    "NO_TOW_SINGLE_LAP"
                    for r in canonical
                ) == 3
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_four_lap_entries",

        "value":
            sum(
                r[
                    "year"
                ] == 2023
                and
                r[
                    "reference_type"
                ]
                ==
                "FOUR_LAP_QUALIFYING_SIM"
                for r in canonical
            ),

        "expected":
            4,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2023
                    and
                    r[
                        "reference_type"
                    ]
                    ==
                    "FOUR_LAP_QUALIFYING_SIM"
                    for r in canonical
                ) == 4
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_four_lap_entries",

        "value":
            sum(
                r[
                    "year"
                ] == 2024
                and
                r[
                    "reference_type"
                ]
                ==
                "FOUR_LAP_QUALIFYING_SIM"
                for r in canonical
            ),

        "expected":
            6,

        "status":
            (
                "PASS"
                if sum(
                    r[
                        "year"
                    ] == 2024
                    and
                    r[
                        "reference_type"
                    ]
                    ==
                    "FOUR_LAP_QUALIFYING_SIM"
                    for r in canonical
                ) == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_only",

        "value":
            all(
                r[
                    "model_role"
                ] == "VALIDATION_ONLY"
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
                    ] == "VALIDATION_ONLY"
                    for r in canonical
                    if r[
                        "year"
                    ] == 2024
                )
                else "FAIL"
            ),
    },
]


FIELDS = [
    "year",
    "driver_name",
    "driver_key",
    "car_number",
    "reference_speed_mph",
    "reference_type",
    "reference_priority",
    "source_quality",
    "source_type",
    "source_file",
    "extraction_method",
    "model_role",
    "provenance_note",
    "pdf_position",
    "pdf_lap_time",
]


with OUT_ALL.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=FIELDS
    )

    writer.writeheader()
    writer.writerows(
        all_rows
    )


with OUT_CANONICAL.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=FIELDS
    )

    writer.writeheader()
    writer.writerows(
        canonical
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
        "R4F6G_V2",

    "status":
        "R4F6G_V2_ENTRY_IDENTITY_CORRECTED",

    "critical_correction":
        (
            "Car numbers are no longer integer-normalized. "
            "Entries #6 and #06 remain distinct. "
            "Canonical identity is year + normalized driver name."
        ),

    "supersedes":
        (
            "r4f6g_canonical_fast_friday_reference_panel_v1.csv"
        ),

    "reference_hierarchy": [
        "FOUR_LAP_QUALIFYING_SIM",
        "NO_TOW_SINGLE_LAP",
        "GENERAL_FAST_FRIDAY_BEST_SPEED",
    ],

    "summary":
        summary_rows,

    "next_phase":
        (
            "Join corrected canonical Fast Friday references "
            "to qualifying attempts and test pre-session "
            "normalization against repeat anchors."
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


print("=" * 128)
print("R4F6G-v2 — ENTRY IDENTITY CORRECTION")
print("=" * 128)

print()
print("YEAR REFERENCE SUMMARY")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"canonical={r['canonical_entries']:2d} | "
        f"4lap={r['four_lap']:2d} | "
        f"no_tow={r['no_tow']:2d} | "
        f"general={r['general']:2d} | "
        f"{r['model_role']}"
    )


print()
print("LEADING-ZERO IDENTITY CHECK")

print(
    "2023 Felix Rosenqvist =",
    (
        r23[
            "car_number"
        ]
        if r23
        else "MISSING"
    )
)

print(
    "2023 Helio Castroneves =",
    (
        c23[
            "car_number"
        ]
        if c23
        else "MISSING"
    )
)

print(
    "2024 Callum Ilott =",
    (
        i24[
            "car_number"
        ]
        if i24
        else "MISSING"
    )
)

print(
    "2024 Helio Castroneves =",
    (
        c24[
            "car_number"
        ]
        if c24
        else "MISSING"
    )
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
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_ALL.relative_to(ROOT)
)
print(
    OUT_CANONICAL.relative_to(ROOT)
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
    "R4F6G_V2_ENTRY_IDENTITY_CORRECTED"
)
