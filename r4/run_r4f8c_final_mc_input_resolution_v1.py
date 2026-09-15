from pathlib import Path
import csv
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

TARGET_FILES = [
    OUT / "r4f8b_final_mc_eligible_decision_rows_v1.csv",
    OUT / "r4f8b_final_mc_action_expansion_v1.csv",
    OUT / "r4f8b_final_action_mc_contract_v1.json",
    OUT / "r4f7c7_final_performance_architecture_contract_v1.json",
    OUT / "r4lc5e_last_chance_fused_interface_v2.csv",
]

OUT_SCHEMA = (
    OUT /
    "r4f8c_final_mc_input_schema_resolution_v1.csv"
)

OUT_CANDIDATES = (
    OUT /
    "r4f8c_wait_queue_candidate_sources_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f8c_final_mc_input_resolution_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f8c_final_mc_input_resolution_report_v1.json"
)


KEYWORDS = {
    "CURRENT_RESULT": [
        "current",
        "protected",
        "best_speed",
        "current_speed",
        "current_result",
    ],

    "BENCHMARK": [
        "benchmark",
        "cutoff",
        "advance",
        "advancement",
        "threshold",
    ],

    "TIME": [
        "time",
        "remaining",
        "elapsed",
        "session",
    ],

    "WAIT": [
        "wait",
        "queue",
        "lane1",
        "lane2",
        "requeue",
        "return",
    ],

    "PERFORMANCE": [
        "reference",
        "fast_friday",
        "speed",
        "residual",
        "uncertainty",
        "sigma",
        "sd",
    ],

    "ACTION": [
        "action",
        "feasible",
        "protected",
        "withdraw",
        "retain",
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

    for klass, tokens in KEYWORDS.items():

        if any(
            token in c
            for token in tokens
        ):
            classes.append(
                klass
            )

    return ";".join(
        classes
    )


schema_rows = []

print("=" * 154)
print("R4F8C — FINAL MC INPUT RESOLUTION")
print("=" * 154)


for path in TARGET_FILES:

    print()
    print("=" * 154)
    print(
        f"FILE: {path.relative_to(ROOT)}"
    )
    print("=" * 154)

    if not path.exists():

        print("MISSING")

        schema_rows.append({
            "file":
                str(
                    path.relative_to(ROOT)
                ),

            "exists":
                False,

            "rows":
                0,

            "column":
                "",

            "classes":
                "",

            "sample_values":
                "",
        })

        continue


    if path.suffix.lower() == ".json":

        obj = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        print("JSON TOP-LEVEL KEYS")

        for key in obj.keys():

            print(
                f"  {key}"
            )

            schema_rows.append({
                "file":
                    str(
                        path.relative_to(ROOT)
                    ),

                "exists":
                    True,

                "rows":
                    1,

                "column":
                    key,

                "classes":
                    classify_column(
                        key
                    ),

                "sample_values":
                    clean(
                        obj.get(key)
                    )[:300],
            })

        continue


    fields, rows = read_csv(
        path
    )

    print(
        f"rows={len(rows)}"
    )

    print()
    print("ALL COLUMNS")


    for field in fields:

        values = []

        for r in rows:

            v = clean(
                r.get(
                    field
                )
            )

            if (
                v
                and
                v not in values
            ):
                values.append(
                    v
                )

            if len(
                values
            ) >= 4:
                break


        classes = classify_column(
            field
        )


        print(
            f"  {field}"
            +
            (
                f"   [{classes}]"
                if classes
                else ""
            )
        )


        schema_rows.append({
            "file":
                str(
                    path.relative_to(ROOT)
                ),

            "exists":
                True,

            "rows":
                len(rows),

            "column":
                field,

            "classes":
                classes,

            "sample_values":
                " | ".join(
                    values
                ),
        })


    print()
    print("KEY MC FIELDS")


    key_fields = [
        r
        for r in schema_rows
        if (
            r[
                "file"
            ]
            ==
            str(
                path.relative_to(ROOT)
            )
            and
            r[
                "classes"
            ]
        )
    ]


    for r in key_fields:

        print(
            f"  {r['column']:48s} | "
            f"{r['classes']:32s} | "
            f"{r['sample_values'][:100]}"
        )


# =============================================================================
# Search existing output CSVs for wait/queue evidence.
# =============================================================================

candidate_rows = []


for path in sorted(
    OUT.glob("*.csv")
):

    try:

        fields, rows = read_csv(
            path
        )

    except Exception:

        continue


    matches = []

    for field in fields:

        c = norm(
            field
        )

        if any(
            token in c
            for token in [
                "wait",
                "queue",
                "lane1",
                "lane2",
                "requeue",
                "return",
                "completion",
            ]
        ):

            matches.append(
                field
            )


    if not matches:
        continue


    candidate_rows.append({
        "file":
            str(
                path.relative_to(ROOT)
            ),

        "rows":
            len(rows),

        "matching_columns":
            ";".join(
                matches
            ),
    })


candidate_rows.sort(
    key=lambda r: (
        -r[
            "rows"
        ],
        r[
            "file"
        ],
    )
)


print()
print("=" * 154)
print("WAIT / QUEUE SOURCE CANDIDATES")
print("=" * 154)


for r in candidate_rows[:40]:

    print(
        f"{r['file'][:76]:76s} | "
        f"rows={r['rows']:4d} | "
        f"{r['matching_columns']}"
    )


# =============================================================================
# Frozen counts
# =============================================================================

decision_path = (
    OUT /
    "r4f8b_final_mc_eligible_decision_rows_v1.csv"
)

action_path = (
    OUT /
    "r4f8b_final_mc_action_expansion_v1.csv"
)

lc_path = (
    OUT /
    "r4lc5e_last_chance_fused_interface_v2.csv"
)


decision_rows = (
    read_csv(
        decision_path
    )[1]
    if decision_path.exists()
    else []
)

action_rows = (
    read_csv(
        action_path
    )[1]
    if action_path.exists()
    else []
)

lc_rows = (
    read_csv(
        lc_path
    )[1]
    if lc_path.exists()
    else []
)


print()
print("=" * 154)
print("REGIME COVERAGE")
print("=" * 154)

print(
    f"F8B MC decisions: {len(decision_rows)}"
)

print(
    f"F8B expanded actions: {len(action_rows)}"
)

print(
    f"LC fused interface rows: {len(lc_rows)}"
)


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "f8b_decision_rows",
        "value":
            len(
                decision_rows
            ),
        "expected":
            50,
        "status":
            (
                "PASS"
                if len(
                    decision_rows
                ) == 50
                else "FAIL"
            ),
    },

    {
        "metric":
            "f8b_action_rows",
        "value":
            len(
                action_rows
            ),
        "expected":
            150,
        "status":
            (
                "PASS"
                if len(
                    action_rows
                ) == 150
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_interface_rows",
        "value":
            len(
                lc_rows
            ),
        "expected":
            10,
        "status":
            (
                "PASS"
                if len(
                    lc_rows
                ) == 10
                else "FAIL"
            ),
    },

    {
        "metric":
            "wait_queue_candidate_source_found",
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
            "schema_resolution_only_no_mc_run",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


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


with OUT_CANDIDATES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    if candidate_rows:

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
        "R4F8C",

    "status":
        "R4F8C_FINAL_MC_INPUT_RESOLUTION_READY",

    "f8b_decision_rows":
        len(
            decision_rows
        ),

    "f8b_action_rows":
        len(
            action_rows
        ),

    "last_chance_interface_rows":
        len(
            lc_rows
        ),

    "wait_queue_candidate_sources":
        candidate_rows[:30],

    "important_boundary":
        (
            "R4F8B currently contains Day1 decision states only. "
            "Last Chance must remain a separate regime-specific action "
            "branch and be integrated before final system completion."
        ),

    "next_phase":
        (
            "R4F8D final Day1 Monte Carlo engine, followed by "
            "Last Chance regime integration using its frozen action semantics."
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


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)} PASS | "
    f"0 WARN | "
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
    OUT_SCHEMA.relative_to(
        ROOT
    )
)

print(
    OUT_CANDIDATES.relative_to(
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
    "R4F8C_FINAL_MC_INPUT_RESOLUTION_READY"
)
