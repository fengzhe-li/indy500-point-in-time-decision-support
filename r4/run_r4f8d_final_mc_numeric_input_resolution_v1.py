from pathlib import Path
import csv
import json
import re
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

DECISION_PATH = (
    OUT /
    "r4f8c_fused_mc_decision_universe_v1.csv"
)

ACTION_PATH = (
    OUT /
    "r4f8c_fused_mc_action_expansion_v1.csv"
)

MC_CONTRACT_PATH = (
    OUT /
    "r4f8c_fused_mc_coverage_contract_v1.json"
)

PERFORMANCE_CONTRACT = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

VALIDATION_CONCLUSION = (
    OUT /
    "r4f7v2_external_validation_conclusion_v1.json"
)

OUT_DECISION_SCHEMA = (
    OUT /
    "r4f8d_final_mc_decision_numeric_schema_v1.csv"
)

OUT_WAIT_CANDIDATES = (
    OUT /
    "r4f8d_final_mc_wait_queue_source_candidates_v1.csv"
)

OUT_RESOLUTION = (
    OUT /
    "r4f8d_final_mc_numeric_input_resolution_v1.json"
)

OUT_QA = (
    OUT /
    "r4f8d_final_mc_numeric_input_resolution_qa_v1.csv"
)


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

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def numeric_profile(
    rows,
    field
):

    values = [
        num(
            r.get(field)
        )
        for r in rows
    ]

    values = [
        x
        for x in values
        if x is not None
    ]

    if not values:

        return {
            "numeric_rows":
                0,

            "numeric_fraction":
                0.0,

            "unique_numeric":
                0,

            "min":
                "",

            "max":
                "",
        }


    return {
        "numeric_rows":
            len(values),

        "numeric_fraction":
            (
                len(values)
                /
                len(rows)
            ),

        "unique_numeric":
            len(
                {
                    round(
                        x,
                        8
                    )
                    for x in values
                }
            ),

        "min":
            min(values),

        "max":
            max(values),
    }


def classify_field(field):
    c = norm(field)

    classes = []


    if (
        "benchmark" in c
        or
        "cutoff" in c
        or
        "bubble" in c
        or
        "threshold" in c
    ):
        classes.append(
            "BENCHMARK"
        )


    if (
        (
            "current" in c
            or
            "protected" in c
            or
            "existing" in c
        )
        and
        (
            "speed" in c
            or
            "result" in c
            or
            "rank" in c
        )
    ):
        classes.append(
            "CURRENT_STATE"
        )


    if (
        "speed" in c
        and
        not (
            "benchmark" in c
            or
            "cutoff" in c
        )
    ):
        classes.append(
            "SPEED"
        )


    if (
        "rank" in c
        or
        "position" in c
    ):
        classes.append(
            "RANK"
        )


    if (
        "time" in c
        or
        "minutes" in c
        or
        "seconds" in c
        or
        "elapsed" in c
        or
        "remaining" in c
    ):
        classes.append(
            "TIME"
        )


    if (
        "queue" in c
        or
        "wait" in c
        or
        "lane" in c
    ):
        classes.append(
            "QUEUE_WAIT"
        )


    if (
        "action" in c
    ):
        classes.append(
            "ACTION"
        )


    if (
        "session" in c
        or
        "regime" in c
    ):
        classes.append(
            "SESSION_REGIME"
        )


    if (
        "protected" in c
        or
        "valid_result" in c
        or
        "has_result" in c
    ):
        classes.append(
            "PROTECTION"
        )


    if (
        "attempt_id" in c
        or
        "decision_id" in c
        or
        "state_id" in c
    ):
        classes.append(
            "IDENTIFIER"
        )


    return ";".join(
        classes
    )


