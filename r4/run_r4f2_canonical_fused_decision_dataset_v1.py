from pathlib import Path
from collections import Counter, defaultdict
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

DAY1_PATH = (
    OUT /
    "r4f1_day1_fused_interface_v1.csv"
)

LC_PATH = (
    OUT /
    "r4lc5e_last_chance_fused_interface_v2.csv"
)

SCHEMA_PATH = (
    OUT /
    "r4lc5e_fused_decision_schema_contract_v2.json"
)

OUT_DATASET = (
    OUT /
    "r4f2_canonical_fused_decision_dataset_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f2_canonical_fused_decision_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f2_canonical_fused_decision_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f2_canonical_fused_decision_report_v1.json"
)


TRAIN_YEARS = {
    2020,
    2021,
    2023,
}

VALIDATION_YEARS = {
    2022,
    2024,
}


ACTIONS = [
    "STOP",
    "REATTEMPT",
    "RETAIN_AND_REATTEMPT",
    "WITHDRAW_AND_REATTEMPT",
    "WITHDRAW_AND_PRIORITY_REATTEMPT",
]

UNRESOLVED_ACTION = (
    "REATTEMPT_SEMANTICS_UNRESOLVED"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truth(v):
    return clean(v).lower() in {
        "true",
        "1",
        "yes",
    }


def integer(v):
    s = clean(v)

    if not s:
        return None

    try:
        return int(
            float(s)
        )
    except Exception:
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


for path in [
    DAY1_PATH,
    LC_PATH,
    SCHEMA_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


day1_rows = read_csv(
    DAY1_PATH
)

lc_rows = read_csv(
    LC_PATH
)

schema = json.loads(
    SCHEMA_PATH.read_text(
        encoding="utf-8"
    )
)


print("=" * 124)
print("R4F2 — CANONICAL FUSED DECISION DATASET")
print("=" * 124)

print(
    f"Day1 rows: "
    f"{len(day1_rows)}"
)

print(
    f"Last Chance rows: "
    f"{len(lc_rows)}"
)

print(
    f"Frozen schema: "
    f"{schema.get('schema_name')}"
)


# =============================================================================
# Canonical output columns
# =============================================================================

rows = []


# =============================================================================
# Day1 adapter
# =============================================================================

for r in day1_rows:

    year = integer(
        r.get(
            "year"
        )
    )

    observed = clean(
        r.get(
            "observed_action_unified"
        )
    )

    action_resolved = (
        observed in ACTIONS
    )

    if year in VALIDATION_YEARS:

        dataset_role = (
            "VALIDATION_ONLY"
        )

    elif action_resolved:

        dataset_role = (
            "MODEL_STATE_PLUS_ACTION_EVIDENCE"
        )

    else:

        dataset_role = (
            "MODEL_STATE_PLUS_STRUCTURAL_REATTEMPT_EVIDENCE"
        )


    safe_policy = truth(
        r.get(
            "safe_for_policy_fit"
        )
    )

    if safe_policy:

        behaviour_supervision = (
            "OBSERVED_BEHAVIOUR_HIGH_CONFIDENCE"
        )

    elif (
        observed
        == UNRESOLVED_ACTION
    ):

        behaviour_supervision = (
            "REATtempt_OCCURRED_ACTION_BRANCH_UNRESOLVED"
        )

    else:

        behaviour_supervision = (
            "OBSERVED_BEHAVIOUR_NOT_POLICY_TRUTH"
        )


    row = {
        "decision_id":
            clean(
                r.get(
                    "decision_id"
                )
            ),

        "year":
            year,

        "session_regime":
            "DAY1",

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "driver_name":
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "decision_stage":
            clean(
                r.get(
                    "decision_stage"
                )
            ),

        "source_attempt_id":
            clean(
                r.get(
                    "source_attempt_id"
                )
            ),

        "current_result_mph":
            clean(
                r.get(
                    "current_result_mph"
                )
            ),

        "current_rank":
            clean(
                r.get(
                    "current_rank"
                )
            ),

        "benchmark_type":
            clean(
                r.get(
                    "benchmark_type"
                )
            ),

        "benchmark_rank":
            clean(
                r.get(
                    "benchmark_rank"
                )
            ),

        "benchmark_speed_mph":
            clean(
                r.get(
                    "benchmark_speed_mph"
                )
            ),

        "margin_to_benchmark_mph":
            clean(
                r.get(
                    "margin_to_benchmark_mph"
                )
            ),

        "qualification_state":
            clean(
                r.get(
                    "qualification_state"
                )
            ),

        "has_protected_result":
            clean(
                r.get(
                    "has_protected_result"
                )
            ),

        "feasible_action_set":
            clean(
                r.get(
                    "feasible_action_set"
                )
            ),

        "action_mask_STOP":
            clean(
                r.get(
                    "action_mask_STOP"
                )
            ),

        "action_mask_REATTEMPT":
            clean(
                r.get(
                    "action_mask_REATTEMPT"
                )
            ),

        "action_mask_RETAIN_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_RETAIN_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
                )
            ),

        "observed_action":
            observed,

        "action_resolved":
            action_resolved,

        "action_evidence_quality":
            clean(
                r.get(
                    "observed_action_quality"
                )
            ),

        "decision_time_utc":
            clean(
                r.get(
                    "decision_time_utc"
                )
            ),

        "time_quality":
            clean(
                r.get(
                    "time_quality"
                )
            ),

        "state_numeric_complete":
            clean(
                r.get(
                    "state_numeric_complete"
                )
            ),

        "thermal_state_available":
            clean(
                r.get(
                    "thermal_state_available"
                )
            ),

        "performance_uncertainty_available":
            clean(
                r.get(
                    "performance_uncertainty_available"
                )
            ),

        "wait_model_available":
            clean(
                r.get(
                    "wait_model_available"
                )
            ),

        "shared_feature_link_status":
            clean(
                r.get(
                    "shared_feature_link_status"
                )
            ),

        "dataset_role":
            dataset_role,

        "behaviour_supervision_role":
            behaviour_supervision,

        "safe_for_policy_fit":
            safe_policy,

        "hard_optimality_truth":
            False,

        "validation_only":
            year in VALIDATION_YEARS,

        "source_interface":
            "R4F1_DAY1",
    }

    rows.append(
        row
    )


