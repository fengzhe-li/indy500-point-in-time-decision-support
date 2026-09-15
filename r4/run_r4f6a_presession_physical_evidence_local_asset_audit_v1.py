from pathlib import Path
from collections import Counter
import csv
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_FILES = (
    OUT /
    "r4f6a_presession_physical_local_assets_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f6a_presession_physical_local_asset_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6a_presession_physical_local_asset_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6a_presession_physical_local_asset_report_v1.json"
)


YEARS = [
    2018,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
    2026,
]

TEXT_EXTENSIONS = {
    ".csv",
    ".json",
    ".txt",
    ".md",
    ".html",
    ".htm",
}

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}


CATEGORY_PATTERNS = {
    "FAST_FRIDAY": [
        r"fast[\s_-]*friday",
        r"fastfriday",
        r"friday.*qual",
    ],

    "QUAL_SIM_NO_TOW": [
        r"qual(?:ifying)?[\s_-]*sim",
        r"qualification[\s_-]*sim",
        r"no[\s_-]*tow",
        r"without[\s_-]*tow",
        r"clean[\s_-]*air",
        r"qualifying[\s_-]*simulation",
    ],

    "PRACTICE_GENERAL": [
        r"practice",
        r"practice[\s_-]*session",
        r"indy[\s_-]*500.*practice",
    ],

    "INDY_RACE": [
        r"indy[\s_-]*500.*race",
        r"race[\s_-]*stint",
        r"indy.*stint",
        r"race[\s_-]*lap",
    ],

    "OTHER_OVAL": [
        r"oval",
        r"texas",
        r"iowa",
        r"gateway",
        r"wwtr",
        r"milwaukee",
        r"nashville.*superspeedway",
    ],

    "TIRE_THERMAL": [
        r"tire",
        r"tyre",
        r"firestone",
        r"thermal",
        r"track[\s_-]*temp",
        r"temperature",
        r"degradation",
        r"stint",
        r"pressure",
    ],

    "QUALIFYING_OFFICIAL": [
        r"qualifying",
        r"qualification",
        r"quals",
        r"pole",
    ],
}


ROLE_MAP = {
    "FAST_FRIDAY":
        "PRESESSION_ENTRY_REFERENCE_HIGH",

    "QUAL_SIM_NO_TOW":
        "PRESESSION_ENTRY_REFERENCE_HIGH",

    "PRACTICE_GENERAL":
        "PRESESSION_REFERENCE_LOW_UNLESS_CONTEXT_CLEAN",

    "INDY_RACE":
        "TIRE_THERMAL_PHYSICAL_PRIOR_ONLY",

    "OTHER_OVAL":
        "WEAK_TRANSFER_TIRE_TEAM_PHYSICAL_PRIOR",

    "TIRE_THERMAL":
        "PHYSICAL_LAYER_SUPPORT",

    "QUALIFYING_OFFICIAL":
        "QUALIFYING_PERFORMANCE_CONTEXT",
}


def should_skip(path):
    return any(
        part in SKIP_DIRS
        for part in path.parts
    )


def normalize_text(value):
    return (
        str(value)
        .lower()
        .replace("\\", "/")
    )


def detect_years(text):
    found = []

    for year in YEARS:

        if str(year) in text:
            found.append(
                year
            )

    return found


def detect_categories(text):
    hits = []

    for category, patterns in CATEGORY_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):

                hits.append(
                    category
                )
                break

    return hits


def safe_read_preview(path, max_chars=12000):
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""

    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )[:max_chars]

    except Exception:
        return ""


def inspect_csv_header(path):
    if path.suffix.lower() != ".csv":
        return []

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            reader = csv.reader(
                f
            )

            return next(
                reader,
                [],
            )

    except Exception:
        return []


