from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser
import csv
import json
import re
import shutil
import subprocess
import ssl

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
RAW = ROOT / "r4/evidence/fast_friday"

OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = (
    OUT /
    "r4f6d_fast_friday_numeric_acquisition_manifest_v1.csv"
)

OUT_RECOVERY = (
    OUT /
    "r4f6e_fast_friday_pdf_recovery_v1.csv"
)

OUT_EVIDENCE = (
    OUT /
    "r4f6e_fast_friday_numeric_content_audit_v1.csv"
)

OUT_YEAR = (
    OUT /
    "r4f6e_fast_friday_numeric_year_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6e_fast_friday_numeric_audit_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6e_fast_friday_numeric_audit_report_v1.json"
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
    try:
        raw = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        parser = VisibleTextParser()
        parser.feed(
            raw
        )

        return parser.text()

    except Exception:
        return ""


def pdf_to_text(path):
    # ------------------------------------------------------------
    # First preference: pdftotext
    # ------------------------------------------------------------

    if shutil.which(
        "pdftotext"
    ):

        try:
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

        except Exception:
            pass

    # ------------------------------------------------------------
    # Second preference: pypdf
    # ------------------------------------------------------------

    try:
        from pypdf import PdfReader

        reader = PdfReader(
            str(path)
        )

        parts = []

        for page in reader.pages:
            try:
                text = (
                    page.extract_text()
                    or
                    ""
                )

                if text.strip():
                    parts.append(
                        text
                    )

            except Exception:
                continue

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


def looks_like_pdf(path):
    try:
        data = path.read_bytes()[:5]
        return data == b"%PDF-"

    except Exception:
        return False


def python_download(
    url,
    target,
):
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
            timeout=30,
        ) as response:

            data = response.read()

        target.write_bytes(
            data
        )

        if looks_like_pdf(
            target
        ):
            return (
                True,
                "PYTHON_HTTPS",
                "",
            )

        try:
            target.unlink()
        except Exception:
            pass

        return (
            False,
            "PYTHON_HTTPS",
            "DOWNLOADED_CONTENT_NOT_PDF",
        )

    except Exception as e:

        return (
            False,
            "PYTHON_HTTPS",
            repr(
                e
            ),
        )


def curl_download(
    url,
    target,
    insecure=False,
):
    if not shutil.which(
        "curl"
    ):
        return (
            False,
            "CURL_UNAVAILABLE",
            "curl not found",
        )

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
        "-A",
        (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/153 Safari/537.36"
        ),
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
            timeout=60,
        )

    except Exception as e:
        return (
            False,
            (
                "CURL_INSECURE"
                if insecure
                else
                "CURL"
            ),
            repr(
                e
            ),
        )


    method = (
        "CURL_INSECURE"
        if insecure
        else
        "CURL"
    )


    if result.returncode != 0:

        try:
            if target.exists():
                target.unlink()
        except Exception:
            pass

        return (
            False,
            method,
            result.stderr.strip(),
        )


    if looks_like_pdf(
        target
    ):
        return (
            True,
            method,
            "",
        )


    try:
        if target.exists():
            target.unlink()
    except Exception:
        pass


    return (
        False,
        method,
        "DOWNLOADED_CONTENT_NOT_PDF",
    )