# =============================================================================
# Last Chance adapter
# =============================================================================

for r in lc_rows:

    year = integer(
        r.get(
            "year"
        )
    )

    observed = clean(
        r.get(
            "observed_action_unified"
        )
    )

    action_resolved = (
        observed in ACTIONS
    )

    if year in VALIDATION_YEARS:

        dataset_role = (
            "VALIDATION_ONLY"
        )

    else:

        dataset_role = (
            "MODEL_STATE_PLUS_ACTION_EVIDENCE"
        )


    safe_policy = truth(
        r.get(
            "safe_for_policy_fit"
        )
    )

    if safe_policy:

        behaviour_supervision = (
            "OBSERVED_BEHAVIOUR_HIGH_CONFIDENCE"
        )

    else:

        behaviour_supervision = (
            "OBSERVED_BEHAVIOUR_NOT_POLICY_TRUTH"
        )


    row = {
        "decision_id":
            clean(
                r.get(
                    "decision_id"
                )
            ),

        "year":
            year,

        "session_regime":
            "LAST_CHANCE",

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "driver_name":
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "decision_stage":
            clean(
                r.get(
                    "decision_stage"
                )
            ),

        "source_attempt_id":
            "",

        "current_result_mph":
            clean(
                r.get(
                    "current_result_mph"
                )
            ),

        "current_rank":
            clean(
                r.get(
                    "current_rank"
                )
            ),

        "benchmark_type":
            clean(
                r.get(
                    "benchmark_type"
                )
            ),

        "benchmark_rank":
            "",

        "benchmark_speed_mph":
            clean(
                r.get(
                    "benchmark_speed_mph"
                )
            ),

        "margin_to_benchmark_mph":
            clean(
                r.get(
                    "margin_to_benchmark_mph"
                )
            ),

        "qualification_state":
            clean(
                r.get(
                    "qualification_state"
                )
            ),

        "has_protected_result":
            clean(
                r.get(
                    "has_protected_result"
                )
            ),

        "feasible_action_set":
            clean(
                r.get(
                    "feasible_action_set"
                )
            ),

        "action_mask_STOP":
            clean(
                r.get(
                    "action_mask_STOP"
                )
            ),

        "action_mask_REATTEMPT":
            clean(
                r.get(
                    "action_mask_REATTEMPT"
                )
            ),

        "action_mask_RETAIN_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_RETAIN_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
                )
            ),

        "observed_action":
            observed,

        "action_resolved":
            action_resolved,

        "action_evidence_quality":
            clean(
                r.get(
                    "action_quality"
                )
            ),

        "decision_time_utc":
            clean(
                r.get(
                    "exact_timestamp"
                )
            ),

        "time_quality":
            clean(
                r.get(
                    "time_quality"
                )
            ),

        "state_numeric_complete":
            bool(
                clean(
                    r.get(
                        "current_result_mph"
                    )
                )
                and
                clean(
                    r.get(
                        "benchmark_speed_mph"
                    )
                )
            ),

        "thermal_state_available":
            clean(
                r.get(
                    "thermal_state_available"
                )
            ),

        "performance_uncertainty_available":
            clean(
                r.get(
                    "performance_uncertainty_available"
                )
            ),

        "wait_model_available":
            clean(
                r.get(
                    "wait_model_available"
                )
            ),

        "shared_feature_link_status":
            clean(
                r.get(
                    "shared_feature_link_status"
                )
            ),

        "dataset_role":
            dataset_role,

        "behaviour_supervision_role":
            behaviour_supervision,

        "safe_for_policy_fit":
            safe_policy,

        "hard_optimality_truth":
            False,

        "validation_only":
            year in VALIDATION_YEARS,

        "source_interface":
            "R4LC5E_V2",
    }

    rows.append(
        row
    )


