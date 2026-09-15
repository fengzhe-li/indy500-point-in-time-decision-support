from pathlib import Path
import csv
import json
import math
from collections import Counter

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

INPUT = (
    OUT /
    "r4lc5d_last_chance_decision_opportunity_panel_v1.csv"
)

OUT_PANEL = (
    OUT /
    "r4lc5e_last_chance_fused_interface_v1.csv"
)

OUT_SCHEMA = (
    OUT /
    "r4lc5e_fused_decision_schema_contract_v1.json"
)

OUT_SUMMARY = (
    OUT /
    "r4lc5e_last_chance_fused_interface_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc5e_last_chance_fused_interface_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc5e_last_chance_fused_interface_report_v1.json"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


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


def truth(v):
    return clean(v).lower() in {
        "true",
        "1",
        "yes",
    }


if not INPUT.exists():
    raise SystemExit(
        f"MISSING INPUT: {INPUT}"
    )


with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    source_rows = list(
        csv.DictReader(f)
    )


print("=" * 120)
print("R4LC5E — LAST CHANCE → FUSED MODEL INTERFACE ADAPTER")
print("=" * 120)

print(
    f"Input decision opportunities: "
    f"{len(source_rows)}"
)


# =============================================================================
# Unified action vocabulary
# =============================================================================

ACTION_STOP = "STOP"

ACTION_RETAIN_REATTEMPT = (
    "RETAIN_AND_REATTEMPT"
)

ACTION_WITHDRAW_REATTEMPT = (
    "WITHDRAW_AND_REATTEMPT"
)

ACTION_PRIORITY_REATTEMPT = (
    "WITHDRAW_AND_PRIORITY_REATTEMPT"
)

ALL_ACTIONS = [
    ACTION_STOP,
    ACTION_RETAIN_REATTEMPT,
    ACTION_WITHDRAW_REATTEMPT,
    ACTION_PRIORITY_REATTEMPT,
]


# =============================================================================
# Unified schema
# =============================================================================

schema_contract = {
    "schema_name":
        "FUSED_INDYCAR_QUALIFYING_DECISION_STATE_V1",

    "purpose":
        (
            "Shared decision-state interface for Day 1 and "
            "Last Chance models."
        ),

    "shared_features": [
        "decision_id",
        "year",
        "session_regime",
        "car_number",
        "driver_name",
        "current_result_mph",
        "benchmark_speed_mph",
        "margin_to_benchmark_mph",
        "current_rank",
        "qualification_state",
        "decision_stage",
        "time_remaining_seconds",
        "time_quality",
        "thermal_state_available",
        "performance_uncertainty_available",
        "wait_model_available",
    ],

    "regime_specific_features": [
        "benchmark_type",
        "action_semantics_regime",
    ],

    "action_vocabulary":
        ALL_ACTIONS,

    "day1_action_semantics": {
        "STOP":
            "Keep current result and do not reattempt.",

        "RETAIN_AND_REATTEMPT":
            (
                "Enter non-priority reattempt path while "
                "retaining current result."
            ),

        "WITHDRAW_AND_PRIORITY_REATTEMPT":
            (
                "Withdraw current result and take priority "
                "reattempt path."
            ),
    },

    "last_chance_action_semantics": {
        "STOP":
            "Do not make another Last Chance attempt.",

        "WITHDRAW_AND_REATTEMPT":
            (
                "If a valid qualifying result is currently held, "
                "withdraw it before making another attempt."
            ),

        "REATTEMPT_WITHOUT_HELD_RESULT":
            (
                "If currently outside the field without a protected "
                "qualifying result, make another attempt."
            ),
    },

    "important_constraint":
        (
            "Unified vocabulary does not imply identical feasible "
            "actions across regimes. Feasible-action masks must be "
            "applied before strategy evaluation."
        ),
}


# =============================================================================
# Convert Last Chance opportunities
# =============================================================================

rows = []

for r in source_rows:

    decision_id = clean(
        r.get(
            "decision_id"
        )
    )

    year = int(
        clean(
            r.get(
                "year"
            )
        )
    )

    current_speed = num(
        r.get(
            "current_speed_mph"
        )
    )

    bubble_speed = num(
        r.get(
            "bubble_speed_mph"
        )
    )

    margin = None

    if (
        current_speed is not None
        and bubble_speed is not None
    ):
        margin = (
            current_speed
            - bubble_speed
        )

    qualification_state = clean(
        r.get(
            "qualification_state"
        )
    )

    observed_raw = clean(
        r.get(
            "observed_action"
        )
    )

    feasible_raw = clean(
        r.get(
            "feasible_actions"
        )
    )


    # =========================================================================
    # Determine whether a qualifying result is currently being protected
    # =========================================================================

    state_upper = (
        qualification_state.upper()
    )

    has_protected_result = any(
        token in state_upper
        for token in [
            "PROVISIONALLY_QUALIFIED",
            "PROVISIONALLY_ON_BUBBLE",
        ]
    )

    outside_field = any(
        token in state_upper
        for token in [
            "OUTSIDE_FIELD",
            "OUTSIDE FIELD",
            "AFTER_BUMP",
        ]
    )


    # =========================================================================
    # Unified observed action
    #
    # Last Chance REATTEMPT has two distinct meanings:
    #
    # - if holding a valid protected result:
    #       WITHDRAW_AND_REATTEMPT
    #
    # - if outside field / no protected result:
    #       REATTEMPT with no result to protect
    #
    # The second case is represented using WITHDRAW_AND_REATTEMPT = False
    # plus action_context.
    # =========================================================================

    if observed_raw == "STOP":

        observed_action = (
            ACTION_STOP
        )

        action_context = (
            "STOP_CURRENT_STATE"
        )

    elif (
        observed_raw == "REATTEMPT"
        and has_protected_result
    ):

        observed_action = (
            ACTION_WITHDRAW_REATTEMPT
        )

        action_context = (
            "REATTEMPT_FROM_PROTECTED_RESULT"
        )

    elif observed_raw == "REATTEMPT":

        observed_action = (
            ACTION_WITHDRAW_REATTEMPT
        )

        action_context = (
            "REATTEMPT_WITHOUT_PROTECTED_RESULT"
        )

    else:

        observed_action = (
            "UNKNOWN"
        )

        action_context = (
            "UNKNOWN"
        )


    # =========================================================================
    # Feasible action mask
    # =========================================================================

    mask_stop = True

    mask_retain = False

    mask_withdraw = True

    mask_priority = False


    # Last Chance does not use the Day-1 retain/Lane2 action.
    #
    # If there is no protected result, the unified "withdraw" action
    # represents the reattempt branch but no actual deletion is required.
    withdrawal_required = (
        has_protected_result
    )


    # =========================================================================
    # Benchmark semantics
    # =========================================================================

    benchmark_type = (
        "LAST_CHANCE_SURVIVAL_BUBBLE"
    )

    benchmark_speed = (
        bubble_speed
    )


    # =========================================================================
    # Current rank
    # =========================================================================

    rank = clean(
        r.get(
            "current_rank_within_last_chance"
        )
    )


    # =========================================================================
    # Build unified row
    # =========================================================================

    row = {
        "decision_id":
            decision_id,

        "year":
            year,

        "session_regime":
            "LAST_CHANCE",

        "source_session_regime":
            clean(
                r.get(
                    "session_regime"
                )
            ),

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

        "qualification_state":
            qualification_state,

        "current_rank":
            rank,

        "current_result_mph":
            (
                f"{current_speed:.6f}"
                if current_speed is not None
                else ""
            ),

        "benchmark_type":
            benchmark_type,

        "benchmark_speed_mph":
            (
                f"{benchmark_speed:.6f}"
                if benchmark_speed is not None
                else ""
            ),

        "margin_to_benchmark_mph":
            (
                f"{margin:.6f}"
                if margin is not None
                else ""
            ),

        "has_protected_result":
            has_protected_result,

        "outside_field":
            outside_field,

        "withdrawal_required_for_reattempt":
            withdrawal_required,

        "action_semantics_regime":
            "LAST_CHANCE",

        "action_mask_STOP":
            mask_stop,

        "action_mask_RETAIN_AND_REATTEMPT":
            mask_retain,

        "action_mask_WITHDRAW_AND_REATTEMPT":
            mask_withdraw,

        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT":
            mask_priority,

        "observed_action_raw":
            observed_raw,

        "observed_action_unified":
            observed_action,

        "observed_action_context":
            action_context,

        "outcome":
            clean(
                r.get(
                    "outcome"
                )
            ),

        "state_quality":
            clean(
                r.get(
                    "state_quality"
                )
            ),

        "action_quality":
            clean(
                r.get(
                    "action_quality"
                )
            ),

        "safe_for_policy_fit":
            truth(
                r.get(
                    "safe_for_policy_fit"
                )
            ),

        "exact_timestamp":
            clean(
                r.get(
                    "exact_timestamp"
                )
            ),

        "time_remaining_seconds":
            clean(
                r.get(
                    "exact_session_remaining_seconds"
                )
            ),

        "time_quality":
            (
                "UNKNOWN"
                if not clean(
                    r.get(
                        "exact_session_remaining_seconds"
                    )
                )
                else "EXACT"
            ),

        # Hooks for shared Fused-model layers.
        "thermal_state_available":
            False,

        "performance_uncertainty_available":
            False,

        "wait_model_available":
            False,

        "shared_feature_link_status":
            "PENDING",

        "evidence_role":
            clean(
                r.get(
                    "evidence_role"
                )
            ),

        "note":
            clean(
                r.get(
                    "note"
                )
            ),
    }

    rows.append(
        row
    )


# =============================================================================
# QA
# =============================================================================

action_counts = Counter(
    r[
        "observed_action_unified"
    ]
    for r in rows
)

policy_rows = [
    r
    for r in rows
    if r[
        "safe_for_policy_fit"
    ]
]

numeric_rows = [
    r
    for r in rows
    if (
        r[
            "current_result_mph"
        ]
        and
        r[
            "benchmark_speed_mph"
        ]
    )
]

illegal_retain = [
    r
    for r in rows
    if r[
        "action_mask_RETAIN_AND_REATTEMPT"
    ]
]

illegal_priority = [
    r
    for r in rows
    if r[
        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
    ]
]

missing_stop_mask = [
    r
    for r in rows
    if not r[
        "action_mask_STOP"
    ]
]

unknown_actions = [
    r
    for r in rows
    if r[
        "observed_action_unified"
    ]
    == "UNKNOWN"
]


qa_rows = [
    {
        "metric":
            "input_rows_preserved",

        "value":
            len(rows),

        "expected":
            len(source_rows),

        "status":
            (
                "PASS"
                if len(rows)
                == len(source_rows)
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_unknown_observed_actions",

        "value":
            len(
                unknown_actions
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not unknown_actions
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_retain_action_disabled",

        "value":
            len(
                illegal_retain
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not illegal_retain
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_priority_action_disabled",

        "value":
            len(
                illegal_priority
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not illegal_priority
                else "FAIL"
            ),
    },

    {
        "metric":
            "stop_always_feasible",

        "value":
            len(
                missing_stop_mask
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not missing_stop_mask
                else "FAIL"
            ),
    },

    {
        "metric":
            "action_diversity_preserved",

        "value":
            ";".join(
                sorted(
                    action_counts.keys()
                )
            ),

        "expected":
            "STOP;WITHDRAW_AND_REATTEMPT",

        "status":
            (
                "PASS"
                if set(
                    action_counts.keys()
                )
                == {
                    "STOP",
                    "WITHDRAW_AND_REATTEMPT",
                }
                else "FAIL"
            ),
    },

    {
        "metric":
            "shared_layers_not_fabricated",

        "value":
            sum(
                bool(
                    r[
                        "thermal_state_available"
                    ]
                    or
                    r[
                        "performance_uncertainty_available"
                    ]
                    or
                    r[
                        "wait_model_available"
                    ]
                )
                for r in rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not (
                        r[
                            "thermal_state_available"
                        ]
                        or
                        r[
                            "performance_uncertainty_available"
                        ]
                        or
                        r[
                            "wait_model_available"
                        ]
                    )
                    for r in rows
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Summary by year
# =============================================================================

summary_rows = []

for year in sorted(
    {
        r["year"]
        for r in rows
    }
):

    subset = [
        r
        for r in rows
        if r[
            "year"
        ] == year
    ]

    summary_rows.append({
        "year":
            year,

        "rows":
            len(
                subset
            ),

        "stop":
            sum(
                r[
                    "observed_action_unified"
                ]
                == ACTION_STOP
                for r in subset
            ),

        "reattempt":
            sum(
                r[
                    "observed_action_unified"
                ]
                == ACTION_WITHDRAW_REATTEMPT
                for r in subset
            ),

        "protected_result_rows":
            sum(
                bool(
                    r[
                        "has_protected_result"
                    ]
                )
                for r in subset
            ),

        "outside_field_rows":
            sum(
                bool(
                    r[
                        "outside_field"
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

        "numeric_state_rows":
            sum(
                bool(
                    r[
                        "current_result_mph"
                    ]
                    and
                    r[
                        "benchmark_speed_mph"
                    ]
                )
                for r in subset
            ),
    })


# =============================================================================
# Save
# =============================================================================

with OUT_PANEL.open(
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


OUT_SCHEMA.write_text(
    json.dumps(
        schema_contract,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


report = {
    "phase":
        "R4LC5E",

    "status":
        "R4LC5E_LAST_CHANCE_FUSED_INTERFACE_READY",

    "rows":
        len(
            rows
        ),

    "policy_fit_rows":
        len(
            policy_rows
        ),

    "numeric_state_rows":
        len(
            numeric_rows
        ),

    "observed_action_counts":
        dict(
            action_counts
        ),

    "shared_layer_status":
        "PENDING_LINKAGE",

    "next_phase":
        (
            "Build Day1 adapter to the same Fused schema, "
            "then create unified Day1 + Last Chance interface."
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
print("UNIFIED ACTION COUNTS")

for action in sorted(
    action_counts
):

    print(
        f"{action:32s} | "
        f"{action_counts[action]}"
    )


print()
print("YEAR SUMMARY")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"rows={r['rows']} | "
        f"STOP={r['stop']} | "
        f"REATTEMPT={r['reattempt']} | "
        f"protected={r['protected_result_rows']} | "
        f"outside={r['outside_field_rows']} | "
        f"policy_fit={r['policy_fit_rows']} | "
        f"numeric={r['numeric_state_rows']}"
    )


print()
print("FUSED INTERFACE ROWS")

for r in rows:

    print(
        f"{r['decision_id']} | "
        f"state={r['qualification_state']} | "
        f"margin="
        f"{r['margin_to_benchmark_mph'] or '-'} | "
        f"protected="
        f"{r['has_protected_result']} | "
        f"withdraw_required="
        f"{r['withdrawal_required_for_reattempt']} | "
        f"action="
        f"{r['observed_action_unified']}"
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
    OUT_PANEL.relative_to(ROOT)
)
print(
    OUT_SCHEMA.relative_to(ROOT)
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
    "R4LC5E_LAST_CHANCE_FUSED_INTERFACE_READY"
)