def relevance_score(
    categories,
    years,
    filename_hit,
    content_hit,
    header_hit,
):
    score = 0

    weights = {
        "FAST_FRIDAY": 20,
        "QUAL_SIM_NO_TOW": 20,
        "INDY_RACE": 10,
        "OTHER_OVAL": 7,
        "TIRE_THERMAL": 7,
        "QUALIFYING_OFFICIAL": 6,
        "PRACTICE_GENERAL": 4,
    }

    for category in categories:

        score += weights.get(
            category,
            0,
        )

    if years:
        score += 3

    if filename_hit:
        score += 5

    if content_hit:
        score += 3

    if header_hit:
        score += 4

    return score


rows = []

for path in ROOT.rglob("*"):

    if not path.is_file():
        continue

    if should_skip(
        path
    ):
        continue

    if path.name.startswith(
        "r4f6a_"
    ):
        continue

    rel = path.relative_to(
        ROOT
    )

    filename_text = normalize_text(
        str(rel)
    )

    preview = safe_read_preview(
        path
    )

    content_text = normalize_text(
        preview
    )

    header = inspect_csv_header(
        path
    )

    header_text = normalize_text(
        " ".join(
            header
        )
    )

    filename_categories = detect_categories(
        filename_text
    )

    content_categories = detect_categories(
        content_text
    )

    header_categories = detect_categories(
        header_text
    )

    categories = sorted(
        set(
            filename_categories
            +
            content_categories
            +
            header_categories
        )
    )

    if not categories:
        continue

    years = sorted(
        set(
            detect_years(
                filename_text
            )
            +
            detect_years(
                content_text
            )
        )
    )

    filename_hit = bool(
        filename_categories
    )

    content_hit = bool(
        content_categories
    )

    header_hit = bool(
        header_categories
    )

    roles = sorted(
        {
            ROLE_MAP[
                category
            ]
            for category in categories
            if category in ROLE_MAP
        }
    )

    score = relevance_score(
        categories,
        years,
        filename_hit,
        content_hit,
        header_hit,
    )

    if (
        "FAST_FRIDAY"
        in categories
        or
        "QUAL_SIM_NO_TOW"
        in categories
    ):

        priority = (
            "HIGH"
        )

    elif (
        "INDY_RACE"
        in categories
        or
        "TIRE_THERMAL"
        in categories
        or
        "QUALIFYING_OFFICIAL"
        in categories
    ):

        priority = (
            "MEDIUM"
        )

    else:

        priority = (
            "LOW"
        )


    rows.append({
        "file":
            str(
                rel
            ),

        "extension":
            path.suffix.lower(),

        "size_bytes":
            path.stat().st_size,

        "years":
            ";".join(
                str(year)
                for year in years
            ),

        "categories":
            ";".join(
                categories
            ),

        "intended_roles":
            ";".join(
                roles
            ),

        "filename_hit":
            filename_hit,

        "content_hit":
            content_hit,

        "header_hit":
            header_hit,

        "relevance_score":
            score,

        "csv_fields_sample":
            ";".join(
                header[:40]
            ),

        "priority":
            priority,
    })


rows.sort(
    key=lambda r: (
        0
        if r[
            "priority"
        ] == "HIGH"
        else
        1
        if r[
            "priority"
        ] == "MEDIUM"
        else
        2,
        -int(
            r[
                "relevance_score"
            ]
        ),
        r[
            "file"
        ],
    )
)


summary_rows = []

