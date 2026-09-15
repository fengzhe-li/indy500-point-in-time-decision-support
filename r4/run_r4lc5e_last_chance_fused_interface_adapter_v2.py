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
    "r4lc5e_last_chance_fused_interface_v2.csv"
)

OUT_SCHEMA = (
    OUT /
    "r4lc5e_fused_decision_schema_contract_v2.json"
)

OUT_SUMMARY = (
    OUT /
    "r4lc5e_last_chance_fused_interface_summary_v2.csv"
)

OUT_QA = (
    OUT /
    "r4lc5e_last_chance_fused_interface_qa_v2.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc5e_last_chance_fused_interface_report_v2.json"
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
print("R4LC5E-v2 — LAST CHANCE → FUSED ACTION SEMANTICS CORRECTION")
print("=" * 120)

print(
    f"Input decision opportunities: "
    f"{len(source_rows)}"
)


# =============================================================================
# FINAL unified action vocabulary
# =============================================================================

STOP = "STOP"

REATTEMPT = "REATTEMPT"

RETAIN_AND_REATTEMPT = (
    "RETAIN_AND_REATTEMPT"
)

WITHDRAW_AND_REATTEMPT = (
    "WITHDRAW_AND_REATTEMPT"
)

WITHDRAW_AND_PRIORITY_REATTEMPT = (
    "WITHDRAW_AND_PRIORITY_REATTEMPT"
)

ALL_ACTIONS = [
    STOP,
    REATTEMPT,
    RETAIN_AND_REATTEMPT,
    WITHDRAW_AND_REATTEMPT,
    WITHDRAW_AND_PRIORITY_REATTEMPT,
]


# =============================================================================
# Frozen fused action/schema contract
# =============================================================================

schema_contract = {
    "schema_name":
        "FUSED_INDYCAR_QUALIFYING_DECISION_STATE_V2",

    "schema_status":
        "ACTION_SEMANTICS_FROZEN",

    "action_vocabulary":
        ALL_ACTIONS,

    "action_definitions": {
        "STOP":
            (
                "Do not make another qualifying attempt."
            ),

        "REATTEMPT":
            (
                "Make another attempt when there is no currently "
                "protected valid result that must be retained or withdrawn."
            ),

        "RETAIN_AND_REATTEMPT":
            (
                "Retain the current valid result while entering "
                "a non-priority reattempt path."
            ),

        "WITHDRAW_AND_REATTEMPT":
            (
                "Withdraw the currently protected valid result "
                "before making another attempt."
            ),

        "WITHDRAW_AND_PRIORITY_REATTEMPT":
            (
                "Withdraw the current result and enter the "
                "priority reattempt path."
            ),
    },

    "feasible_action_rules": {
        "DAY1_WITH_VALID_RESULT": [
            STOP,
            RETAIN_AND_REATTEMPT,
            WITHDRAW_AND_PRIORITY_REATTEMPT,
        ],

        "LAST_CHANCE_WITH_VALID_RESULT": [
            STOP,
            WITHDRAW_AND_REATTEMPT,
        ],

        "LAST_CHANCE_WITHOUT_VALID_RESULT": [
            STOP,
            REATTEMPT,
        ],
    },

    "shared_features": [
        "decision_id",
        "year",
        "session_regime",
        "car_number",
        "driver_name",
        "decision_stage",
        "qualification_state",
        "current_rank",
        "current_result_mph",
        "benchmark_type",
        "benchmark_speed_mph",
        "margin_to_benchmark_mph",
        "has_protected_result",
        "time_remaining_seconds",
        "time_quality",
        "thermal_state_available",
        "performance_uncertainty_available",
        "wait_model_available",
    ],

    "critical_rule":
        (
            "REATTEMPT and WITHDRAW_AND_REATTEMPT must remain "
            "distinct. A car already outside the field with no "
            "protected result cannot be labelled as withdrawing "
            "a result before reattempting."
        ),
}


# =============================================================================
# Convert Last Chance rows
# =============================================================================

rows = []

for r in source_rows:

    decision_id = clean(
        r.get("decision_id")
    )

    year = int(
        clean(
            r.get("year")
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
            "AFTER_BUMP",
        ]
    )

    observed_raw = clean(
        r.get(
            "observed_action"
        )
    )


    # =========================================================================
    # Correct action semantics
    # =========================================================================

    if observed_raw == "STOP":

        observed_action = STOP

    elif (
        observed_raw == "REATTEMPT"
        and has_protected_result
    ):

        observed_action = (
            WITHDRAW_AND_REATTEMPT
        )

    elif (
        observed_raw == "REATTEMPT"
        and not has_protected_result
    ):

        observed_action = (
            REATTEMPT
        )

    else:

        observed_action = (
            "UNKNOWN"
        )


    # =========================================================================
    # Feasible action mask
    # =========================================================================

    mask_stop = True

    if has_protected_result:

        mask_reattempt = False
        mask_retain = False
        mask_withdraw = True
        mask_priority = False

        feasible_action_set = (
            "STOP|WITHDRAW_AND_REATTEMPT"
        )

    else:

        mask_reattempt = True
        mask_retain = False
        mask_withdraw = False
        mask_priority = False

        feasible_action_set = (
            "STOP|REATTEMPT"
        )


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
            clean(
                r.get(
                    "current_rank_within_last_chance"
                )
            ),

        "current_result_mph":
            (
                f"{current_speed:.6f}"
                if current_speed is not None
                else ""
            ),

        "benchmark_type":
            "LAST_CHANCE_SURVIVAL_BUBBLE",

        "benchmark_speed_mph":
            (
                f"{bubble_speed:.6f}"
                if bubble_speed is not None
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

        "action_semantics_regime":
            "LAST_CHANCE",

        "feasible_action_set":
            feasible_action_set,

        "action_mask_STOP":
            mask_stop,

        "action_mask_REATTEMPT":
            mask_reattempt,

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

        "withdrawal_required_for_observed_action":
            (
                observed_action
                == WITHDRAW_AND_REATTEMPT
            ),

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
                "EXACT"
                if clean(
                    r.get(
                        "exact_session_remaining_seconds"
                    )
                )
                else "UNKNOWN"
            ),

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

unknown_actions = [
    r
    for r in rows
    if r[
        "observed_action_unified"
    ] == "UNKNOWN"
]

bad_outside_withdraw = [
    r
    for r in rows
    if (
        not r[
            "has_protected_result"
        ]
        and
        r[
            "observed_action_unified"
        ]
        == WITHDRAW_AND_REATTEMPT
    )
]

bad_protected_plain_reattempt = [
    r
    for r in rows
    if (
        r[
            "has_protected_result"
        ]
        and
        r[
            "observed_action_unified"
        ]
        == REATTEMPT
    )
]

bad_masks = []

for r in rows:

    if r[
        "has_protected_result"
    ]:

        expected = {
            "STOP": True,
            "REATTEMPT": False,
            "RETAIN": False,
            "WITHDRAW": True,
            "PRIORITY": False,
        }

    else:

        expected = {
            "STOP": True,
            "REATTEMPT": True,
            "RETAIN": False,
            "WITHDRAW": False,
            "PRIORITY": False,
        }

    actual = {
        "STOP":
            r[
                "action_mask_STOP"
            ],

        "REATTEMPT":
            r[
                "action_mask_REATTEMPT"
            ],

        "RETAIN":
            r[
                "action_mask_RETAIN_AND_REATTEMPT"
            ],

        "WITHDRAW":
            r[
                "action_mask_WITHDRAW_AND_REATTEMPT"
            ],

        "PRIORITY":
            r[
                "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
            ],
    }

    if actual != expected:

        bad_masks.append(
            r["decision_id"]
        )


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
            "no_unknown_actions",

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
            "outside_field_never_labelled_withdraw",

        "value":
            len(
                bad_outside_withdraw
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not bad_outside_withdraw
                else "FAIL"
            ),
    },

    {
        "metric":
            "protected_result_never_plain_reattempt",

        "value":
            len(
                bad_protected_plain_reattempt
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not bad_protected_plain_reattempt
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_action_masks_valid",

        "value":
            len(
                bad_masks
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not bad_masks
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_never_uses_retain",

        "value":
            sum(
                bool(
                    r[
                        "action_mask_RETAIN_AND_REATTEMPT"
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
                    not r[
                        "action_mask_RETAIN_AND_REATTEMPT"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_never_uses_priority",

        "value":
            sum(
                bool(
                    r[
                        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
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
                    not r[
                        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "shared_layers_still_unlinked",

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
# Summary
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

        "STOP":
            sum(
                r[
                    "observed_action_unified"
                ] == STOP
                for r in subset
            ),

        "REATTEMPT":
            sum(
                r[
                    "observed_action_unified"
                ] == REATTEMPT
                for r in subset
            ),

        "WITHDRAW_AND_REATTEMPT":
            sum(
                r[
                    "observed_action_unified"
                ]
                == WITHDRAW_AND_REATTEMPT
                for r in subset
            ),

        "protected_rows":
            sum(
                bool(
                    r[
                        "has_protected_result"
                    ]
                )
                for r in subset
            ),

        "outside_rows":
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
        "R4LC5E_V2",

    "status":
        "R4LC5E_V2_LAST_CHANCE_FUSED_ACTION_SEMANTICS_FROZEN",

    "rows":
        len(rows),

    "action_counts":
        dict(
            action_counts
        ),

    "semantic_fix":
        (
            "Cars without a protected qualifying result are now "
            "labelled REATTEMPT rather than WITHDRAW_AND_REATTEMPT."
        ),

    "next_phase":
        (
            "Build Day1 adapter against the frozen V2 fused schema."
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
print("CORRECTED ACTION COUNTS")

for action in ALL_ACTIONS:

    print(
        f"{action:36s} | "
        f"{action_counts.get(action, 0)}"
    )


print()
print("YEAR SUMMARY")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"rows={r['rows']} | "
        f"STOP={r['STOP']} | "
        f"REATTEMPT={r['REATTEMPT']} | "
        f"WITHDRAW={r['WITHDRAW_AND_REATTEMPT']} | "
        f"protected={r['protected_rows']} | "
        f"outside={r['outside_rows']} | "
        f"policy_fit={r['policy_fit_rows']}"
    )


print()
print("CORRECTED FUSED INTERFACE")

for r in rows:

    print(
        f"{r['decision_id']} | "
        f"protected={r['has_protected_result']} | "
        f"feasible={r['feasible_action_set']} | "
        f"observed={r['observed_action_unified']}"
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
    "R4LC5E_V2_LAST_CHANCE_FUSED_ACTION_SEMANTICS_FROZEN"
)
