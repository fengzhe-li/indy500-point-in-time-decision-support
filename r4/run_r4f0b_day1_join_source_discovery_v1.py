from pathlib import Path
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
    "r4f0b_day1_join_source_candidates_v1.csv"
)

OUT_FIELDS = (
    OUT /
    "r4f0b_day1_join_field_inventory_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f0b_day1_join_source_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f0b_day1_join_source_report_v1.json"
)


SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

NAME_HINTS = [
    "decision",
    "state",
    "action",
    "chronology",
    "lane",
    "target",
    "benchmark",
    "attempt",
    "leaderboard",
]

FIELD_GROUPS = {
    "year": [
        "year",
    ],

    "attempt_id": [
        "attempt_id",
        "decision_attempt_id",
    ],

    "car": [
        "car_number",
        "car",
        "entry_number",
    ],

    "driver": [
        "driver_name",
        "driver",
    ],

    "current_result": [
        "current_result",
        "current_result_mph",
        "current_speed_mph",
        "current_four_lap_average_speed_mph",
        "current_best_speed_mph",
        "prior_speed_mph",
    ],

    "current_rank": [
        "current_rank",
        "current_position",
        "leaderboard_rank",
        "rank_before",
    ],

    "benchmark": [
        "advancement_benchmark",
        "benchmark_speed_mph",
        "benchmark_rank",
        "bubble_speed_mph",
        "cutoff_speed_mph",
        "target_rank",
    ],

    "lane": [
        "lane_action",
        "lane",
        "lane_choice",
        "queue_lane",
    ],

    "action": [
        "strategy_action",
        "observed_action",
        "action",
        "decision_action",
        "withdraw_action",
        "requeue_action",
    ],

    "time": [
        "decision_time_utc",
        "event_time_point_utc",
        "time_point_utc",
        "performance_time_utc",
        "canonical_start_time_utc",
        "canonical_end_time_utc",
    ],

    "time_quality": [
        "time_quality",
        "time_evidence_class",
        "canonical_event_time_quality",
        "chronology_quality",
    ],

    "session": [
        "session",
        "session_name",
        "session_regime",
    ],
}


def should_skip(path):
    return any(
        part in SKIP_DIRS
        for part in path.parts
    )