def recover_pdf(
    original_url,
    target,
):
    attempts = []

    corrected_url = (
        original_url
        .replace(
            "https://www.imscdn.com/",
            "https://imscdn.com/"
        )
    )

    urls = []

    for url in [
        corrected_url,
        original_url,
    ]:

        if url not in urls:
            urls.append(
                url
            )


    # ------------------------------------------------------------
    # 1. Normal Python HTTPS
    # ------------------------------------------------------------

    for url in urls:

        ok, method, error = python_download(
            url,
            target,
        )

        attempts.append({
            "url":
                url,

            "method":
                method,

            "success":
                ok,

            "error":
                error,
        })

        if ok:
            return (
                True,
                url,
                method,
                attempts,
            )


    # ------------------------------------------------------------
    # 2. Normal curl
    # ------------------------------------------------------------

    for url in urls:

        ok, method, error = curl_download(
            url,
            target,
            insecure=False,
        )

        attempts.append({
            "url":
                url,

            "method":
                method,

            "success":
                ok,

            "error":
                error,
        })

        if ok:
            return (
                True,
                url,
                method,
                attempts,
            )


    # ------------------------------------------------------------
    # 3. Last resort:
    # public static official PDF + explicit PDF signature check.
    #
    # This bypasses certificate validation only for retrieval.
    # The result is rejected unless it is actually a PDF.
    # ------------------------------------------------------------

    for url in urls:

        ok, method, error = curl_download(
            url,
            target,
            insecure=True,
        )

        attempts.append({
            "url":
                url,

            "method":
                method,

            "success":
                ok,

            "error":
                error,
        })

        if ok:
            return (
                True,
                url,
                method,
                attempts,
            )


    return (
        False,
        "",
        "",
        attempts,
    )


def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def snippets_for_pattern(
    text,
    pattern,
    radius=220,
    limit=20,
):
    snippets = []

    for m in re.finditer(
        pattern,
        text,
        flags=re.IGNORECASE,
    ):

        start = max(
            0,
            m.start() - radius,
        )

        end = min(
            len(text),
            m.end() + radius,
        )

        snippet = normalize_text(
            text[start:end]
        )

        snippets.append(
            snippet
        )

        if len(snippets) >= limit:
            break

    return snippets


if not MANIFEST_PATH.exists():

    raise SystemExit(
        f"MISSING INPUT: {MANIFEST_PATH}"
    )


manifest = read_csv(
    MANIFEST_PATH
)


print("=" * 128)
print("R4F6E — FAST FRIDAY PDF RECOVERY + NUMERIC CONTENT AUDIT")
print("=" * 128)

print(
    f"R4F6D manifest rows: "
    f"{len(manifest)}"
)


# =============================================================================
# PDF recovery
# =============================================================================

recovery_rows = []

for r in manifest:

    if clean(
        r.get(
            "source_type"
        )
    ) != "OFFICIAL_RESULTS_PDF":
        continue

    year = int(
        r[
            "year"
        ]
    )

    target = (
        ROOT /
        r[
            "local_file"
        ]
    )

    original_url = clean(
        r[
            "url"
        ]
    )


    print()
    print(
        f"PDF RECOVERY | {year}"
    )


    if (
        target.exists()
        and
        looks_like_pdf(
            target
        )
    ):

        print(
            "Already present and valid PDF."
        )

        success = True
        final_url = original_url
        method = "ALREADY_PRESENT"
        attempts = []

    else:

        (
            success,
            final_url,
            method,
            attempts,
        ) = recover_pdf(
            original_url,
            target,
        )


    print(
        f"success={success} | "
        f"method={method or '-'} | "
        f"bytes="
        f"{target.stat().st_size if target.exists() else 0}"
    )


    recovery_rows.append({
        "year":
            year,

        "original_url":
            original_url,

        "final_url":
            final_url,

        "local_file":
            str(
                target.relative_to(
                    ROOT
                )
            ),

        "success":
            success,

        "recovery_method":
            method,

        "valid_pdf_signature":
            (
                looks_like_pdf(
                    target
                )
                if target.exists()
                else False
            ),

        "bytes":
            (
                target.stat().st_size
                if target.exists()
                else 0
            ),

        "attempt_count":
            len(
                attempts
            ),

        "attempt_log":
            json.dumps(
                attempts,
                ensure_ascii=False,
            ),
    })


# =============================================================================
# Build complete acquired asset inventory
# =============================================================================

assets = []

for r in manifest:

    local = ROOT / r[
        "local_file"
    ]

    if not local.exists():
        continue

    source_type = clean(
        r[
            "source_type"
        ]
    )

    # Reject failed/non-PDF remnants.
    if (
        source_type
        ==
        "OFFICIAL_RESULTS_PDF"
        and
        not looks_like_pdf(
            local
        )
    ):
        continue

    assets.append({
        "year":
            int(
                r[
                    "year"
                ]
            ),

        "session":
            clean(
                r[
                    "session"
                ]
            ),

        "source_type":
            source_type,

        "reference_role":
            clean(
                r[
                    "reference_role"
                ]
            ),

        "file":
            local,
    })


