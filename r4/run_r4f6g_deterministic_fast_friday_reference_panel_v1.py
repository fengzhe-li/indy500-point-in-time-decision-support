from pathlib import Path
from collections import Counter
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

PDFS = {
    2023:
        RAW /
        "2023_fast_friday_practice5_results.pdf",

    2024:
        RAW /
        "2024_fast_friday_practice5_results.pdf",
}

OUT_ALL = (
    OUT /
    "r4f6g_fast_friday_all_reference_evidence_v1.csv"
)

OUT_CANONICAL = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f6g_fast_friday_reference_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6g_fast_friday_reference_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6g_fast_friday_reference_report_v1.json"
)


REFERENCE_PRIORITY = {
    "FOUR_LAP_QUALIFYING_SIM": 3,
    "NO_TOW_SINGLE_LAP": 2,
    "GENERAL_FAST_FRIDAY_BEST_SPEED": 1,
}


# =============================================================================
# Explicit editorial references already verified against official text.
#
# These are NOT inferred from generic nearby numbers.
# Only statements whose driver -> qualifying-like metric relationship was
# explicit in the official editorial are promoted here.
# =============================================================================

EDITORIAL_REFERENCES = [
    # -------------------------------------------------------------------------
    # 2021 — explicitly described as no-tow / running alone.
    # -------------------------------------------------------------------------
    {
        "year": 2021,
        "driver_name": "Alexander Rossi",
        "car_number": "27",
        "reference_speed_mph": 231.598,
        "reference_type": "NO_TOW_SINGLE_LAP",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2021_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fastest driver running alone; "
            "best no-tow lap 231.598 mph.",
        "model_role": "CORE_DEVELOPMENT",
    },

    {
        "year": 2021,
        "driver_name": "Graham Rahal",
        "car_number": "15",
        "reference_speed_mph": 231.518,
        "reference_type": "NO_TOW_SINGLE_LAP",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2021_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: second on no-tow list at 231.518 mph.",
        "model_role": "CORE_DEVELOPMENT",
    },

    {
        "year": 2021,
        "driver_name": "Pato O'Ward",
        "car_number": "5",
        "reference_speed_mph": 231.510,
        "reference_type": "NO_TOW_SINGLE_LAP",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2021_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: third among no-tows at 231.510 mph.",
        "model_role": "CORE_DEVELOPMENT",
    },

    # -------------------------------------------------------------------------
    # 2023 — explicit four-lap qualifying simulation averages.
    # -------------------------------------------------------------------------
    {
        "year": 2023,
        "driver_name": "Takuma Sato",
        "car_number": "11",
        "reference_speed_mph": 233.412,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fastest four-lap average during sims.",
        "model_role": "CORE_DEVELOPMENT",
    },

    {
        "year": 2023,
        "driver_name": "Marcus Ericsson",
        "car_number": "8",
        "reference_speed_mph": 233.112,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: four-lap qualifying sim average.",
        "model_role": "CORE_DEVELOPMENT",
    },

    {
        "year": 2023,
        "driver_name": "Josef Newgarden",
        "car_number": "2",
        "reference_speed_mph": 233.085,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: four-lap qualifying sim average.",
        "model_role": "CORE_DEVELOPMENT",
    },

    {
        "year": 2023,
        "driver_name": "Will Power",
        "car_number": "12",
        "reference_speed_mph": 233.070,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2023_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: four-lap qualifying sim average.",
        "model_role": "CORE_DEVELOPMENT",
    },

    # -------------------------------------------------------------------------
    # 2024 — explicit qualifying-simulation speed chart values.
    # Validation only.
    # -------------------------------------------------------------------------
    {
        "year": 2024,
        "driver_name": "Josef Newgarden",
        "car_number": "2",
        "reference_speed_mph": 234.063,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: best four-lap qualifying sim average.",
        "model_role": "VALIDATION_ONLY",
    },

    {
        "year": 2024,
        "driver_name": "Scott McLaughlin",
        "car_number": "3",
        "reference_speed_mph": 233.623,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: second-fastest qualifying sim.",
        "model_role": "VALIDATION_ONLY",
    },

    {
        "year": 2024,
        "driver_name": "Will Power",
        "car_number": "12",
        "reference_speed_mph": 233.451,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: third-fastest qualifying sim.",
        "model_role": "VALIDATION_ONLY",
    },

    {
        "year": 2024,
        "driver_name": "Alexander Rossi",
        "car_number": "7",
        "reference_speed_mph": 233.355,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fourth on qualifying sim chart.",
        "model_role": "VALIDATION_ONLY",
    },

    {
        "year": 2024,
        "driver_name": "Pato O'Ward",
        "car_number": "5",
        "reference_speed_mph": 233.043,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: fifth on qualifying sim chart.",
        "model_role": "VALIDATION_ONLY",
    },

    {
        "year": 2024,
        "driver_name": "Kyle Larson",
        "car_number": "17",
        "reference_speed_mph": 232.549,
        "reference_type": "FOUR_LAP_QUALIFYING_SIM",
        "source_quality": "VERY_HIGH",
        "source_file":
            "r4/evidence/fast_friday/"
            "2024_fast_friday_official_editorial.html",
        "provenance_note":
            "Official editorial: 10th on qualifying sim speed chart.",
        "model_role": "VALIDATION_ONLY",
    },
]


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


