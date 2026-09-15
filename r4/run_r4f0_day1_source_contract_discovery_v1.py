from pathlib import Path
import csv
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_CANDIDATES = (
    OUT /
    "r4f0_day1_source_candidates_v1.csv"
)

OUT_FIELDS = (
    OUT /
    "r4f0_day1_source_field_inventory_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f0_day1_source_discovery_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f0_day1_source_discovery_report_v1.json"
)


# =============================================================================
# Search concepts
#
# We deliberately use concept groups rather than requiring exact historical
# column names, because older R4 outputs were produced across several phases.
# =============================================================================

CONCEPTS = {
    "year": [
        r"^year$",
        r"season",
    ],

    "car": [
        r"car_number",
        r"carnumber",
        r"^car$",
        r"entry",
    ],

    "driver": [
        r"driver_name",
        r"driver",
    ],

    "current_result": [
        r"current.*result",
        r"current.*speed",
        r"best.*speed",
        r"reference.*speed",
        r"prior.*speed",
    ],

    "rank": [
        r"current.*rank",
        r"rank",
        r"position",
    ],

    "benchmark": [
        r"benchmark",
        r"advancement",
        r"cutoff",
        r"bubble",
        r"target_rank",
        r"target.*speed",
    ],

    "action": [
        r"action",
        r"decision",
        r"retain",
        r"withdraw",
        r"lane",
        r"requeue",
    ],

    "lane": [
        r"lane",
    ],

    "time": [
        r"time",
        r"timestamp",
        r"utc",
        r"elapsed",
        r"remaining",
    ],

    "time_quality": [
        r"time.*quality",
        r"time.*class",
        r"chronology",
        r"provenance",
    ],

    "session": [
        r"session",
        r"regime",
    ],
}


def normalize(name):
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def matches_any(field, patterns):
    f = normalize(
        field
    )

    for pattern in patterns:

        if re.search(
            pattern,
            f,
            flags=re.IGNORECASE
        ):
            return True

    return False


def inspect_csv(path):
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.reader(
                f
            )

            header = next(
                reader,
                []
            )

            row_count = 0

            for _ in reader:
                row_count += 1

    except Exception as exc:

        return {
            "error":
                repr(exc),

            "columns":
                [],

            "row_count":
                0,
        }

    return {
        "error":
            "",

        "columns":
            header,

        "row_count":
            row_count,
    }


candidate_rows = []
field_rows = []


# =============================================================================
# Scan only R4 output CSVs.
#
# Last Chance files are excluded from Day1-source ranking.
# =============================================================================

csv_paths = sorted(
    OUT.glob(
        "*.csv"
    )
)

for path in csv_paths:

    low_name = path.name.lower()

    if low_name.startswith(
        "r4lc"
    ):
        continue

    if low_name.startswith(
        "r4f0"
    ):
        continue

    info = inspect_csv(
        path
    )

    columns = info[
        "columns"
    ]

    concept_hits = {}

    for concept, patterns in CONCEPTS.items():

        hits = [
            c
            for c in columns
            if matches_any(
                c,
                patterns
            )
        ]

        concept_hits[
            concept
        ] = hits

        for field in hits:

            field_rows.append({
                "file":
                    path.name,

                "concept":
                    concept,

                "field":
                    field,
            })


    # =========================================================================
    # Scoring
    #
    # Highest weight goes to decision/action/current-state content.
    # Mere performance panels should therefore rank below decision-state files.
    # =========================================================================

    score = 0

    weights = {
        "year": 2,
        "car": 2,
        "driver": 1,
        "current_result": 5,
        "rank": 4,
        "benchmark": 5,
        "action": 7,
        "lane": 5,
        "time": 3,
        "time_quality": 3,
        "session": 2,
    }

    for concept, weight in weights.items():

        if concept_hits[
            concept
        ]:
            score += weight


    # Extra bonuses for likely canonical decision-state artifacts.
    name_bonus = 0

    for token, bonus in [
        ("decision", 7),
        ("state", 5),
        ("action", 6),
        ("observable", 4),
        ("chronology", 3),
        ("attempt", 2),
        ("r4a", 6),
    ]:

        if token in low_name:
            name_bonus += bonus

    score += name_bonus


    candidate_rows.append({
        "file":
            path.name,

        "rows":
            info[
                "row_count"
            ],

        "columns":
            len(
                columns
            ),

        "score":
            score,

        "name_bonus":
            name_bonus,

        "has_year":
            bool(
                concept_hits[
                    "year"
                ]
            ),

        "has_car":
            bool(
                concept_hits[
                    "car"
                ]
            ),

        "has_current_result":
            bool(
                concept_hits[
                    "current_result"
                ]
            ),

        "has_rank":
            bool(
                concept_hits[
                    "rank"
                ]
            ),

        "has_benchmark":
            bool(
                concept_hits[
                    "benchmark"
                ]
            ),

        "has_action":
            bool(
                concept_hits[
                    "action"
                ]
            ),

        "has_lane":
            bool(
                concept_hits[
                    "lane"
                ]
            ),

        "has_time":
            bool(
                concept_hits[
                    "time"
                ]
            ),

        "has_time_quality":
            bool(
                concept_hits[
                    "time_quality"
                ]
            ),

        "action_fields":
            ";".join(
                concept_hits[
                    "action"
                ]
            ),

        "current_result_fields":
            ";".join(
                concept_hits[
                    "current_result"
                ]
            ),

        "benchmark_fields":
            ";".join(
                concept_hits[
                    "benchmark"
                ]
            ),

        "rank_fields":
            ";".join(
                concept_hits[
                    "rank"
                ]
            ),

        "time_fields":
            ";".join(
                concept_hits[
                    "time"
                ]
            ),

        "error":
            info[
                "error"
            ],
    })