# Add recovered PDFs in case R4F6D marked them failed.
for rr in recovery_rows:

    if not rr[
        "success"
    ]:
        continue

    path = ROOT / rr[
        "local_file"
    ]

    if any(
        a[
            "file"
        ] == path
        for a in assets
    ):
        continue

    year = rr[
        "year"
    ]

    assets.append({
        "year":
            year,

        "session":
            "Practice 5 (Fast Friday)",

        "source_type":
            "OFFICIAL_RESULTS_PDF",

        "reference_role":
            (
                "VALIDATION_FOUR_LAP_QUALIFYING_SIM"
                if year == 2024
                else
                "FOUR_LAP_QUALIFYING_SIM_HIGH_PRIORITY"
            ),

        "file":
            path,
    })


# =============================================================================
# Extract visible text
# =============================================================================

evidence_rows = []

FOUR_LAP_PATTERNS = [
    r"four[-\s]?lap",
    r"4[-\s]?lap",
    r"four lap average",
    r"four-lap average",
]

QUAL_SIM_PATTERNS = [
    r"qualifying simulation",
    r"qualifying sim",
    r"qualification simulation",
]

NO_TOW_PATTERNS = [
    r"no[-\s]?tow",
    r"without a tow",
    r"without tow",
    r"clean air",
]

MPH_PATTERN = (
    r"\b(?:22[0-9]|23[0-9]|24[0-9])"
    r"\.\d{2,3}\s*(?:mph)?\b"
)

DRIVER_CONTEXT_PATTERNS = [
    r"\bdriver\b",
    r"\bcar\b",
    r"\bposition\b",
    r"\bpos\b",
]


for asset in sorted(
    assets,
    key=lambda a: (
        a[
            "year"
        ],
        a[
            "source_type"
        ],
        str(
            a[
                "file"
            ]
        ),
    )
):

    path = asset[
        "file"
    ]

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


    text_length = len(
        text
    )

    four_lap_hits = sum(
        len(
            re.findall(
                p,
                text,
                flags=re.IGNORECASE,
            )
        )
        for p in FOUR_LAP_PATTERNS
    )

    qual_sim_hits = sum(
        len(
            re.findall(
                p,
                text,
                flags=re.IGNORECASE,
            )
        )
        for p in QUAL_SIM_PATTERNS
    )

    no_tow_hits = sum(
        len(
            re.findall(
                p,
                text,
                flags=re.IGNORECASE,
            )
        )
        for p in NO_TOW_PATTERNS
    )

    mph_matches = re.findall(
        MPH_PATTERN,
        text,
        flags=re.IGNORECASE,
    )

    driver_context_score = sum(
        1
        for p in DRIVER_CONTEXT_PATTERNS
        if re.search(
            p,
            text,
            flags=re.IGNORECASE,
        )
    )


    four_contexts = []

    for p in (
        FOUR_LAP_PATTERNS
        +
        QUAL_SIM_PATTERNS
    ):

        four_contexts.extend(
            snippets_for_pattern(
                text,
                p,
                radius=260,
                limit=5,
            )
        )


    no_tow_contexts = []

    for p in NO_TOW_PATTERNS:

        no_tow_contexts.extend(
            snippets_for_pattern(
                text,
                p,
                radius=260,
                limit=5,
            )
        )


    if (
        four_lap_hits > 0
        or
        qual_sim_hits > 0
    ) and mph_matches:

        semantic_grade = (
            "HIGH_FOUR_LAP_OR_QUAL_SIM_NUMERIC"
        )

    elif (
        no_tow_hits > 0
        and
        mph_matches
    ):

        semantic_grade = (
            "HIGH_NO_TOW_NUMERIC"
        )

    elif (
        len(
            mph_matches
        ) >= 5
        and
        driver_context_score >= 2
    ):

        semantic_grade = (
            "MEDIUM_SESSION_NUMERIC"
        )

    elif mph_matches:

        semantic_grade = (
            "LOW_NUMERIC_CONTEXT"
        )

    else:

        semantic_grade = (
            "NO_NUMERIC_REFERENCE_CONTENT"
        )


    evidence_rows.append({
        "year":
            asset[
                "year"
            ],

        "session":
            asset[
                "session"
            ],

        "source_type":
            asset[
                "source_type"
            ],

        "reference_role":
            asset[
                "reference_role"
            ],

        "local_file":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "extraction_method":
            extraction_method,

        "text_length":
            text_length,

        "four_lap_hits":
            four_lap_hits,

        "qualifying_sim_hits":
            qual_sim_hits,

        "no_tow_hits":
            no_tow_hits,

        "mph_numeric_hits":
            len(
                mph_matches
            ),

        "driver_context_score":
            driver_context_score,

        "semantic_grade":
            semantic_grade,

        "sample_mph_values":
            ";".join(
                mph_matches[:20]
            ),

        "four_lap_context_1":
            (
                four_contexts[0]
                if len(
                    four_contexts
                ) >= 1
                else ""
            ),

        "four_lap_context_2":
            (
                four_contexts[1]
                if len(
                    four_contexts
                ) >= 2
                else ""
            ),

        "no_tow_context_1":
            (
                no_tow_contexts[0]
                if len(
                    no_tow_contexts
                ) >= 1
                else ""
            ),
    })