def normalize(v):
    return (
        str(v)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def inspect_csv(path):
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            fields = (
                reader.fieldnames
                or []
            )

            rows = []

            for i, row in enumerate(reader):

                if i < 3:
                    rows.append(row)

            # Count separately without loading whole file.
            count = i + 1 if 'i' in locals() else 0

        return {
            "fields":
                fields,

            "sample_rows":
                rows,

            "row_count":
                count,

            "error":
                "",
        }

    except Exception as exc:

        return {
            "fields":
                [],

            "sample_rows":
                [],

            "row_count":
                0,

            "error":
                repr(exc),
        }


def field_hits(fields, candidates):
    normalized = {
        normalize(f):
            f
        for f in fields
    }

    hits = []

    for candidate in candidates:

        c = normalize(candidate)

        if c in normalized:
            hits.append(
                normalized[c]
            )

    return hits


candidate_rows = []
field_rows = []


# =============================================================================
# Scan entire active project for CSV files likely relevant to Day1 decision state
# =============================================================================

for path in ROOT.rglob("*.csv"):

    if should_skip(path):
        continue

    rel = path.relative_to(ROOT)

    low_name = str(
        rel
    ).lower()

    if "r4lc" in low_name:
        continue

    if "r4f0" in low_name:
        continue

    info = inspect_csv(
        path
    )

    if info["error"]:
        continue

    fields = info[
        "fields"
    ]

    exact_hits = {}

    for group, candidates in FIELD_GROUPS.items():

        hits = field_hits(
            fields,
            candidates
        )

        exact_hits[
            group
        ] = hits

        for hit in hits:

            field_rows.append({
                "file":
                    str(rel),

                "group":
                    group,

                "field":
                    hit,
            })


    name_score = sum(
        1
        for hint in NAME_HINTS
        if hint in low_name
    )

    schema_score = 0

    weights = {
        "year": 2,
        "attempt_id": 6,
        "car": 3,
        "driver": 1,
        "current_result": 7,
        "current_rank": 6,
        "benchmark": 7,
        "lane": 7,
        "action": 8,
        "time": 4,
        "time_quality": 3,
        "session": 2,
    }

    for group, weight in weights.items():

        if exact_hits[
            group
        ]:
            schema_score += weight

    total_score = (
        schema_score
        + name_score
    )


    # Only keep files with meaningful Day1 decision relevance.
    meaningful = (
        name_score > 0
        or
        exact_hits["lane"]
        or
        exact_hits["action"]
        or
        exact_hits["current_result"]
        or
        exact_hits["current_rank"]
        or
        exact_hits["benchmark"]
    )

    if not meaningful:
        continue


    candidate_rows.append({
        "file":
            str(rel),

        "rows":
            info[
                "row_count"
            ],

        "columns":
            len(
                fields
            ),

        "score":
            total_score,

        "name_score":
            name_score,

        "attempt_id_fields":
            ";".join(
                exact_hits[
                    "attempt_id"
                ]
            ),

        "car_fields":
            ";".join(
                exact_hits[
                    "car"
                ]
            ),

        "current_result_fields":
            ";".join(
                exact_hits[
                    "current_result"
                ]
            ),

        "current_rank_fields":
            ";".join(
                exact_hits[
                    "current_rank"
                ]
            ),

        "benchmark_fields":
            ";".join(
                exact_hits[
                    "benchmark"
                ]
            ),

        "lane_fields":
            ";".join(
                exact_hits[
                    "lane"
                ]
            ),

        "action_fields":
            ";".join(
                exact_hits[
                    "action"
                ]
            ),

        "time_fields":
            ";".join(
                exact_hits[
                    "time"
                ]
            ),

        "time_quality_fields":
            ";".join(
                exact_hits[
                    "time_quality"
                ]
            ),

        "join_key_strength":
            (
                "HIGH"
                if (
                    exact_hits[
                        "attempt_id"
                    ]
                    and
                    exact_hits[
                        "year"
                    ]
                )
                else
                "MEDIUM"
                if (
                    exact_hits[
                        "year"
                    ]
                    and
                    exact_hits[
                        "car"
                    ]
                )
                else
                "LOW"
            ),
    })


candidate_rows.sort(
    key=lambda r: (
        -int(
            r["score"]
        ),
        (
            0
            if r[
                "join_key_strength"
            ] == "HIGH"
            else
            1
            if r[
                "join_key_strength"
            ] == "MEDIUM"
            else
            2
        ),
        -int(
            r["rows"]
        ),
        r["file"],
    )
)


# =============================================================================
# Identify likely roles
# =============================================================================

decision_state_candidates = []

action_candidates = []

chronology_candidates = []

for r in candidate_rows:

    low = r[
        "file"
    ].lower()

    if (
        r[
            "current_result_fields"
        ]
        or
        r[
            "current_rank_fields"
        ]
        or
        r[
            "benchmark_fields"
        ]
        or
        "decision_state"
        in low
    ):
        decision_state_candidates.append(
            r
        )

    if (
        r[
            "action_fields"
        ]
        or
        r[
            "lane_fields"
        ]
        or
        "action"
        in low
    ):
        action_candidates.append(
            r
        )

    if (
        r[
            "time_fields"
        ]
        or
        r[
            "time_quality_fields"
        ]
        or
        "chronology"
        in low
    ):
        chronology_candidates.append(
            r
        )


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "candidate_files_found",

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
            "decision_state_candidate_found",

        "value":
            len(
                decision_state_candidates
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if decision_state_candidates
                else "WARN"
            ),
    },

    {
        "metric":
            "action_candidate_found",

        "value":
            len(
                action_candidates
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if action_candidates
                else "WARN"
            ),
    },

    {
        "metric":
            "chronology_candidate_found",

        "value":
            len(
                chronology_candidates
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if chronology_candidates
                else "WARN"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_FILES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = (
        list(
            candidate_rows[0].keys()
        )
        if candidate_rows
        else [
            "file",
            "rows",
            "score",
        ]
    )

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

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "file",
            "group",
            "field",
        ]
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
        "R4F0B",

    "status":
        "R4F0B_DAY1_JOIN_SOURCE_DISCOVERY_READY",

    "candidate_count":
        len(
            candidate_rows
        ),

    "decision_state_candidate_count":
        len(
            decision_state_candidates
        ),

    "action_candidate_count":
        len(
            action_candidates
        ),

    "chronology_candidate_count":
        len(
            chronology_candidates
        ),

    "goal":
        (
            "Locate the actual existing Day1 decision-state, "
            "action and chronology artifacts across the full "
            "active project before constructing the Fused adapter."
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

print("=" * 122)
print("R4F0B — DAY1 JOIN SOURCE DISCOVERY")
print("=" * 122)

print()
print(
    f"Candidate files: "
    f"{len(candidate_rows)}"
)

print(
    f"Decision-state candidates: "
    f"{len(decision_state_candidates)}"
)

print(
    f"Action candidates: "
    f"{len(action_candidates)}"
)

print(
    f"Chronology candidates: "
    f"{len(chronology_candidates)}"
)


print()
print("=" * 122)
print("TOP OVERALL CANDIDATES")
print("=" * 122)

for i, r in enumerate(
    candidate_rows[:25],
    start=1
):

    print(
        f"{i:2d}. "
        f"score={r['score']:2d} | "
        f"join={r['join_key_strength']:6s} | "
        f"rows={r['rows']:4d} | "
        f"{r['file']}"
    )

    print(
        f"    attempt_id="
        f"{r['attempt_id_fields'] or '-'}"
    )

    print(
        f"    current="
        f"{r['current_result_fields'] or '-'}"
    )

    print(
        f"    rank="
        f"{r['current_rank_fields'] or '-'}"
    )

    print(
        f"    benchmark="
        f"{r['benchmark_fields'] or '-'}"
    )

    print(
        f"    lane="
        f"{r['lane_fields'] or '-'}"
    )

    print(
        f"    action="
        f"{r['action_fields'] or '-'}"
    )

    print(
        f"    time="
        f"{r['time_fields'] or '-'}"
    )


print()
print("=" * 122)
print("TOP DECISION-STATE CANDIDATES")
print("=" * 122)

for r in decision_state_candidates[
    :15
]:

    print(
        f"score={r['score']:2d} | "
        f"join={r['join_key_strength']:6s} | "
        f"rows={r['rows']:4d} | "
        f"{r['file']}"
    )


print()
print("=" * 122)
print("TOP ACTION CANDIDATES")
print("=" * 122)

for r in action_candidates[
    :15
]:

    print(
        f"score={r['score']:2d} | "
        f"join={r['join_key_strength']:6s} | "
        f"rows={r['rows']:4d} | "
        f"{r['file']}"
    )


print()
print("=" * 122)
print("TOP CHRONOLOGY CANDIDATES")
print("=" * 122)

for r in chronology_candidates[
    :15
]:

    print(
        f"score={r['score']:2d} | "
        f"join={r['join_key_strength']:6s} | "
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
    OUT_FILES.relative_to(ROOT)
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
    "R4F0B_DAY1_JOIN_SOURCE_DISCOVERY_READY"
)