for category in CATEGORY_PATTERNS:

    subset = []

    for r in rows:

        clean_categories = (
            r[
                "categories"
            ].split(";")
        )

        if category in clean_categories:

            subset.append(
                r
            )


    year_counter = Counter()

    for r in subset:

        year_values = [
            y.strip()
            for y in r[
                "years"
            ].split(";")
            if y.strip()
        ]

        for year_text in year_values:

            try:
                year = int(
                    year_text
                )

            except Exception:
                continue

            year_counter[
                year
            ] += 1


    summary_rows.append({
        "category":
            category,

        "files":
            len(
                subset
            ),

        "years":
            ";".join(
                str(year)
                for year in sorted(
                    year_counter
                )
            ),

        "year_file_counts":
            ";".join(
                f"{year}:{year_counter[year]}"
                for year in sorted(
                    year_counter
                )
            ),

        "high_priority_files":
            sum(
                r[
                    "priority"
                ] == "HIGH"
                for r in subset
            ),

        "medium_priority_files":
            sum(
                r[
                    "priority"
                ] == "MEDIUM"
                for r in subset
            ),

        "low_priority_files":
            sum(
                r[
                    "priority"
                ] == "LOW"
                for r in subset
            ),

        "intended_role":
            ROLE_MAP.get(
                category,
                "",
            ),
    })


presession_candidates = [
    r
    for r in rows
    if (
        "FAST_FRIDAY"
        in r[
            "categories"
        ].split(";")
        or
        "QUAL_SIM_NO_TOW"
        in r[
            "categories"
        ].split(";")
    )
]


race_physical_candidates = [
    r
    for r in rows
    if (
        "INDY_RACE"
        in r[
            "categories"
        ].split(";")
        or
        "OTHER_OVAL"
        in r[
            "categories"
        ].split(";")
        or
        "TIRE_THERMAL"
        in r[
            "categories"
        ].split(";")
    )
]


year_matrix = {}

for year in YEARS:

    year_matrix[
        year
    ] = {
        "FAST_FRIDAY":
            0,

        "QUAL_SIM_NO_TOW":
            0,

        "PRACTICE_GENERAL":
            0,

        "INDY_RACE":
            0,

        "OTHER_OVAL":
            0,

        "TIRE_THERMAL":
            0,

        "QUALIFYING_OFFICIAL":
            0,
    }


for r in rows:

    row_years = []

    for y in r[
        "years"
    ].split(";"):

        y = y.strip()

        if not y:
            continue

        try:
            row_years.append(
                int(
                    y
                )
            )

        except Exception:
            continue


    categories = r[
        "categories"
    ].split(";")


    for year in row_years:

        if year not in year_matrix:
            continue

        for category in categories:

            if category in year_matrix[
                year
            ]:

                year_matrix[
                    year
                ][
                    category
                ] += 1


qa_rows = [
    {
        "metric":
            "relevant_local_assets_found",

        "value":
            len(
                rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if rows
                else "WARN"
            ),
    },

    {
        "metric":
            "high_value_presession_candidates",

        "value":
            len(
                presession_candidates
            ),

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },

    {
        "metric":
            "race_or_physical_candidates",

        "value":
            len(
                race_physical_candidates
            ),

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },

    {
        "metric":
            "audit_only_no_model_mutation",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "practice_not_promoted_to_high_value_by_default",

        "value":
            sum(
                1
                for r in rows
                if (
                    "PRACTICE_GENERAL"
                    in r[
                        "categories"
                    ].split(";")
                    and
                    "FAST_FRIDAY"
                    not in r[
                        "categories"
                    ].split(";")
                    and
                    "QUAL_SIM_NO_TOW"
                    not in r[
                        "categories"
                    ].split(";")
                    and
                    r[
                        "priority"
                    ] == "HIGH"
                )
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not (
                        "PRACTICE_GENERAL"
                        in r[
                            "categories"
                        ].split(";")
                        and
                        "FAST_FRIDAY"
                        not in r[
                            "categories"
                        ].split(";")
                        and
                        "QUAL_SIM_NO_TOW"
                        not in r[
                            "categories"
                        ].split(";")
                        and
                        r[
                            "priority"
                        ] == "HIGH"
                    )
                    for r in rows
                )
                else "FAIL"
            ),
    },
]


