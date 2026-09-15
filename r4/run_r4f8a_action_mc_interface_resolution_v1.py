from pathlib import Path
import csv
import json
import re
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

REQUIRED_FILES = [
    OUT / "r4f2_canonical_fused_decision_dataset_v2.csv",
    OUT / "r4f7c7_final_performance_architecture_contract_v1.json",
    OUT / "r4f7v2_external_validation_conclusion_v1.json",
]

OUT_CANDIDATES = (
    OUT /
    "r4f8a_action_mc_candidate_files_v1.csv"
)

OUT_SCHEMA = (
    OUT /
    "r4f8a_action_mc_schema_resolution_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f8a_action_mc_interface_resolution_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f8a_action_mc_interface_resolution_report_v1.json"
)


KEYWORDS = [
    "action",
    "queue",
    "wait",
    "monte",
    "simulation",
    "simulate",
    "decision",
    "benchmark",
    "rank",
    "withdraw",
    "lane",
    "reattempt",
    "completion",
    "remaining",
    "session",
]


TARGET_SEMANTICS = {
    "ACTION": [
        "action",
        "feasible_action",
        "observed_action",
    ],

    "CURRENT_RESULT": [
        "current_result",
        "current_speed",
        "protected_speed",
        "best_speed",
        "current_best",
    ],

    "BENCHMARK": [
        "benchmark",
        "cutoff",
        "bubble",
        "advancement",
    ],

    "RANK": [
        "rank",
        "position",
        "place",
    ],

    "QUEUE": [
        "queue",
        "lane",
        "wait",
        "requeue",
    ],

    "TIME": [
        "decision_time",
        "remaining",
        "elapsed",
        "session_time",
        "timestamp",
        "_utc",
    ],

    "PROBABILITY": [
        "prob",
        "probability",
        "p_",
    ],

    "MONTE_CARLO": [
        "simulation",
        "monte",
        "draw",
        "sample",
        "scenario",
    ],

    "COMPLETION": [
        "complete",
        "completion",
        "finish",
    ],

    "IDENTITY": [
        "attempt_id",
        "decision_id",
        "driver",
        "car_number",
        "year",
        "session",
    ],
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def norm(v):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(v).lower()
    ).strip("_")


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def classify_column(col):
    c = norm(col)

    classes = []

    for semantic, tokens in (
        TARGET_SEMANTICS.items()
    ):

        if any(
            token in c
            for token in tokens
        ):
            classes.append(
                semantic
            )

    return classes


for path in REQUIRED_FILES:

    if not path.exists():

        raise SystemExit(
            f"MISSING REQUIRED INPUT: {path}"
        )


# =============================================================================
# Scan action / queue / MC candidate CSVs
# =============================================================================

candidate_rows = []
schema_rows = []


for path in sorted(
    OUT.glob("*.csv")
):

    name = norm(
        path.name
    )

    if not any(
        keyword in name
        for keyword in KEYWORDS
    ):
        continue


    try:

        fields, rows = read_csv(
            path
        )

    except Exception:

        continue


    if not fields:
        continue


    semantic_counts = {
        k: 0
        for k in TARGET_SEMANTICS
    }


    for col in fields:

        classes = classify_column(
            col
        )

        for cls in classes:

            semantic_counts[
                cls
            ] += 1


        if classes:

            schema_rows.append({
                "file":
                    str(
                        path.relative_to(
                            ROOT
                        )
                    ),

                "column":
                    col,

                "semantic_classes":
                    ";".join(
                        classes
                    ),

                "rows":
                    len(rows),
            })


    score = (
        semantic_counts[
            "ACTION"
        ] * 6
        +
        semantic_counts[
            "QUEUE"
        ] * 5
        +
        semantic_counts[
            "BENCHMARK"
        ] * 4
        +
        semantic_counts[
            "CURRENT_RESULT"
        ] * 4
        +
        semantic_counts[
            "TIME"
        ] * 3
        +
        semantic_counts[
            "RANK"
        ] * 3
        +
        semantic_counts[
            "PROBABILITY"
        ] * 3
        +
        semantic_counts[
            "MONTE_CARLO"
        ] * 3
        +
        semantic_counts[
            "COMPLETION"
        ] * 2
    )


    candidate_rows.append({
        "file":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "rows":
            len(rows),

        "columns":
            len(fields),

        "score":
            score,

        **{
            f"{k.lower()}_columns":
                semantic_counts[k]
            for k in semantic_counts
        },

        "all_columns":
            ";".join(
                fields
            ),
    })


candidate_rows.sort(
    key=lambda r: (
        -r[
            "score"
        ],
        -r[
            "rows"
        ],
        r[
            "file"
        ],
    )
)


# =============================================================================
# Explicit frozen F2 inspection
# =============================================================================

f2_path = (
    OUT /
    "r4f2_canonical_fused_decision_dataset_v2.csv"
)

f2_fields, f2_rows = read_csv(
    f2_path
)


f2_semantics = {
    key: []
    for key in TARGET_SEMANTICS
}


for col in f2_fields:

    for cls in classify_column(
        col
    ):

        f2_semantics[
            cls
        ].append(
            col
        )


# =============================================================================
# Search likely queue / P11 artifacts
# =============================================================================

queue_candidates = [
    r
    for r in candidate_rows
    if (
        r[
            "queue_columns"
        ] > 0
        or
        r[
            "monte_carlo_columns"
        ] > 0
        or
        "p11" in norm(
            r[
                "file"
            ]
        )
        or
        "wait" in norm(
            r[
                "file"
            ]
        )
    )
]