# =============================================================================
# Year summary
# =============================================================================

year_rows = []

for year in [
    2020,
    2021,
    2022,
    2023,
    2024,
]:

    subset = [
        r
        for r in evidence_rows
        if r[
            "year"
        ] == year
    ]

    grades = [
        r[
            "semantic_grade"
        ]
        for r in subset
    ]


    if (
        "HIGH_FOUR_LAP_OR_QUAL_SIM_NUMERIC"
        in grades
    ):

        best_evidence = (
            "FOUR_LAP_OR_QUAL_SIM_NUMERIC"
        )

    elif (
        "HIGH_NO_TOW_NUMERIC"
        in grades
    ):

        best_evidence = (
            "NO_TOW_NUMERIC"
        )

    elif (
        "MEDIUM_SESSION_NUMERIC"
        in grades
    ):

        best_evidence = (
            "GENERAL_SESSION_NUMERIC"
        )

    elif subset:

        best_evidence = (
            "WEAK_OR_CONTEXT_ONLY"
        )

    else:

        best_evidence = (
            "NO_LOCAL_ACQUIRED_ASSET"
        )


    year_rows.append({
        "year":
            year,

        "assets":
            len(
                subset
            ),

        "four_lap_or_qual_sim_assets":
            sum(
                r[
                    "semantic_grade"
                ]
                ==
                "HIGH_FOUR_LAP_OR_QUAL_SIM_NUMERIC"
                for r in subset
            ),

        "no_tow_numeric_assets":
            sum(
                r[
                    "semantic_grade"
                ]
                ==
                "HIGH_NO_TOW_NUMERIC"
                for r in subset
            ),

        "general_session_numeric_assets":
            sum(
                r[
                    "semantic_grade"
                ]
                ==
                "MEDIUM_SESSION_NUMERIC"
                for r in subset
            ),

        "total_mph_hits":
            sum(
                int(
                    r[
                        "mph_numeric_hits"
                    ]
                )
                for r in subset
            ),

        "best_local_evidence":
            best_evidence,

        "model_role":
            (
                "VALIDATION_ONLY"
                if year == 2024
                else
                "DEGRADED_VALIDATION"
                if year == 2022
                else
                "CORE_DEVELOPMENT"
            ),
    })


# =============================================================================
# QA
# =============================================================================

valid_recovered_pdfs = sum(
    1
    for r in recovery_rows
    if (
        r[
            "success"
        ]
        and
        r[
            "valid_pdf_signature"
        ]
    )
)


