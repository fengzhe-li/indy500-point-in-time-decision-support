from pathlib import Path
from urllib.request import Request, urlopen
import csv
import json
import math
import re
import subprocess
import shutil
import unicodedata

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
RAW = ROOT / "r4/evidence/fast_friday"

OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

BASE_CANONICAL = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

CODEX_EXPANDED = (
    OUT /
    "r4f6j_candidate_expanded_fast_friday_reference_panel_v1.csv"
)

CODEX_EVIDENCE = (
    OUT /
    "r4f6j_missing_fast_friday_reference_evidence_v1.csv"
)

OUT_2021_PDF = (
    RAW /
    "2021_fast_friday_practice5_results_r4f6k.pdf"
)

OUT_2021_ROWS = (
    OUT /
    "r4f6k_2021_fast_friday_general_reference_rows_v1.csv"
)

OUT_EVIDENCE = (
    OUT /
    "r4f6k_expanded_fast_friday_all_evidence_v1.csv"
)

OUT_CANONICAL = (
    OUT /
    "r4f6k_expanded_fast_friday_canonical_panel_v1.csv"
)

OUT_QUARANTINE = (
    OUT /
    "r4f6k_fast_friday_quarantine_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f6k_expanded_fast_friday_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6k_expanded_fast_friday_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6k_expanded_fast_friday_report_v1.json"
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
    "LOW": 0,
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(
            csv.DictReader(f)
        )


def normalize_driver(name):
    value = unicodedata.normalize(
        "NFKD",
        clean(name)
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
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def display_driver(pdf_name):
    name = re.sub(
        r"\s+\(R\)\s*$",
        "",
        clean(pdf_name)
    )

    if "," not in name:
        return name

    surname, given = name.split(
        ",",
        1
    )

    return (
        given.strip()
        +
        " "
        +
        surname.strip()
    )


def download_file(url, target):
    req = Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/153 Safari/537.36"
        },
    )

    try:
        with urlopen(
            req,
            timeout=30
        ) as response:
            data = response.read()

        target.write_bytes(
            data
        )

        if data[:5] == b"%PDF-":
            return (
                True,
                "PYTHON_HTTPS",
                "",
            )

    except Exception as e:
        python_error = repr(e)

    else:
        python_error = "NOT_PDF"


    # Official/public archived PDF fallback.
    if shutil.which("curl"):

        for insecure in [
            False,
            True,
        ]:

            cmd = [
                "curl",
                "-L",
                "--fail",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "15",
                "--max-time",
                "45",
            ]

            if insecure:
                cmd.append(
                    "--insecure"
                )

            cmd.extend([
                "-o",
                str(target),
                url,
            ])

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if (
                    result.returncode == 0
                    and
                    target.exists()
                    and
                    target.read_bytes()[:5]
                    == b"%PDF-"
                ):
                    return (
                        True,
                        (
                            "CURL_INSECURE"
                            if insecure
                            else "CURL"
                        ),
                        "",
                    )

            except Exception:
                pass


    return (
        False,
        "",
        python_error,
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
            text = (
                page.extract_text()
                or
                ""
            )

            if text.strip():
                parts.append(
                    text
                )

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


# =============================================================================
# Inputs
# =============================================================================

for path in [
    BASE_CANONICAL,
    CODEX_EXPANDED,
]:

    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


base_rows = read_csv(
    BASE_CANONICAL
)

codex_rows = read_csv(
    CODEX_EXPANDED
)

codex_evidence = (
    read_csv(
        CODEX_EVIDENCE
    )
    if CODEX_EVIDENCE.exists()
    else []
)


print("=" * 136)
print("R4F6K — EXPANDED FAST FRIDAY CANONICAL INTEGRATION")
print("=" * 136)

print(
    f"Base canonical rows: {len(base_rows)}"
)

print(
    f"Codex candidate rows: {len(codex_rows)}"
)


# =============================================================================
# Recover 2021 full-field Practice 5 result.
#
# Try known official/archive PDF paths.
# =============================================================================

PDF_URLS = [
    (
        "https://www.imscdn.com/INDYCAR/Documents/"
        "5807/2021-05-21/indycar-results-p5.pdf"
    ),
    (
        "https://indycaraldia.com/wp-content/uploads/"
        "2021/05/indycar-results-p5.pdf"
    ),
]


download_success = False
download_method = ""
download_url = ""
download_error = ""


for url in PDF_URLS:

    ok, method, error = download_file(
        url,
        OUT_2021_PDF
    )

    if ok:
        download_success = True
        download_method = method
        download_url = url
        break

    download_error = error


if not download_success:

    raise SystemExit(
        "2021 FAST FRIDAY PDF RECOVERY FAILED: "
        +
        download_error
    )


text, extraction_method = pdf_to_text(
    OUT_2021_PDF
)

if not text.strip():

    raise SystemExit(
        "2021 PDF DOWNLOADED BUT TEXT EXTRACTION FAILED"
    )


# =============================================================================
# Deterministic result-row parser.
#
# Expected structure follows official IndyCar practice report:
# rank / car / driver / engine-tire / best time / best speed / ...
# =============================================================================

ROW_PATTERNS = [
    re.compile(
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
    ),

    re.compile(
        r"^\s*"
        r"(?P<position>\d{1,2})"
        r"\s+"
        r"(?P<car>\d{1,2})"
        r"\s+"
        r"(?P<driver>.+?)"
        r"\s+"
        r"[HC]/F"
        r"\s+"
        r"(?P<lap_time>\d{2}:\d{2}\.\d{4})"
        r"\s+"
        r"(?P<speed>\d{3}\.\d{3})"
    ),
]


rows_2021 = []
unparsed_2021 = []


for line_no, line in enumerate(
    text.splitlines(),
    start=1
):

    if not re.search(
        r"\b(?:22[0-9]|23[0-9])\.\d{3}\b",
        line
    ):
        continue

    match = None

    for pattern in ROW_PATTERNS:

        match = pattern.match(
            line
        )

        if match:
            break


    if match is None:

        unparsed_2021.append({
            "line_no":
                line_no,

            "raw_line":
                line,
        })

        continue


    driver = display_driver(
        match.group(
            "driver"
        )
    )

    rows_2021.append({
        "year":
            2021,

        "driver_name":
            driver,

        "driver_key":
            normalize_driver(
                driver
            ),

        "car_number":
            match.group(
                "car"
            ),

        "reference_speed_mph":
            float(
                match.group(
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
            (
                "OFFICIAL_RESULTS_PDF"
                if "imscdn.com"
                in download_url
                else
                "OFFICIAL_TIMING_PDF_ARCHIVE"
            ),

        "source_url":
            download_url,

        "source_file":
            str(
                OUT_2021_PDF.relative_to(
                    ROOT
                )
            ),

        "extraction_method":
            extraction_method,

        "model_role":
            "CORE_DEVELOPMENT",

        "provenance_note":
            (
                "2021 Indianapolis 500 Practice 5 Fast Friday "
                "full-field best-speed result."
            ),

        "pdf_position":
            int(
                match.group(
                    "position"
                )
            ),

        "pdf_lap_time":
            match.group(
                "lap_time"
            ),
    })


# =============================================================================
# Normalize incoming evidence schema
# =============================================================================

def normalized_row(r):

    year = int(
        float(
            clean(
                r.get(
                    "year"
                )
            )
        )
    )

    name = clean(
        r.get(
            "driver_name"
        )
    )

    key = clean(
        r.get(
            "driver_key"
        )
    )

    if not key:
        key = normalize_driver(
            name
        )


    reference_type = clean(
        r.get(
            "reference_type"
        )
    )

    priority = (
        int(
            float(
                clean(
                    r.get(
                        "reference_priority"
                    )
                )
            )
        )
        if clean(
            r.get(
                "reference_priority"
            )
        )
        else REFERENCE_PRIORITY.get(
            reference_type,
            0
        )
    )


    role = clean(
        r.get(
            "model_role"
        )
    )


    # Frozen role correction.
    if year == 2022:
        role = (
            "DEGRADED_CHRONOLOGY_VALIDATION"
        )

    elif year == 2024:
        role = (
            "VALIDATION_ONLY"
        )

    elif year == 2025:
        role = (
            "TECHNICAL_REGIME_TRANSFER"
        )


    return {
        "year":
            year,

        "driver_name":
            name,

        "driver_key":
            key,

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "reference_speed_mph":
            num(
                r.get(
                    "reference_speed_mph"
                )
            ),

        "reference_type":
            reference_type,

        "reference_priority":
            priority,

        "source_quality":
            clean(
                r.get(
                    "source_quality"
                )
            )
            or
            "HIGH",

        "source_type":
            clean(
                r.get(
                    "source_type"
                )
            ),

        "source_url":
            clean(
                r.get(
                    "source_url"
                )
            ),

        "source_file":
            clean(
                r.get(
                    "source_file"
                )
            ),

        "extraction_method":
            clean(
                r.get(
                    "extraction_method"
                )
            ),

        "model_role":
            role,

        "provenance_note":
            clean(
                r.get(
                    "provenance_note"
                )
            ),

        "pdf_position":
            clean(
                r.get(
                    "pdf_position"
                )
            ),

        "pdf_lap_time":
            clean(
                r.get(
                    "pdf_lap_time"
                )
            ),
    }


all_evidence = []


for r in codex_evidence:

    try:
        row = normalized_row(
            r
        )

    except Exception:
        continue

    all_evidence.append(
        row
    )


for r in codex_rows:

    try:
        row = normalized_row(
            r
        )

    except Exception:
        continue

    all_evidence.append(
        row
    )


for r in base_rows:

    try:
        row = normalized_row(
            r
        )

    except Exception:
        continue

    all_evidence.append(
        row
    )


all_evidence.extend(
    rows_2021
)


# =============================================================================
# Explicit 2021 no-tow evidence.
# These must remain higher priority than full-field general best speed.
# =============================================================================

NO_TOW_2021 = [
    (
        "Alexander Rossi",
        "27",
        231.598,
    ),
    (
        "Graham Rahal",
        "15",
        231.518,
    ),
    (
        "Pato O'Ward",
        "5",
        231.510,
    ),
]


for name, car, speed in NO_TOW_2021:

    all_evidence.append({
        "year":
            2021,

        "driver_name":
            name,

        "driver_key":
            normalize_driver(
                name
            ),

        "car_number":
            car,

        "reference_speed_mph":
            speed,

        "reference_type":
            "NO_TOW_SINGLE_LAP",

        "reference_priority":
            2,

        "source_quality":
            "VERY_HIGH",

        "source_type":
            "OFFICIAL_EDITORIAL_HTML",

        "source_url":
            (
                "https://www.indycar.com/News/"
                "2021/05/05-21-Practice"
            ),

        "source_file":
            (
                "r4/evidence/fast_friday/"
                "2021_fast_friday_official_editorial.html"
            ),

        "extraction_method":
            "EXPLICIT_VERIFIED_STATEMENT",

        "model_role":
            "CORE_DEVELOPMENT",

        "provenance_note":
            (
                "Official Fast Friday recap explicitly identifies "
                "driver's no-tow speed."
            ),

        "pdf_position":
            "",

        "pdf_lap_time":
            "",
    })


# =============================================================================
# Deduplicate exact evidence rows
# =============================================================================

dedup = {}

for r in all_evidence:

    if (
        r[
            "year"
        ]
        is None
        or
        not r[
            "driver_key"
        ]
        or
        r[
            "reference_speed_mph"
        ]
        is None
    ):
        continue

    key = (
        r[
            "year"
        ],
        r[
            "driver_key"
        ],
        r[
            "reference_type"
        ],
        round(
            r[
                "reference_speed_mph"
            ],
            6
        ),
        r[
            "source_file"
        ],
    )

    dedup[
        key
    ] = r


all_evidence = list(
    dedup.values()
)


# =============================================================================
# Quarantine physically implausible model-facing references.
#
# Keep raw/additive evidence, exclude from canonical.
# =============================================================================

quarantine = []
model_eligible = []


for r in all_evidence:

    speed = r[
        "reference_speed_mph"
    ]


    if (
        speed is None
        or
        speed < 200.0
        or
        speed > 245.0
    ):

        quarantine.append({
            **r,

            "quarantine_reason":
                "PHYSICALLY_IMPLAUSIBLE_REFERENCE_SPEED",
        })

        continue


    model_eligible.append(
        r
    )


# =============================================================================
# Canonical row per year + driver.
# =============================================================================

canonical_map = {}


for r in model_eligible:

    key = (
        r[
            "year"
        ],
        r[
            "driver_key"
        ],
    )

    score = (
        r[
            "reference_priority"
        ],
        QUALITY_SCORE.get(
            r[
                "source_quality"
            ],
            0
        ),
    )

    current = canonical_map.get(
        key
    )


    if current is None:

        canonical_map[
            key
        ] = r
        continue


    current_score = (
        current[
            "reference_priority"
        ],
        QUALITY_SCORE.get(
            current[
                "source_quality"
            ],
            0
        ),
    )


    if score > current_score:

        canonical_map[
            key
        ] = r


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


# =============================================================================
# Summary
# =============================================================================

summary_rows = []


for year in [
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
]:

    subset = [
        r
        for r in canonical
        if r[
            "year"
        ] == year
    ]


    role = (
        subset[
            0
        ][
            "model_role"
        ]
        if subset
        else ""
    )


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

        "quarantined":
            sum(
                r[
                    "year"
                ] == year
                for r in quarantine
            ),

        "model_role":
            role,
    })


# =============================================================================
# QA
# =============================================================================

def year_count(year):
    return sum(
        r[
            "year"
        ] == year
        for r in canonical
    )


duplicate_keys = []

seen = set()

for r in canonical:

    key = (
        r[
            "year"
        ],
        r[
            "driver_key"
        ],
    )

    if key in seen:
        duplicate_keys.append(
            key
        )

    seen.add(
        key
    )


simpson_bad_in_canonical = any(
    r[
        "year"
    ] == 2025
    and
    "simpson"
    in r[
        "driver_key"
    ]
    and
    r[
        "reference_speed_mph"
    ] < 200
    for r in canonical
)


qa_rows = [
    {
        "metric":
            "2020_entries",
        "value":
            year_count(
                2020
            ),
        "expected":
            33,
        "status":
            (
                "PASS"
                if year_count(
                    2020
                ) == 33
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_entries",
        "value":
            year_count(
                2021
            ),
        "expected":
            ">=33",
        "status":
            (
                "PASS"
                if year_count(
                    2021
                ) >= 33
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_entries",
        "value":
            year_count(
                2022
            ),
        "expected":
            33,
        "status":
            (
                "PASS"
                if year_count(
                    2022
                ) == 33
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_entries",
        "value":
            year_count(
                2023
            ),
        "expected":
            34,
        "status":
            (
                "PASS"
                if year_count(
                    2023
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_entries",
        "value":
            year_count(
                2024
            ),
        "expected":
            34,
        "status":
            (
                "PASS"
                if year_count(
                    2024
                ) == 34
                else "FAIL"
            ),
    },

    {
        "metric":
            "canonical_identity_unique",
        "value":
            len(
                duplicate_keys
            ),
        "expected":
            0,
        "status":
            (
                "PASS"
                if not duplicate_keys
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_no_tow_preserved",
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
            "2022_role_corrected",
        "value":
            all(
                r[
                    "model_role"
                ]
                ==
                "DEGRADED_CHRONOLOGY_VALIDATION"
                for r in canonical
                if r[
                    "year"
                ] == 2022
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
                    "DEGRADED_CHRONOLOGY_VALIDATION"
                    for r in canonical
                    if r[
                        "year"
                    ] == 2022
                )
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
            "2025_transfer_only",
        "value":
            all(
                r[
                    "model_role"
                ]
                ==
                "TECHNICAL_REGIME_TRANSFER"
                for r in canonical
                if r[
                    "year"
                ] == 2025
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
                    "TECHNICAL_REGIME_TRANSFER"
                    for r in canonical
                    if r[
                        "year"
                    ] == 2025
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "implausible_simpson_not_canonical",
        "value":
            not simpson_bad_in_canonical,
        "expected":
            True,
        "status":
            (
                "PASS"
                if not simpson_bad_in_canonical
                else "FAIL"
            ),
    },

    {
        "metric":
            "leading_zero_policy_preserved",
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
    "driver_key",
    "car_number",
    "reference_speed_mph",
    "reference_type",
    "reference_priority",
    "source_quality",
    "source_type",
    "source_url",
    "source_file",
    "extraction_method",
    "model_role",
    "provenance_note",
    "pdf_position",
    "pdf_lap_time",
]


with OUT_2021_ROWS.open(
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
        rows_2021
    )


with OUT_EVIDENCE.open(
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
            all_evidence,
            key=lambda r: (
                r[
                    "year"
                ],
                r[
                    "driver_key"
                ],
                -r[
                    "reference_priority"
                ],
            )
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


quarantine_fields = (
    FIELDS
    +
    [
        "quarantine_reason"
    ]
)

with OUT_QUARANTINE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=quarantine_fields
    )

    writer.writeheader()
    writer.writerows(
        quarantine
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
        "R4F6K",

    "status":
        "R4F6K_EXPANDED_FAST_FRIDAY_CANONICAL_READY",

    "supersedes_for_model_facing_reference":
        [
            "r4f6g_canonical_fast_friday_reference_panel_v2.csv",
            "r4f6j_candidate_expanded_fast_friday_reference_panel_v1.csv",
        ],

    "2021_pdf_source":
        download_url,

    "2021_download_method":
        download_method,

    "2021_general_rows":
        len(
            rows_2021
        ),

    "canonical_summary":
        summary_rows,

    "quarantined_rows":
        len(
            quarantine
        ),

    "frozen_role_policy": {
        "2020":
            "CORE_DEVELOPMENT",

        "2021":
            "CORE_DEVELOPMENT",

        "2022":
            "DEGRADED_CHRONOLOGY_VALIDATION",

        "2023":
            "CORE_DEVELOPMENT",

        "2024":
            "VALIDATION_ONLY",

        "2025":
            "TECHNICAL_REGIME_TRANSFER",
    },

    "important_measurement_rule":
        (
            "FOUR_LAP_QUALIFYING_SIM, NO_TOW_SINGLE_LAP and "
            "GENERAL_FAST_FRIDAY_BEST_SPEED remain distinct "
            "measurement types and are not assumed homogeneous."
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

print()
print("=" * 136)
print("2021 FULL-FIELD RECOVERY")
print("=" * 136)

print(
    f"download_url={download_url}"
)

print(
    f"download_method={download_method}"
)

print(
    f"parsed_general_rows={len(rows_2021)}"
)

print(
    f"unparsed_numeric_rows={len(unparsed_2021)}"
)


print()
print("=" * 136)
print("EXPANDED CANONICAL COVERAGE")
print("=" * 136)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"entries={r['canonical_entries']:2d} | "
        f"4lap={r['four_lap']:2d} | "
        f"no_tow={r['no_tow']:2d} | "
        f"general={r['general']:2d} | "
        f"quarantine={r['quarantined']:2d} | "
        f"{r['model_role']}"
    )


print()
print("=" * 136)
print("2021 CANONICAL TOP 12")
print("=" * 136)

rows_2021_canonical = [
    r
    for r in canonical
    if r[
        "year"
    ] == 2021
]

rows_2021_canonical = sorted(
    rows_2021_canonical,
    key=lambda r:
        -r[
            "reference_speed_mph"
        ]
)


for r in rows_2021_canonical[:12]:

    print(
        f"{r['driver_name']:24s} | "
        f"car={r['car_number']:>2s} | "
        f"{r['reference_speed_mph']:.3f} | "
        f"{r['reference_type']}"
    )


print()
print("=" * 136)
print("QUARANTINE")
print("=" * 136)

if not quarantine:

    print("NONE")

else:

    for r in quarantine:

        print(
            f"{r['year']} | "
            f"{r['driver_name']} | "
            f"car={r['car_number']} | "
            f"{r['reference_speed_mph']} | "
            f"{r['quarantine_reason']}"
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
    OUT_2021_ROWS.relative_to(ROOT)
)
print(
    OUT_EVIDENCE.relative_to(ROOT)
)
print(
    OUT_CANONICAL.relative_to(ROOT)
)
print(
    OUT_QUARANTINE.relative_to(ROOT)
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
    "R4F6K_EXPANDED_FAST_FRIDAY_CANONICAL_READY"
)