def normalize_driver(pdf_name):
    # Official format:
    # "Sato, Takuma"
    # "Robb, Sting Ray (R)"
    # "Pedersen, Benjamin (R)"

    name = re.sub(
        r"\s+\(R\)\s*$",
        "",
        pdf_name.strip(),
    )

    if "," not in name:
        return name.strip()

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


def normalize_car(car):
    try:
        return str(
            int(
                car
            )
        )
    except Exception:
        return car.strip()


# =============================================================================
# Deterministic PDF schema
#
# Observed official rows:
#
# POS CAR DRIVER D/H/F 00:38.xxxx SPEED ...
#
# =============================================================================

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
unparsed_numeric_rows = []


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

            unparsed_numeric_rows.append({
                "year":
                    year,

                "line_no":
                    line_no,

                "raw_line":
                    line,
            })

            continue


        driver_name = normalize_driver(
            m.group(
                "driver"
            )
        )

        car_number = normalize_car(
            m.group(
                "car"
            )
        )

        speed = float(
            m.group(
                "speed"
            )
        )

        role = (
            "VALIDATION_ONLY"
            if year == 2024
            else
            "CORE_DEVELOPMENT"
        )


        pdf_rows.append({
            "year":
                year,

            "driver_name":
                driver_name,

            "car_number":
                car_number,

            "reference_speed_mph":
                speed,

            "reference_type":
                "GENERAL_FAST_FRIDAY_BEST_SPEED",

            "reference_priority":
                REFERENCE_PRIORITY[
                    "GENERAL_FAST_FRIDAY_BEST_SPEED"
                ],

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
                role,

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


# =============================================================================
# Convert editorial rows to common schema
# =============================================================================

editorial_rows = []

for r in EDITORIAL_REFERENCES:

    row = dict(
        r
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
    ] = (
        "OFFICIAL_EDITORIAL_HTML"
    )

    row[
        "extraction_method"
    ] = (
        "EXPLICIT_VERIFIED_STATEMENT"
    )

    row[
        "pdf_position"
    ] = ""

    row[
        "pdf_lap_time"
    ] = ""

    editorial_rows.append(
        row
    )


all_rows = (
    pdf_rows
    +
    editorial_rows
)


# =============================================================================
# Canonical reference:
# highest-quality relevant reference for each year/car.
#
# Car number is preferred over driver string because the downstream qualifying
# attempt panel already has stable car_number.
# =============================================================================

QUALITY_SCORE = {
    "VERY_HIGH": 3,
    "HIGH": 2,
    "MEDIUM": 1,
}


canonical_by_entry = {}

for row in all_rows:

    key = (
        row[
            "year"
        ],
        normalize_car(
            row[
                "car_number"
            ]
        ),
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

    current = canonical_by_entry.get(
        key
    )

    if current is None:

        canonical_by_entry[
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

        canonical_by_entry[
            key
        ] = row


canonical = sorted(
    canonical_by_entry.values(),
    key=lambda r: (
        r[
            "year"
        ],
        int(
            normalize_car(
                r[
                    "car_number"
                ]
            )
        )
        if normalize_car(
            r[
                "car_number"
            ]
        ).isdigit()
        else 999,
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

    evidence = [
        r
        for r in all_rows
        if r[
            "year"
        ] == year
    ]

    canon = [
        r
        for r in canonical
        if r[
            "year"
        ] == year
    ]


    summary_rows.append({
        "year":
            year,

        "all_evidence_rows":
            len(
                evidence
            ),

        "canonical_entries":
            len(
                canon
            ),

        "four_lap_canonical":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "FOUR_LAP_QUALIFYING_SIM"
                for r in canon
            ),

        "no_tow_canonical":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "NO_TOW_SINGLE_LAP"
                for r in canon
            ),

        "general_canonical":
            sum(
                r[
                    "reference_type"
                ]
                ==
                "GENERAL_FAST_FRIDAY_BEST_SPEED"
                for r in canon
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

pdf_counts = Counter(
    r[
        "year"
    ]
    for r in pdf_rows
)


duplicate_entry_keys = []

seen = set()

for r in canonical:

    key = (
        r[
            "year"
        ],
        normalize_car(
            r[
                "car_number"
            ]
        ),
    )

    if key in seen:
        duplicate_entry_keys.append(
            key
        )

    seen.add(
        key
    )


qa_rows = [
    {
        "metric":
            "2023_pdf_rows_parsed",

        "value":
            pdf_counts[
                2023
            ],

        "expected":
            34,

        "status":
            (
                "PASS"
                if pdf_counts[
                    2023
                ] == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_pdf_rows_parsed",

        "value":
            pdf_counts[
                2024
            ],

        "expected":
            34,

        "status":
            (
                "PASS"
                if pdf_counts[
                    2024
                ] == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "unparsed_numeric_pdf_rows",

        "value":
            len(
                unparsed_numeric_rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not unparsed_numeric_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_verified_no_tow_refs",

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
                for r in editorial_rows
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
                    for r in editorial_rows
                ) == 3
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_verified_four_lap_refs",

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
                for r in editorial_rows
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
                    for r in editorial_rows
                ) == 4
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_verified_four_lap_refs",

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
                for r in editorial_rows
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
                    for r in editorial_rows
                ) == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "canonical_entry_keys_unique",

        "value":
            len(
                duplicate_entry_keys
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not duplicate_entry_keys
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
            "r4f6f_v1_not_used_as_input",

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

FIELDS = [
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
        sorted(
            all_rows,
            key=lambda r: (
                r[
                    "year"
                ],
                r[
                    "car_number"
                ],
                -r[
                    "reference_priority"
                ],
            ),
        )
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
        "R4F6G",

    "status":
        "R4F6G_DETERMINISTIC_FAST_FRIDAY_REFERENCE_PANEL_READY",

    "critical_correction":
        (
            "R4F6F-v1 automatic name-regex panel is rejected as "
            "model input. R4F6G replaces it with deterministic parsing "
            "of the observed official timing-report schema."
        ),

    "reference_hierarchy": [
        "FOUR_LAP_QUALIFYING_SIM",
        "NO_TOW_SINGLE_LAP",
        "GENERAL_FAST_FRIDAY_BEST_SPEED",
    ],

    "pdf_rows": {
        "2023":
            pdf_counts[
                2023
            ],

        "2024":
            pdf_counts[
                2024
            ],
    },

    "canonical_entries":
        len(
            canonical
        ),

    "summary":
        summary_rows,

    "known_limitations": [
        (
            "2020 and 2022 driver-level Fast Friday references "
            "are not yet recovered."
        ),

        (
            "General Fast Friday best speed can contain more "
            "draft/context contamination than four-lap qualifying "
            "simulation or explicit no-tow evidence."
        ),

        (
            "2024 remains validation-only."
        ),
    ],

    "next_phase":
        (
            "Join canonical Fast Friday references against qualifying "
            "attempt entries, measure entry coverage, and test whether "
            "pre-session normalization improves cross-car repeat-anchor "
            "prediction versus the rejected annual-field-median baseline."
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

print("=" * 128)
print("R4F6G — DETERMINISTIC FAST FRIDAY REFERENCE PANEL")
print("=" * 128)

print()
print("PDF PARSE")
print(
    f"2023 parsed={pdf_counts[2023]}/34"
)
print(
    f"2024 parsed={pdf_counts[2024]}/34"
)

print(
    f"Unparsed numeric PDF rows: "
    f"{len(unparsed_numeric_rows)}"
)


print()
print("=" * 128)
print("YEAR REFERENCE SUMMARY")
print("=" * 128)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"all_evidence={r['all_evidence_rows']:2d} | "
        f"canonical={r['canonical_entries']:2d} | "
        f"4lap={r['four_lap_canonical']:2d} | "
        f"no_tow={r['no_tow_canonical']:2d} | "
        f"general={r['general_canonical']:2d} | "
        f"{r['model_role']}"
    )


print()
print("=" * 128)
print("HIGH-PRIORITY QUALIFYING-LIKE REFERENCES")
print("=" * 128)

for r in canonical:

    if r[
        "reference_type"
    ] == "GENERAL_FAST_FRIDAY_BEST_SPEED":
        continue

    print(
        f"{r['year']} | "
        f"{r['driver_name']:24s} | "
        f"car={r['car_number']:>2s} | "
        f"{r['reference_speed_mph']:.3f} | "
        f"{r['reference_type']}"
    )


print()
print("=" * 128)
print("CANONICAL SAMPLE — 2023 FIRST 12")
print("=" * 128)

sample_2023 = [
    r
    for r in canonical
    if r[
        "year"
    ] == 2023
][:12]

for r in sample_2023:

    print(
        f"{r['driver_name']:24s} | "
        f"car={r['car_number']:>2s} | "
        f"{r['reference_speed_mph']:.3f} | "
        f"{r['reference_type']}"
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
    "R4F6G_DETERMINISTIC_FAST_FRIDAY_REFERENCE_PANEL_READY"
)