candidate_rows.sort(
    key=lambda r: (
        -int(
            r["score"]
        ),
        -int(
            r["rows"]
        ),
        r["file"],
    )
)


# =============================================================================
# Identify best contract candidates
# =============================================================================

strong_candidates = [
    r
    for r in candidate_rows
    if (
        r[
            "has_year"
        ]
        and
        r[
            "has_car"
        ]
        and
        (
            r[
                "has_action"
            ]
            or
            r[
                "has_lane"
            ]
        )
        and
        (
            r[
                "has_current_result"
            ]
            or
            r[
                "has_rank"
            ]
            or
            r[
                "has_benchmark"
            ]
        )
    )
]


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "non_last_chance_csvs_scanned",

        "value":
            len(
                candidate_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if candidate_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "strong_day1_source_candidate_found",

        "value":
            len(
                strong_candidates
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if strong_candidates
                else "WARN"
            ),
    },

    {
        "metric":
            "last_chance_files_excluded",

        "value":
            sum(
                1
                for r in candidate_rows
                if r[
                    "file"
                ].lower().startswith(
                    "r4lc"
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
                    ].lower().startswith(
                        "r4lc"
                    )
                    for r in candidate_rows
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_CANDIDATES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        candidate_rows[0].keys()
    ) if candidate_rows else [
        "file",
        "rows",
        "columns",
        "score",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        candidate_rows
    )


with OUT_FIELDS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "file",
        "concept",
        "field",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        field_rows
    )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "metric",
        "value",
        "expected",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F0",

    "status":
        "R4F0_DAY1_SOURCE_CONTRACT_DISCOVERY_READY",

    "csv_files_scanned":
        len(
            candidate_rows
        ),

    "strong_candidate_count":
        len(
            strong_candidates
        ),

    "top_candidates": [
        {
            "file":
                r[
                    "file"
                ],

            "score":
                r[
                    "score"
                ],

            "rows":
                r[
                    "rows"
                ],

            "action_fields":
                r[
                    "action_fields"
                ],

            "current_result_fields":
                r[
                    "current_result_fields"
                ],

            "benchmark_fields":
                r[
                    "benchmark_fields"
                ],
        }
        for r in candidate_rows[
            :10
        ]
    ],

    "next_phase":
        (
            "Select the highest-quality existing Day1 decision-state "
            "source and map it into the frozen Fused V2 action schema."
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

print("=" * 120)
print("R4F0 — DAY1 SOURCE CONTRACT DISCOVERY")
print("=" * 120)

print()
print(
    f"CSV files scanned: "
    f"{len(candidate_rows)}"
)

print(
    f"Strong Day1 candidates: "
    f"{len(strong_candidates)}"
)


print()
print("=" * 120)
print("TOP DAY1 SOURCE CANDIDATES")
print("=" * 120)

for rank, r in enumerate(
    candidate_rows[:20],
    start=1
):

    print(
        f"{rank:2d}. "
        f"score={r['score']:2d} | "
        f"rows={r['rows']:4d} | "
        f"{r['file']}"
    )

    print(
        f"    action="
        f"{r['action_fields'] or '-'}"
    )

    print(
        f"    current="
        f"{r['current_result_fields'] or '-'}"
    )

    print(
        f"    benchmark="
        f"{r['benchmark_fields'] or '-'}"
    )

    print(
        f"    rank="
        f"{r['rank_fields'] or '-'}"
    )

    print(
        f"    time="
        f"{r['time_fields'] or '-'}"
    )


print()
print("=" * 120)
print("STRONG CONTRACT CANDIDATES")
print("=" * 120)

if not strong_candidates:

    print(
        "NONE — Day1 contract may require joining multiple existing R4 files."
    )

else:

    for r in strong_candidates[:15]:

        print(
            f"score={r['score']:2d} | "
            f"rows={r['rows']:4d} | "
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
    OUT_CANDIDATES.relative_to(ROOT)
)
print(
    OUT_FIELDS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F0_DAY1_SOURCE_CONTRACT_DISCOVERY_READY"
)
