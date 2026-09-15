from pathlib import Path
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

FILES = {
    "chronology_v10":
        ROOT /
        "weather/output/unified_attempt_chronology_constraint_ledger_v10.csv",

    "decision_state_v2":
        ROOT /
        "weather/output/decision_time_observable_state_v2.csv",

    "decision_evidence_v2":
        ROOT /
        "weather/output/contemporaneous_decision_state_evidence_ledger_v2.csv",

    "action_lane_v8":
        ROOT /
        "weather/output/unified_attempt_action_lane_ledger_v8.csv",

    "attempt_panel_v1":
        ROOT /
        "r4/output/r4p1_attempt_four_lap_panel_v1.csv",
}

OUT = ROOT / "r4/output"
OUT.mkdir(
    parents=True,
    exist_ok=True
)

OUT_REPORT = (
    OUT /
    "r4f0c_day1_exact_join_contract_report_v1.json"
)

OUT_QA = (
    OUT /
    "r4f0c_day1_exact_join_contract_qa_v1.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def clean(v):
    return "" if v is None else str(v).strip()


def nonempty_values(rows, field, limit=12):
    values = []

    seen = set()

    for row in rows:

        value = clean(
            row.get(field)
        )

        if not value:
            continue

        if value in seen:
            continue

        seen.add(
            value
        )

        values.append(
            value
        )

        if len(values) >= limit:
            break

    return values


loaded = {}

print("=" * 122)
print("R4F0C — DAY1 EXACT JOIN CONTRACT INSPECTION")
print("=" * 122)

for name, path in FILES.items():

    print()
    print("=" * 122)
    print(name)
    print("=" * 122)

    if not path.exists():

        print(
            f"MISSING: {path}"
        )

        loaded[name] = {
            "path":
                str(path),

            "rows":
                [],

            "fields":
                [],

            "exists":
                False,
        }

        continue

    rows = read_csv(
        path
    )

    fields = (
        list(
            rows[0].keys()
        )
        if rows
        else []
    )

    loaded[name] = {
        "path":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "rows":
            rows,

        "fields":
            fields,

        "exists":
            True,
    }

    print(
        f"rows={len(rows)}"
    )

    print()
    print("FIELDS")

    for field in fields:
        print(
            f"  {field}"
        )

    print()
    print("FIRST 3 ROWS")

    for i, row in enumerate(
        rows[:3],
        start=1
    ):

        print()
        print(
            f"ROW {i}"
        )

        print(
            json.dumps(
                row,
                indent=2,
                ensure_ascii=False
            )
        )


# =============================================================================
# Full decision-state rows
# =============================================================================

state_rows = loaded[
    "decision_state_v2"
][
    "rows"
]

print()
print("=" * 122)
print("ALL DECISION STATE V2 ROWS")
print("=" * 122)

for i, row in enumerate(
    state_rows,
    start=1
):

    print()
    print(
        f"STATE ROW {i}"
    )

    print(
        json.dumps(
            row,
            indent=2,
            ensure_ascii=False
        )
    )


# =============================================================================
# Candidate join fields by exact common column name
# =============================================================================

names = list(
    loaded.keys()
)

print()
print("=" * 122)
print("EXACT COMMON FIELDS")
print("=" * 122)

common_field_report = []

for i, left_name in enumerate(
    names
):

    for right_name in names[
        i + 1:
    ]:

        left_fields = set(
            loaded[
                left_name
            ][
                "fields"
            ]
        )

        right_fields = set(
            loaded[
                right_name
            ][
                "fields"
            ]
        )

        common = sorted(
            left_fields
            &
            right_fields
        )

        if not common:
            continue

        print()
        print(
            f"{left_name} <-> {right_name}"
        )

        for field in common:
            print(
                f"  {field}"
            )

        common_field_report.append({
            "left":
                left_name,

            "right":
                right_name,

            "common_fields":
                common,
        })


# =============================================================================
# Candidate identity fields and observed values
# =============================================================================

IDENTITY_FIELDS = [
    "attempt_id",
    "year",
    "car_number",
    "car",
    "driver_name",
    "driver",
    "session",
    "session_name",
    "decision_id",
    "decision_key",
    "attempt_index",
    "attempt_number",
    "run_number",
    "lane",
    "queue_lane",
    "action",
]

print()
print("=" * 122)
print("IDENTITY / JOIN FIELD VALUES")
print("=" * 122)

identity_report = {}

for name in names:

    rows = loaded[
        name
    ][
        "rows"
    ]

    fields = loaded[
        name
    ][
        "fields"
    ]

    print()
    print(
        name
    )

    identity_report[
        name
    ] = {}

    for field in IDENTITY_FIELDS:

        if field not in fields:
            continue

        values = nonempty_values(
            rows,
            field,
            limit=20
        )

        identity_report[
            name
        ][
            field
        ] = values

        print(
            f"  {field}: "
            f"{values}"
        )


# =============================================================================
# Look for semantic-equivalent columns
# =============================================================================

semantic_groups = {
    "year":
        [
            "year",
        ],

    "car":
        [
            "car_number",
            "car",
            "entry_number",
        ],

    "driver":
        [
            "driver_name",
            "driver",
        ],

    "action":
        [
            "action",
            "strategy_action",
            "lane_action",
        ],

    "lane":
        [
            "lane",
            "queue_lane",
            "lane_action",
        ],

    "rank":
        [
            "current_rank",
            "rank",
            "current_position",
        ],

    "benchmark":
        [
            "cutoff_speed_mph",
            "benchmark_speed_mph",
            "advancement_benchmark",
        ],

    "time":
        [
            "time_point_utc",
            "decision_time_utc",
            "canonical_start_time_utc",
            "canonical_end_time_utc",
        ],
}


print()
print("=" * 122)
print("SEMANTIC FIELD MAP")
print("=" * 122)

semantic_report = {}

for name in names:

    fields = set(
        loaded[
            name
        ][
            "fields"
        ]
    )

    semantic_report[
        name
    ] = {}

    print()
    print(
        name
    )

    for semantic, candidates in semantic_groups.items():

        hits = [
            field
            for field in candidates
            if field in fields
        ]

        if hits:

            semantic_report[
                name
            ][
                semantic
            ] = hits

            print(
                f"  {semantic}: "
                f"{hits}"
            )


# =============================================================================
# QA
# =============================================================================

qa_rows = []

for name, obj in loaded.items():

    qa_rows.append({
        "metric":
            f"{name}_exists",

        "value":
            obj[
                "exists"
            ],

        "expected":
            True,

        "status":
            (
                "PASS"
                if obj[
                    "exists"
                ]
                else "FAIL"
            ),
    })


qa_rows.append({
    "metric":
        "decision_state_rows",

    "value":
        len(
            state_rows
        ),

    "expected":
        8,

    "status":
        (
            "PASS"
            if len(
                state_rows
            ) == 8
            else "WARN"
        ),
})


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
        "R4F0C",

    "status":
        "R4F0C_DAY1_EXACT_JOIN_CONTRACT_INSPECTION_READY",

    "files": {
        name: {
            "path":
                obj[
                    "path"
                ],

            "exists":
                obj[
                    "exists"
                ],

            "rows":
                len(
                    obj[
                        "rows"
                    ]
                ),

            "fields":
                obj[
                    "fields"
                ],
        }
        for name, obj in loaded.items()
    },

    "common_fields":
        common_field_report,

    "identity_values":
        identity_report,

    "semantic_map":
        semantic_report,

    "next_phase":
        (
            "Construct R4F1 Day1 adapter using verified join "
            "keys only; no guessed identity linkage."
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
print("=" * 122)
print("QA")
print("=" * 122)

print(
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    for row in fails:

        print(
            f"FAIL | "
            f"{row['metric']} | "
            f"{row['value']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_REPORT.relative_to(
        ROOT
    )
)
print(
    OUT_QA.relative_to(
        ROOT
    )
)

print()
print(
    "R4F0C_DAY1_EXACT_JOIN_CONTRACT_INSPECTION_READY"
)