# =============================================================================
# QA
# =============================================================================

ids = [
    r[
        "decision_id"
    ]
    for r in rows
]

duplicate_ids = [
    x
    for x, count
    in Counter(ids).items()
    if count > 1
]

validation_leak = [
    r
    for r in rows
    if (
        r[
            "validation_only"
        ]
        and
        r[
            "safe_for_policy_fit"
        ]
    )
]

hard_truth_rows = [
    r
    for r in rows
    if r[
        "hard_optimality_truth"
    ]
]

invalid_actions = [
    r
    for r in rows
    if (
        r[
            "observed_action"
        ]
        not in ACTIONS
        and
        r[
            "observed_action"
        ]
        != UNRESOLVED_ACTION
    )
]


qa_rows = [
    {
        "metric":
            "all_rows_preserved",

        "value":
            len(rows),

        "expected":
            len(day1_rows)
            + len(lc_rows),

        "status":
            (
                "PASS"
                if len(rows)
                ==
                len(day1_rows)
                + len(lc_rows)
                else "FAIL"
            ),
    },

    {
        "metric":
            "decision_ids_unique",

        "value":
            len(
                duplicate_ids
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not duplicate_ids
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_policy_fit_leakage",

        "value":
            len(
                validation_leak
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not validation_leak
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_hard_optimality_truth",

        "value":
            len(
                hard_truth_rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not hard_truth_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "only_valid_or_explicitly_unresolved_actions",

        "value":
            len(
                invalid_actions
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not invalid_actions
                else "FAIL"
            ),
    },

    {
        "metric":
            "both_regimes_present",

        "value":
            ";".join(
                sorted(
                    {
                        r[
                            "session_regime"
                        ]
                        for r in rows
                    }
                )
            ),

        "expected":
            "DAY1;LAST_CHANCE",

        "status":
            (
                "PASS"
                if {
                    r[
                        "session_regime"
                    ]
                    for r in rows
                }
                ==
                {
                    "DAY1",
                    "LAST_CHANCE",
                }
                else "FAIL"
            ),
    },
]


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for regime in [
    "DAY1",
    "LAST_CHANCE",
]:

    for year in sorted(
        {
            r[
                "year"
            ]
            for r in rows
            if r[
                "session_regime"
            ] == regime
        }
    ):

        subset = [
            r
            for r in rows
            if (
                r[
                    "session_regime"
                ] == regime
                and
                r[
                    "year"
                ] == year
            )
        ]

        counts = Counter(
            r[
                "observed_action"
            ]
            for r in subset
        )

        summary_rows.append({
            "session_regime":
                regime,

            "year":
                year,

            "rows":
                len(
                    subset
                ),

            "resolved_action_rows":
                sum(
                    bool(
                        r[
                            "action_resolved"
                        ]
                    )
                    for r in subset
                ),

            "unresolved_action_rows":
                sum(
                    not bool(
                        r[
                            "action_resolved"
                        ]
                    )
                    for r in subset
                ),

            "numeric_state_rows":
                sum(
                    truth(
                        r[
                            "state_numeric_complete"
                        ]
                    )
                    for r in subset
                ),

            "policy_fit_rows":
                sum(
                    bool(
                        r[
                            "safe_for_policy_fit"
                        ]
                    )
                    for r in subset
                ),

            "validation_rows":
                sum(
                    bool(
                        r[
                            "validation_only"
                        ]
                    )
                    for r in subset
                ),

            "STOP":
                counts.get(
                    "STOP",
                    0
                ),

            "REATTEMPT":
                counts.get(
                    "REATTEMPT",
                    0
                ),

            "RETAIN_AND_REATTEMPT":
                counts.get(
                    "RETAIN_AND_REATTEMPT",
                    0
                ),

            "WITHDRAW_AND_REATTEMPT":
                counts.get(
                    "WITHDRAW_AND_REATTEMPT",
                    0
                ),

            "WITHDRAW_AND_PRIORITY_REATTEMPT":
                counts.get(
                    "WITHDRAW_AND_PRIORITY_REATTEMPT",
                    0
                ),

            "UNRESOLVED":
                counts.get(
                    UNRESOLVED_ACTION,
                    0
                ),
        })


# =============================================================================
# Save
# =============================================================================

with OUT_DATASET.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        rows
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
        "R4F2",

    "status":
        "R4F2_CANONICAL_FUSED_DECISION_DATASET_READY",

    "schema_name":
        schema.get(
            "schema_name"
        ),

    "row_count":
        len(rows),

    "day1_rows":
        len(day1_rows),

    "last_chance_rows":
        len(lc_rows),

    "resolved_action_rows":
        sum(
            bool(
                r[
                    "action_resolved"
                ]
            )
            for r in rows
        ),

    "unresolved_action_rows":
        sum(
            not bool(
                r[
                    "action_resolved"
                ]
            )
            for r in rows
        ),

    "policy_fit_rows":
        sum(
            bool(
                r[
                    "safe_for_policy_fit"
                ]
            )
            for r in rows
        ),

    "methodology": [
        (
            "Historical observed actions are behaviour evidence, "
            "not hard optimality labels."
        ),

        (
            "Day1 repeat attempts whose Lane1/Lane2 semantics "
            "are unresolved remain explicitly unresolved."
        ),

        (
            "2022 and 2024 are isolated as validation-only rows."
        ),

        (
            "The Fused model will share physical, performance, "
            "thermal and stochastic layers while applying "
            "regime-specific feasible-action masks."
        ),
    ],

    "next_phase":
        (
            "Construct Day1-only, Last-Chance-only and Fused "
            "simulation/model specifications using the canonical "
            "decision interface."
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
print("=" * 124)
print("FUSED DATASET SUMMARY")
print("=" * 124)

print(
    f"Rows: "
    f"{len(rows)}"
)

print(
    f"Day1: "
    f"{len(day1_rows)}"
)

print(
    f"Last Chance: "
    f"{len(lc_rows)}"
)

print(
    "Resolved actions: "
    f"{sum(bool(r['action_resolved']) for r in rows)}"
)

print(
    "Unresolved actions: "
    f"{sum(not bool(r['action_resolved']) for r in rows)}"
)

print(
    "Policy-fit behaviour rows: "
    f"{sum(bool(r['safe_for_policy_fit']) for r in rows)}"
)


print()
print("=" * 124)
print("REGIME / YEAR SUMMARY")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['session_regime']:12s} | "
        f"{r['year']} | "
        f"rows={r['rows']:3d} | "
        f"resolved={r['resolved_action_rows']:3d} | "
        f"unresolved={r['unresolved_action_rows']:3d} | "
        f"numeric={r['numeric_state_rows']:3d} | "
        f"fit={r['policy_fit_rows']:3d} | "
        f"validation={r['validation_rows']:3d}"
    )


print()
print("=" * 124)
print("ACTION COUNTS BY REGIME")
print("=" * 124)

for regime in [
    "DAY1",
    "LAST_CHANCE",
]:

    subset = [
        r
        for r in rows
        if r[
            "session_regime"
        ] == regime
    ]

    counts = Counter(
        r[
            "observed_action"
        ]
        for r in subset
    )

    print()
    print(regime)

    for action, count in sorted(
        counts.items()
    ):

        print(
            f"  {action:40s} | "
            f"{count}"
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
    OUT_DATASET.relative_to(ROOT)
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
    "R4F2_CANONICAL_FUSED_DECISION_DATASET_READY"
)
