from pathlib import Path
from collections import defaultdict, Counter
import csv
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

AUDIT_PATH = (
    OUT /
    "r4f6a_presession_physical_local_assets_v1.csv"
)

OUT_VERIFIED = (
    OUT /
    "r4f6b_presession_candidate_semantic_verification_v1.csv"
)

OUT_YEAR = (
    OUT /
    "r4f6b_presession_candidate_year_coverage_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6b_presession_candidate_semantic_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6b_presession_candidate_semantic_report_v1.json"
)


TEXT_EXTENSIONS = {
    ".txt",
    ".csv",
    ".json",
    ".md",
    ".html",
    ".htm",
}

YEARS = [
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
]


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


def safe_read(path, limit=250000):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )[:limit]
    except Exception:
        return ""


def detect_years(text):
    return [
        year
        for year in YEARS
        if str(year) in text
    ]


def count_pattern(text, patterns):
    total = 0

    for pattern in patterns:
        total += len(
            re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    return total


def has_pattern(text, patterns):
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def extract_contexts(
    text,
    anchor_patterns,
    radius=350,
    max_hits=12,
):
    contexts = []

    for pattern in anchor_patterns:

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

            snippet = (
                text[start:end]
                .replace("\n", " ")
                .replace("\r", " ")
            )

            snippet = re.sub(
                r"\s+",
                " ",
                snippet,
            ).strip()

            contexts.append(
                snippet
            )

            if len(contexts) >= max_hits:
                return contexts

    return contexts


if not AUDIT_PATH.exists():
    raise SystemExit(
        f"MISSING INPUT: {AUDIT_PATH}"
    )


audit = read_csv(
    AUDIT_PATH
)


print("=" * 126)
print("R4F6B — PRE-SESSION CANDIDATE SEMANTIC VERIFICATION")
print("=" * 126)

print(
    f"R4F6A candidate rows: {len(audit)}"
)


# =============================================================================
# Candidate selection
#
# Only candidates containing FAST_FRIDAY are inspected here.
# Generated R4 reports are excluded because they only repeat methodology text.
# =============================================================================

candidate_rows = []

for r in audit:

    categories = set(
        clean(
            r.get(
                "categories"
            )
        ).split(";")
    )

    rel = clean(
        r.get(
            "file"
        )
    )

    if "FAST_FRIDAY" not in categories:
        continue

    if rel.startswith(
        "r4/output/"
    ):
        continue

    path = ROOT / rel

    if (
        not path.exists()
        or
        path.suffix.lower()
        not in TEXT_EXTENSIONS
    ):
        continue

    candidate_rows.append(
        {
            "audit":
                r,

            "path":
                path,

            "rel":
                rel,
        }
    )


print(
    f"Candidates after generated-report exclusion: "
    f"{len(candidate_rows)}"
)


# =============================================================================
# Semantic evidence rules
# =============================================================================

FAST_FRIDAY_PATTERNS = [
    r"\bfast\s+friday\b",
    r"\bfast[-_]friday\b",
]

SPEED_PATTERNS = [
    r"\b\d{3}\.\d{2,3}\s*mph\b",
    r"\b\d{3}\.\d{2,3}\b",
    r"\bspeed\b",
]

DRIVER_CAR_PATTERNS = [
    r"\bdriver\b",
    r"\bcar\b",
    r"\bno\.\s*\d+\b",
    r"#\d{1,2}\b",
]

PRACTICE_PATTERNS = [
    r"\bpractice\b",
    r"\bpractice\s+\d+\b",
    r"\bpractice\s+session\b",
]

NO_TOW_PATTERNS = [
    r"\bno[-\s]?tow\b",
    r"\bwithout\s+(?:a\s+)?tow\b",
    r"\bclean\s+air\b",
    r"\bqualifying\s+simulation\b",
    r"\bqualifying\s+sim\b",
]

RESULT_TABLE_PATTERNS = [
    r"\bpos\b",
    r"\bposition\b",
    r"\brank\b",
    r"\blap\b",
    r"\bspeed\b",
    r"\bdriver\b",
]

NEGATIVE_META_PATTERNS = [
    r"\bmanifest\b",
    r"\bcandidate\b",
    r"\bdiscovered\s+source\b",
    r"\bmethodology\b",
    r"\bnext[_\s-]*phase\b",
]


verified_rows = []

for item in candidate_rows:

    path = item[
        "path"
    ]

    rel = item[
        "rel"
    ]

    text = safe_read(
        path
    )

    lower = text.lower()

    years = detect_years(
        text
    )

    fast_count = count_pattern(
        text,
        FAST_FRIDAY_PATTERNS
    )

    speed_count = count_pattern(
        text,
        SPEED_PATTERNS
    )

    has_driver_car = has_pattern(
        text,
        DRIVER_CAR_PATTERNS
    )

    has_practice = has_pattern(
        text,
        PRACTICE_PATTERNS
    )

    has_no_tow = has_pattern(
        text,
        NO_TOW_PATTERNS
    )

    result_structure_score = sum(
        1
        for pattern in RESULT_TABLE_PATTERNS
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )

    meta_score = sum(
        1
        for pattern in NEGATIVE_META_PATTERNS
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )


    contexts = extract_contexts(
        text,
        FAST_FRIDAY_PATTERNS,
    )


    # -------------------------------------------------------------------------
    # Semantic classification
    # -------------------------------------------------------------------------

    if (
        fast_count > 0
        and
        speed_count >= 3
        and
        has_driver_car
        and
        result_structure_score >= 3
    ):

        classification = (
            "LIKELY_NUMERIC_FAST_FRIDAY_EVIDENCE"
        )

        model_role = (
            "R4F6C_EXTRACTION_CANDIDATE"
        )


    elif (
        fast_count > 0
        and
        has_no_tow
        and
        speed_count > 0
    ):

        classification = (
            "LIKELY_NO_TOW_QUALIFYING_REFERENCE"
        )

        model_role = (
            "R4F6C_HIGH_PRIORITY_EXTRACTION"
        )


    elif (
        fast_count > 0
        and
        has_practice
        and
        speed_count > 0
    ):

        classification = (
            "FAST_FRIDAY_EDITORIAL_WITH_NUMERIC_CONTEXT"
        )

        model_role = (
            "MANUAL_OR_STRUCTURED_EXTRACTION_REVIEW"
        )


    elif (
        fast_count > 0
        and
        meta_score >= 2
        and
        speed_count == 0
    ):

        classification = (
            "META_REFERENCE_ONLY"
        )

        model_role = (
            "DO_NOT_USE_AS_PERFORMANCE_DATA"
        )


    elif fast_count > 0:

        classification = (
            "FAST_FRIDAY_MENTION_ONLY"
        )

        model_role = (
            "SOURCE_DISCOVERY_ONLY"
        )


    else:

        classification = (
            "KEYWORD_FALSE_POSITIVE"
        )

        model_role = (
            "EXCLUDE"
        )


    verified_rows.append({
        "file":
            rel,

        "years_detected":
            ";".join(
                str(y)
                for y in years
            ),

        "fast_friday_mentions":
            fast_count,

        "numeric_speed_hits":
            speed_count,

        "has_driver_or_car_context":
            has_driver_car,

        "has_practice_context":
            has_practice,

        "has_no_tow_or_qual_sim_context":
            has_no_tow,

        "result_structure_score":
            result_structure_score,

        "meta_reference_score":
            meta_score,

        "classification":
            classification,

        "model_role":
            model_role,

        "context_1":
            (
                contexts[0]
                if len(contexts) >= 1
                else ""
            ),

        "context_2":
            (
                contexts[1]
                if len(contexts) >= 2
                else ""
            ),

        "context_3":
            (
                contexts[2]
                if len(contexts) >= 3
                else ""
            ),
    })


# =============================================================================
# Year coverage
# =============================================================================

year_rows = []

for year in YEARS:

    relevant = [
        r
        for r in verified_rows
        if str(year)
        in
        r[
            "years_detected"
        ].split(";")
    ]

    likely_numeric = [
        r
        for r in relevant
        if r[
            "classification"
        ]
        in {
            "LIKELY_NUMERIC_FAST_FRIDAY_EVIDENCE",
            "LIKELY_NO_TOW_QUALIFYING_REFERENCE",
        }
    ]

    editorial_numeric = [
        r
        for r in relevant
        if r[
            "classification"
        ]
        ==
        "FAST_FRIDAY_EDITORIAL_WITH_NUMERIC_CONTEXT"
    ]

    mentions_only = [
        r
        for r in relevant
        if r[
            "classification"
        ]
        in {
            "FAST_FRIDAY_MENTION_ONLY",
            "META_REFERENCE_ONLY",
            "KEYWORD_FALSE_POSITIVE",
        }
    ]

    year_rows.append({
        "year":
            year,

        "candidate_files":
            len(
                relevant
            ),

        "likely_numeric_files":
            len(
                likely_numeric
            ),

        "editorial_numeric_files":
            len(
                editorial_numeric
            ),

        "mention_or_meta_only_files":
            len(
                mentions_only
            ),

        "local_reference_status":
            (
                "NUMERIC_CANDIDATE_PRESENT"
                if likely_numeric
                else
                "EDITORIAL_NUMERIC_ONLY"
                if editorial_numeric
                else
                "NO_USABLE_LOCAL_FAST_FRIDAY_NUMERIC_EVIDENCE"
            ),
    })


# =============================================================================
# Summary
# =============================================================================

classification_counts = Counter(
    r[
        "classification"
    ]
    for r in verified_rows
)

high_value = [
    r
    for r in verified_rows
    if r[
        "classification"
    ]
    in {
        "LIKELY_NUMERIC_FAST_FRIDAY_EVIDENCE",
        "LIKELY_NO_TOW_QUALIFYING_REFERENCE",
    }
]

editorial_value = [
    r
    for r in verified_rows
    if r[
        "classification"
    ]
    ==
    "FAST_FRIDAY_EDITORIAL_WITH_NUMERIC_CONTEXT"
]


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "semantic_candidates_inspected",

        "value":
            len(
                verified_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if verified_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "generated_r4_reports_excluded",

        "value":
            sum(
                1
                for r in verified_rows
                if r[
                    "file"
                ].startswith(
                    "r4/output/"
                )
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not r[
                        "file"
                    ].startswith(
                        "r4/output/"
                    )
                    for r in verified_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "classification_complete",

        "value":
            len(
                verified_rows
            ),

        "expected":
            len(
                candidate_rows
            ),

        "status":
            (
                "PASS"
                if len(
                    verified_rows
                )
                ==
                len(
                    candidate_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "likely_numeric_assets",

        "value":
            len(
                high_value
            ),

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },

    {
        "metric":
            "editorial_numeric_assets",

        "value":
            len(
                editorial_value
            ),

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_VERIFIED.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            verified_rows[0].keys()
        )
        if verified_rows
        else [
            "file",
            "classification",
            "model_role",
        ]
    )

    writer.writeheader()
    writer.writerows(
        verified_rows
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
        "R4F6B",

    "status":
        "R4F6B_PRESESSION_CANDIDATE_SEMANTIC_VERIFICATION_READY",

    "r4f6a_fast_friday_keyword_candidates":
        len(
            [
                r
                for r in audit
                if "FAST_FRIDAY"
                in clean(
                    r.get(
                        "categories"
                    )
                ).split(";")
            ]
        ),

    "semantic_candidates_after_generated_report_exclusion":
        len(
            verified_rows
        ),

    "likely_numeric_fast_friday_assets":
        len(
            high_value
        ),

    "editorial_numeric_assets":
        len(
            editorial_value
        ),

    "classification_counts":
        dict(
            classification_counts
        ),

    "methodological_rule":
        (
            "A file is not promoted to pre-session entry-reference "
            "evidence merely because it contains the words Fast Friday. "
            "Numeric speed, driver/car context and result-like structure "
            "must be present."
        ),

    "next_phase":
        (
            "If strong local numeric assets exist, extract a canonical "
            "Fast Friday reference panel. Otherwise perform targeted "
            "external acquisition for 2020-2024 Fast Friday results."
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
print("=" * 126)
print("SEMANTIC CLASSIFICATION SUMMARY")
print("=" * 126)

for classification in [
    "LIKELY_NO_TOW_QUALIFYING_REFERENCE",
    "LIKELY_NUMERIC_FAST_FRIDAY_EVIDENCE",
    "FAST_FRIDAY_EDITORIAL_WITH_NUMERIC_CONTEXT",
    "FAST_FRIDAY_MENTION_ONLY",
    "META_REFERENCE_ONLY",
    "KEYWORD_FALSE_POSITIVE",
]:

    print(
        f"{classification:48s} | "
        f"{classification_counts[classification]}"
    )


print()
print("=" * 126)
print("YEAR LOCAL FAST FRIDAY NUMERIC COVERAGE")
print("=" * 126)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"candidates={r['candidate_files']:2d} | "
        f"numeric={r['likely_numeric_files']:2d} | "
        f"editorial_numeric={r['editorial_numeric_files']:2d} | "
        f"mention/meta={r['mention_or_meta_only_files']:2d} | "
        f"{r['local_reference_status']}"
    )


print()
print("=" * 126)
print("VERIFIED HIGH-VALUE LOCAL CANDIDATES")
print("=" * 126)

if not high_value:

    print(
        "NONE"
    )

else:

    for i, r in enumerate(
        high_value,
        start=1
    ):

        print(
            f"{i:2d}. "
            f"{r['classification']} | "
            f"years={r['years_detected'] or '-'}"
        )

        print(
            f"    {r['file']}"
        )

        print(
            f"    fast_mentions="
            f"{r['fast_friday_mentions']} | "
            f"speed_hits="
            f"{r['numeric_speed_hits']} | "
            f"structure="
            f"{r['result_structure_score']} | "
            f"no_tow="
            f"{r['has_no_tow_or_qual_sim_context']}"
        )


print()
print("=" * 126)
print("EDITORIAL NUMERIC CANDIDATES")
print("=" * 126)

if not editorial_value:

    print(
        "NONE"
    )

else:

    for i, r in enumerate(
        editorial_value,
        start=1
    ):

        print(
            f"{i:2d}. "
            f"years={r['years_detected'] or '-'} | "
            f"{r['file']}"
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

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_VERIFIED.relative_to(ROOT)
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
    "R4F6B_PRESESSION_CANDIDATE_SEMANTIC_VERIFICATION_READY"
)