with OUT_FILES.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    fields = (
        list(
            rows[0].keys()
        )
        if rows
        else [
            "file",
            "categories",
            "priority",
        ]
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(
        rows
    )


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
    )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F6A",

    "status":
        "R4F6A_PRESESSION_PHYSICAL_LOCAL_ASSET_AUDIT_READY",

    "relevant_assets":
        len(
            rows
        ),

    "high_value_presession_candidates":
        len(
            presession_candidates
        ),

    "race_or_physical_candidates":
        len(
            race_physical_candidates
        ),

    "evidence_policy": {
        "fast_friday":
            (
                "Primary candidate for pre-session "
                "entry performance reference."
            ),

        "qual_sim_no_tow":
            (
                "Primary candidate for clean "
                "qualifying-like reference."
            ),

        "general_practice":
            (
                "Low-value unless run programme / "
                "tow context is known."
            ),

        "indy_race":
            (
                "Tire / thermal / degradation "
                "physical evidence only."
            ),

        "other_oval":
            (
                "Weak-transfer physical/team/tire prior; "
                "not direct Indy qualifying pace."
            ),
    },

    "next_phase":
        (
            "Inspect high-value local Fast Friday / no-tow "
            "assets. If local evidence is insufficient, "
            "perform targeted external data acquisition."
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


print("=" * 128)
print("R4F6A — PRE-SESSION / PHYSICAL EVIDENCE LOCAL ASSET AUDIT")
print("=" * 128)

print()
print(
    f"Relevant assets found: "
    f"{len(rows)}"
)

print(
    f"High-value pre-session candidates: "
    f"{len(presession_candidates)}"
)

print(
    f"Race / physical candidates: "
    f"{len(race_physical_candidates)}"
)


print()
print("=" * 128)
print("CATEGORY SUMMARY")
print("=" * 128)

for r in summary_rows:

    print(
        f"{r['category']:22s} | "
        f"files={r['files']:3d} | "
        f"years={r['years'] or '-':25s} | "
        f"role={r['intended_role']}"
    )


print()
print("=" * 128)
print("YEAR EVIDENCE MATRIX")
print("=" * 128)

for year in YEARS:

    m = year_matrix[
        year
    ]

    print(
        f"{year} | "
        f"FastFriday={m['FAST_FRIDAY']:2d} | "
        f"QualSimNoTow={m['QUAL_SIM_NO_TOW']:2d} | "
        f"Practice={m['PRACTICE_GENERAL']:2d} | "
        f"IndyRace={m['INDY_RACE']:2d} | "
        f"OtherOval={m['OTHER_OVAL']:2d} | "
        f"TireThermal={m['TIRE_THERMAL']:2d} | "
        f"QualOfficial={m['QUALIFYING_OFFICIAL']:2d}"
    )


print()
print("=" * 128)
print("TOP HIGH-VALUE PRESESSION CANDIDATES")
print("=" * 128)

if not presession_candidates:

    print(
        "NONE FOUND LOCALLY"
    )

else:

    for i, r in enumerate(
        presession_candidates[:30],
        start=1,
    ):

        print(
            f"{i:2d}. "
            f"score={r['relevance_score']:3d} | "
            f"years={r['years'] or '-':20s} | "
            f"{r['file']}"
        )

        print(
            f"    categories="
            f"{r['categories']}"
        )


print()
print("=" * 128)
print("TOP RACE / TIRE / OVAL PHYSICAL CANDIDATES")
print("=" * 128)

if not race_physical_candidates:

    print(
        "NONE FOUND LOCALLY"
    )

else:

    for i, r in enumerate(
        race_physical_candidates[:30],
        start=1,
    ):

        print(
            f"{i:2d}. "
            f"priority={r['priority']:6s} | "
            f"score={r['relevance_score']:3d} | "
            f"years={r['years'] or '-':20s} | "
            f"{r['file']}"
        )

        print(
            f"    categories="
            f"{r['categories']}"
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
    OUT_FILES.relative_to(ROOT)
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
    "R4F6A_PRESESSION_PHYSICAL_LOCAL_ASSET_AUDIT_READY"
)