action_candidates = [
    r
    for r in candidate_rows
    if r[
        "action_columns"
    ] > 0
]


# =============================================================================
# Check frozen contracts
# =============================================================================

performance_contract = json.loads(
    (
        OUT /
        "r4f7c7_final_performance_architecture_contract_v1.json"
    ).read_text(
        encoding="utf-8"
    )
)

validation_contract = json.loads(
    (
        OUT /
        "r4f7v2_external_validation_conclusion_v1.json"
    ).read_text(
        encoding="utf-8"
    )
)


performance_frozen = (
    performance_contract.get(
        "status"
    )
    ==
    "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
)


validation_frozen = (
    validation_contract.get(
        "status"
    )
    ==
    "R4F7V2_EXTERNAL_VALIDATION_CONCLUSION_FROZEN"
)


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "f2_rows",
        "value":
            len(
                f2_rows
            ),
        "expected":
            148,
        "status":
            (
                "PASS"
                if len(
                    f2_rows
                ) == 148
                else "WARN"
            ),
    },

    {
        "metric":
            "f2_action_semantics_found",
        "value":
            len(
                f2_semantics[
                    "ACTION"
                ]
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if f2_semantics[
                    "ACTION"
                ]
                else "WARN"
            ),
    },

    {
        "metric":
            "f2_benchmark_semantics_found",
        "value":
            len(
                f2_semantics[
                    "BENCHMARK"
                ]
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if f2_semantics[
                    "BENCHMARK"
                ]
                else "WARN"
            ),
    },

    {
        "metric":
            "queue_or_mc_candidate_found",
        "value":
            len(
                queue_candidates
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if queue_candidates
                else "WARN"
            ),
    },

    {
        "metric":
            "performance_contract_frozen",
        "value":
            performance_frozen,
        "expected":
            True,
        "status":
            (
                "PASS"
                if performance_frozen
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_conclusion_frozen",
        "value":
            validation_frozen,
        "expected":
            True,
        "status":
            (
                "PASS"
                if validation_frozen
                else "FAIL"
            ),
    },

    {
        "metric":
            "integration_resolution_only_no_simulation",
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

if candidate_rows:

    with OUT_CANDIDATES.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                candidate_rows[
                    0
                ].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            candidate_rows
        )


if schema_rows:

    with OUT_SCHEMA.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                schema_rows[
                    0
                ].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            schema_rows
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
        "R4F8A",

    "status":
        "R4F8A_ACTION_MC_INTERFACE_RESOLUTION_READY",

    "f2_rows":
        len(
            f2_rows
        ),

    "f2_columns":
        f2_fields,

    "f2_semantics":
        f2_semantics,

    "top_action_candidates":
        action_candidates[
            :20
        ],

    "top_queue_mc_candidates":
        queue_candidates[
            :30
        ],

    "performance_contract_frozen":
        performance_frozen,

    "external_validation_conclusion_frozen":
        validation_frozen,

    "next_phase":
        (
            "R4F8B constructs the unified simulation-state interface "
            "for Day1 and Last Chance using resolved existing artifacts."
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

print("=" * 152)
print("R4F8A — ACTION / MONTE CARLO INTERFACE RESOLUTION")
print("=" * 152)


print()
print("=" * 152)
print("F2 FROZEN DECISION DATASET")
print("=" * 152)

print(
    f"rows={len(f2_rows)}"
)

print(
    f"columns={len(f2_fields)}"
)

for semantic in [
    "IDENTITY",
    "ACTION",
    "CURRENT_RESULT",
    "BENCHMARK",
    "RANK",
    "QUEUE",
    "TIME",
    "COMPLETION",
]:

    print(
        f"{semantic:18s} | "
        +
        ";".join(
            f2_semantics[
                semantic
            ]
        )
    )


print()
print("=" * 152)
print("TOP ACTION INTERFACE CANDIDATES")
print("=" * 152)

for r in action_candidates[:20]:

    print(
        f"{r['file'][:82]:82s} | "
        f"rows={r['rows']:4d} | "
        f"score={r['score']:3d} | "
        f"action={r['action_columns']} | "
        f"benchmark={r['benchmark_columns']} | "
        f"time={r['time_columns']}"
    )


print()
print("=" * 152)
print("TOP QUEUE / WAIT / MC CANDIDATES")
print("=" * 152)

for r in queue_candidates[:30]:

    print(
        f"{r['file'][:82]:82s} | "
        f"rows={r['rows']:4d} | "
        f"score={r['score']:3d} | "
        f"queue={r['queue_columns']} | "
        f"mc={r['monte_carlo_columns']} | "
        f"prob={r['probability_columns']} | "
        f"time={r['time_columns']}"
    )


print()
print("=" * 152)
print("TOP QUEUE / MC SCHEMAS")
print("=" * 152)

top_files = {
    r[
        "file"
    ]
    for r in queue_candidates[
        :10
    ]
}


for file in sorted(
    top_files
):

    print()
    print(
        f"FILE: {file}"
    )

    relevant = [
        r
        for r in schema_rows
        if r[
            "file"
        ] == file
    ]

    for r in relevant:

        print(
            f"  {r['column']:48s} | "
            f"{r['semantic_classes']}"
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
    OUT_CANDIDATES.relative_to(
        ROOT
    )
)

print(
    OUT_SCHEMA.relative_to(
        ROOT
    )
)

print(
    OUT_QA.relative_to(
        ROOT
    )
)

print(
    OUT_REPORT.relative_to(
        ROOT
    )
)

print()
print(
    "R4F8A_ACTION_MC_INTERFACE_RESOLUTION_READY"
)