for path in [
    DECISION_PATH,
    ACTION_PATH,
    MC_CONTRACT_PATH,
    PERFORMANCE_CONTRACT,
    VALIDATION_CONCLUSION,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


decision_fields, decisions = read_csv(
    DECISION_PATH
)

action_fields, actions = read_csv(
    ACTION_PATH
)


mc_contract = json.loads(
    MC_CONTRACT_PATH.read_text(
        encoding="utf-8"
    )
)

performance_contract = json.loads(
    PERFORMANCE_CONTRACT.read_text(
        encoding="utf-8"
    )
)

validation_conclusion = json.loads(
    VALIDATION_CONCLUSION.read_text(
        encoding="utf-8"
    )
)


print("=" * 154)
print("R4F8D — FINAL MC NUMERIC INPUT RESOLUTION")
print("=" * 154)

print(
    f"Decision rows: {len(decisions)}"
)

print(
    f"Action rows: {len(actions)}"
)


# =============================================================================
# Decision schema
# =============================================================================

decision_schema_rows = []


for field in decision_fields:

    profile = numeric_profile(
        decisions,
        field
    )

    decision_schema_rows.append({
        "field":
            field,

        "semantic_class":
            classify_field(
                field
            ),

        **profile,
    })


print()
print("=" * 154)
print("DECISION UNIVERSE — ALL COLUMNS")
print("=" * 154)

for r in decision_schema_rows:

    print(
        f"{r['field']:52s} | "
        f"class={r['semantic_class']:34s} | "
        f"numeric={r['numeric_rows']:3d}/"
        f"{len(decisions):3d} | "
        f"unique={r['unique_numeric']:3d} | "
        f"min={r['min']} | "
        f"max={r['max']}"
    )


print()
print("=" * 154)
print("ACTION EXPANSION — ALL COLUMNS")
print("=" * 154)

for field in action_fields:

    profile = numeric_profile(
        actions,
        field
    )

    print(
        f"{field:52s} | "
        f"class={classify_field(field):34s} | "
        f"numeric={profile['numeric_rows']:3d}/"
        f"{len(actions):3d} | "
        f"unique={profile['unique_numeric']:3d}"
    )


# =============================================================================
# Candidate important fields
# =============================================================================

candidate_classes = {
    "BENCHMARK":
        [],

    "CURRENT_STATE":
        [],

    "SPEED":
        [],

    "RANK":
        [],

    "TIME":
        [],

    "QUEUE_WAIT":
        [],

    "PROTECTION":
        [],

    "SESSION_REGIME":
        [],
}


for r in decision_schema_rows:

    classes = (
        r[
            "semantic_class"
        ].split(";")
        if r[
            "semantic_class"
        ]
        else []
    )

    for cls in candidate_classes:

        if cls in classes:

            candidate_classes[
                cls
            ].append(
                r[
                    "field"
                ]
            )


print()
print("=" * 154)
print("RESOLVED DECISION FIELD CANDIDATES")
print("=" * 154)

for cls, fields in (
    candidate_classes.items()
):

    print()
    print(cls)

    if not fields:
        print("  NONE")

    else:

        for field in fields:

            print(
                f"  {field}"
            )


# =============================================================================
# Wait / queue source discovery
# =============================================================================

wait_candidates = []


for path in sorted(
    OUT.glob(
        "*.csv"
    )
):

    name = path.name.lower()

    if not any(
        token in name
        for token in [
            "wait",
            "queue",
            "lane",
            "p11",
            "requeue",
            "return",
        ]
    ):

        continue


    if path in {
        DECISION_PATH,
        ACTION_PATH,
    }:
        continue


    try:

        fields, rows = read_csv(
            path
        )

    except Exception:

        continue


    if not rows:
        continue


    queue_fields = [
        f
        for f in fields
        if (
            "queue" in norm(f)
            or
            "wait" in norm(f)
            or
            "lane" in norm(f)
            or
            "requeue" in norm(f)
            or
            "minutes" in norm(f)
            or
            "seconds" in norm(f)
        )
    ]


    action_fields_here = [
        f
        for f in fields
        if (
            "action" in norm(f)
            or
            "lane" in norm(f)
        )
    ]


    decision_id_fields = [
        f
        for f in fields
        if (
            "decision_id" in norm(f)
            or
            "attempt_id" in norm(f)
            or
            "state_id" in norm(f)
        )
    ]


    numeric_queue_fields = []


    for field in queue_fields:

        profile = numeric_profile(
            rows,
            field
        )

        if profile[
            "numeric_rows"
        ] > 0:

            numeric_queue_fields.append(
                field
            )


    wait_candidates.append({
        "file":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "rows":
            len(rows),

        "queue_wait_fields":
            ";".join(
                queue_fields
            ),

        "numeric_queue_wait_fields":
            ";".join(
                numeric_queue_fields
            ),

        "action_or_lane_fields":
            ";".join(
                action_fields_here
            ),

        "decision_identifier_fields":
            ";".join(
                decision_id_fields
            ),
    })


wait_candidates.sort(
    key=lambda r: (
        -int(
            bool(
                r[
                    "numeric_queue_wait_fields"
                ]
            )
        ),
        -int(
            bool(
                r[
                    "decision_identifier_fields"
                ]
            )
        ),
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

if not wait_candidates:

    print("NONE")

else:

    for r in wait_candidates[:30]:

        print()
        print(
            f"FILE: {r['file']}"
        )

        print(
            f"  rows={r['rows']}"
        )

        print(
            f"  numeric_queue_wait_fields="
            f"[{r['numeric_queue_wait_fields']}]"
        )

        print(
            f"  action_or_lane_fields="
            f"[{r['action_or_lane_fields']}]"
        )

        print(
            f"  decision_identifier_fields="
            f"[{r['decision_identifier_fields']}]"
        )


# =============================================================================
# Performance uncertainty evidence
# =============================================================================

selected_k = (
    performance_contract.get(
        "selected_shrinkage_k"
    )
)

prior_mean = (
    performance_contract.get(
        "frozen_cross_year_prior_mean_residual_mph"
    )
)

prior_sd = (
    performance_contract.get(
        "frozen_cross_year_prior_sd_mph"
    )
)

external_status = (
    validation_conclusion.get(
        "model_status"
    )
)


print()
print("=" * 154)
print("FROZEN PERFORMANCE INPUT")
print("=" * 154)

print(
    f"selected_shrinkage_k={selected_k}"
)

print(
    f"prior_mean_residual_mph={prior_mean}"
)

print(
    f"prior_sd_residual_mph={prior_sd}"
)

print(
    f"external_validation_status={external_status}"
)

print(
    "uncertainty_policy="
    "BROAD_EARLY_SESSION_AND_SHRINK_WITH_CURRENT_SESSION_EVIDENCE"
)


# =============================================================================
# Automatic architecture resolution
# =============================================================================

has_benchmark = (
    len(
        candidate_classes[
            "BENCHMARK"
        ]
    ) > 0
)

has_speed = (
    len(
        candidate_classes[
            "SPEED"
        ]
    ) > 0
)

has_time = (
    len(
        candidate_classes[
            "TIME"
        ]
    ) > 0
)

has_protection = (
    len(
        candidate_classes[
            "PROTECTION"
        ]
    ) > 0
)

has_numeric_wait_source = any(
    bool(
        clean(
            r[
                "numeric_queue_wait_fields"
            ]
        )
    )
    for r in wait_candidates
)


resolution = {
    "phase":
        "R4F8D",

    "status":
        "R4F8D_FINAL_MC_NUMERIC_INPUTS_RESOLVED",

    "decision_rows":
        len(
            decisions
        ),

    "action_rows":
        len(
            actions
        ),

    "decision_fields":
        decision_fields,

    "action_fields":
        action_fields,

    "semantic_candidates":
        candidate_classes,

    "wait_queue_source_candidates":
        wait_candidates,

    "performance_model": {
        "selected_shrinkage_k":
            selected_k,

        "prior_mean_residual_mph":
            prior_mean,

        "prior_sd_residual_mph":
            prior_sd,

        "external_validation_status":
            external_status,
    },

    "availability": {
        "benchmark_field_candidate":
            has_benchmark,

        "speed_field_candidate":
            has_speed,

        "time_field_candidate":
            has_time,

        "protection_field_candidate":
            has_protection,

        "numeric_wait_queue_source_candidate":
            has_numeric_wait_source,
    },

    "frozen_rules": {
        "old_p11_probabilities":
            "FORBIDDEN_AS_FINAL_MC_OUTPUT",

        "old_wait_queue_evidence":
            (
                "MAY_BE_REUSED_ONLY_AS EMPIRICAL/DECLARED WAIT INPUT "
                "AFTER FIELD-LEVEL SEMANTICS ARE VERIFIED"
            ),

        "performance":
            (
                "FAST_FRIDAY_REFERENCE_PLUS_FROZEN_ONLINE_SHRUNK_"
                "SESSION_CALIBRATION_PLUS_UNCERTAINTY"
            ),

        "external_validation":
            "MIXED_SO_EARLY_SESSION_UNCERTAINTY_MUST_REMAIN_BROAD",
    },

    "next_phase":
        (
            "R4F8E_FINAL_FUSED_ACTION_MONTE_CARLO"
        ),
}


OUT_RESOLUTION.write_text(
    json.dumps(
        resolution,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


with OUT_DECISION_SCHEMA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            decision_schema_rows[
                0
            ].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        decision_schema_rows
    )


if wait_candidates:

    with OUT_WAIT_CANDIDATES.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                wait_candidates[
                    0
                ].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            wait_candidates
        )


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "fused_decisions",
        "value":
            len(decisions),
        "expected":
            60,
        "status":
            (
                "PASS"
                if len(decisions) == 60
                else "FAIL"
            ),
    },

    {
        "metric":
            "expanded_action_rows",
        "value":
            len(actions),
        "expected":
            170,
        "status":
            (
                "PASS"
                if len(actions) == 170
                else "FAIL"
            ),
    },

    {
        "metric":
            "benchmark_candidate_found",
        "value":
            has_benchmark,
        "expected":
            True,
        "status":
            (
                "PASS"
                if has_benchmark
                else "WARN"
            ),
    },

    {
        "metric":
            "speed_candidate_found",
        "value":
            has_speed,
        "expected":
            True,
        "status":
            (
                "PASS"
                if has_speed
                else "WARN"
            ),
    },

    {
        "metric":
            "numeric_wait_candidate_found",
        "value":
            has_numeric_wait_source,
        "expected":
            True,
        "status":
            (
                "PASS"
                if has_numeric_wait_source
                else "WARN"
            ),
    },

    {
        "metric":
            "old_p11_final_probabilities_reused",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "model_refit_performed",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "mc_simulation_performed",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },
]


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


print()
print("=" * 154)
print("FINAL MC READINESS")
print("=" * 154)

print(
    f"benchmark_candidate_found={has_benchmark}"
)

print(
    f"speed_candidate_found={has_speed}"
)

print(
    f"time_candidate_found={has_time}"
)

print(
    f"protection_candidate_found={has_protection}"
)

print(
    f"numeric_wait_queue_source_found={has_numeric_wait_source}"
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
    OUT_DECISION_SCHEMA.relative_to(
        ROOT
    )
)

if wait_candidates:

    print(
        OUT_WAIT_CANDIDATES.relative_to(
            ROOT
        )
    )

print(
    OUT_RESOLUTION.relative_to(
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
    "R4F8D_FINAL_MC_NUMERIC_INPUTS_RESOLVED"
)