qa_rows = [
    {
        "metric":
            "r4f6d_manifest_rows",

        "value":
            len(
                manifest
            ),

        "expected":
            10,

        "status":
            (
                "PASS"
                if len(
                    manifest
                ) == 10
                else "FAIL"
            ),
    },

    {
        "metric":
            "pdf_recovery_attempts",

        "value":
            len(
                recovery_rows
            ),

        "expected":
            2,

        "status":
            (
                "PASS"
                if len(
                    recovery_rows
                ) == 2
                else "FAIL"
            ),
    },

    {
        "metric":
            "recovered_pdf_signature_valid",

        "value":
            valid_recovered_pdfs,

        "expected":
            "0_to_2_observed",

        "status":
            "PASS",
    },

    {
        "metric":
            "content_assets_audited",

        "value":
            len(
                evidence_rows
            ),

        "expected":
            ">=8",

        "status":
            (
                "PASS"
                if len(
                    evidence_rows
                ) >= 8
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
                for r in year_rows
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
                    for r in year_rows
                    if r[
                        "year"
                    ] == 2024
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_RECOVERY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            recovery_rows[0].keys()
        )
        if recovery_rows
        else [
            "year",
            "success",
        ]
    )

    writer.writeheader()
    writer.writerows(
        recovery_rows
    )


with OUT_EVIDENCE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            evidence_rows[0].keys()
        )
        if evidence_rows
        else [
            "year",
            "semantic_grade",
        ]
    )

    writer.writeheader()
    writer.writerows(
        evidence_rows
    )


with OUT_YEAR.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            year_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        year_rows
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
        "R4F6E",

    "status":
        "R4F6E_FAST_FRIDAY_NUMERIC_CONTENT_AUDIT_READY",

    "pdf_recovery_attempted":
        len(
            recovery_rows
        ),

    "pdf_recovered":
        valid_recovered_pdfs,

    "assets_audited":
        len(
            evidence_rows
        ),

    "year_summary":
        year_rows,

    "reference_hierarchy": [
        "FOUR_LAP_QUALIFYING_SIM",
        "NO_TOW_SINGLE_LAP",
        "GENERAL_FAST_FRIDAY_SESSION_SPEED",
    ],

    "important_constraint":
        (
            "Numeric content detection does not yet create "
            "a canonical entry reference. Driver-level extraction "
            "and row-level provenance are required next."
        ),

    "next_phase":
        (
            "Extract driver/car-level Fast Friday reference rows "
            "from the strongest verified assets and quantify "
            "coverage against Day1 qualifying entries."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 128)
print("PDF RECOVERY SUMMARY")
print("=" * 128)

for r in recovery_rows:

    print(
        f"{r['year']} | "
        f"success={r['success']} | "
        f"method={r['recovery_method'] or '-'} | "
        f"valid_pdf={r['valid_pdf_signature']} | "
        f"bytes={r['bytes']}"
    )


print()
print("=" * 128)
print("NUMERIC CONTENT AUDIT")
print("=" * 128)

for r in evidence_rows:

    print(
        f"{r['year']} | "
        f"{r['source_type']:24s} | "
        f"{r['semantic_grade']:38s} | "
        f"4lap={r['four_lap_hits']:2d} | "
        f"qualsim={r['qualifying_sim_hits']:2d} | "
        f"notow={r['no_tow_hits']:2d} | "
        f"mph={r['mph_numeric_hits']:3d}"
    )


print()
print("=" * 128)
print("YEAR REFERENCE READINESS")
print("=" * 128)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"assets={r['assets']:2d} | "
        f"4lap/qualsim={r['four_lap_or_qual_sim_assets']:2d} | "
        f"no_tow={r['no_tow_numeric_assets']:2d} | "
        f"general={r['general_session_numeric_assets']:2d} | "
        f"mph_hits={r['total_mph_hits']:3d} | "
        f"{r['best_local_evidence']} | "
        f"{r['model_role']}"
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
    OUT_RECOVERY.relative_to(ROOT)
)
print(
    OUT_EVIDENCE.relative_to(ROOT)
)
print(
    OUT_YEAR.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6E_FAST_FRIDAY_NUMERIC_CONTENT_AUDIT_READY"
)
