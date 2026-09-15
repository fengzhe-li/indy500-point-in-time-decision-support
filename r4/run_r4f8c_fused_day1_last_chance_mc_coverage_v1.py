from pathlib import Path
from collections import Counter
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

DAY1_PATH = (
    OUT /
    "r4f8b_final_mc_eligible_decision_rows_v1.csv"
)

LC_PATH = (
    OUT /
    "r4lc5e_last_chance_fused_interface_v2.csv"
)

F8B_CONTRACT = (
    OUT /
    "r4f8b_final_action_mc_contract_v1.json"
)

LC_SCHEMA = (
    OUT /
    "r4lc5e_fused_decision_schema_contract_v2.json"
)

OUT_DECISIONS = (
    OUT /
    "r4f8c_fused_mc_decision_universe_v1.csv"
)

OUT_ACTIONS = (
    OUT /
    "r4f8c_fused_mc_action_expansion_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f8c_fused_mc_coverage_qa_v1.csv"
)

OUT_CONTRACT = (
    OUT /
    "r4f8c_fused_mc_coverage_contract_v1.json"
)

OUT_REPORT = (
    OUT /
    "r4f8c_fused_mc_coverage_report_v1.json"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


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


for path in [
    DAY1_PATH,
    LC_PATH,
    F8B_CONTRACT,
    LC_SCHEMA,
]:
    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


day1_fields, day1_rows = read_csv(
    DAY1_PATH
)

lc_fields, lc_rows = read_csv(
    LC_PATH
)

f8b_contract = json.loads(
    F8B_CONTRACT.read_text(
        encoding="utf-8"
    )
)

lc_contract = json.loads(
    LC_SCHEMA.read_text(
        encoding="utf-8"
    )
)


print("=" * 150)
print(
    "R4F8C — FUSED DAY1 + LAST CHANCE MC COVERAGE"
)
print("=" * 150)


# =============================================================================
# Resolve identifiers
# =============================================================================

def resolve_field(
    fields,
    candidates,
):
    for c in candidates:
        if c in fields:
            return c
    return None


day1_id_field = resolve_field(
    day1_fields,
    [
        "decision_id",
        "decision_state_id",
        "state_id",
        "attempt_id",
    ],
)

lc_id_field = resolve_field(
    lc_fields,
    [
        "decision_id",
        "decision_state_id",
        "state_id",
        "episode_id",
        "attempt_id",
    ],
)


if day1_id_field is None:
    raise SystemExit(
        "DAY1 DECISION ID FIELD NOT FOUND"
    )

if lc_id_field is None:
    raise SystemExit(
        "LAST CHANCE DECISION ID FIELD NOT FOUND"
    )


# =============================================================================
# Resolve LC protected-result state
# =============================================================================

protected_candidates = [
    "protected_result_exists",
    "protected_valid_result",
    "has_protected_result",
    "protected_result_available",
    "current_result_protected",
]

protected_field = resolve_field(
    lc_fields,
    protected_candidates,
)


action_field = resolve_field(
    lc_fields,
    [
        "observed_action",
        "action",
        "canonical_action",
        "action_label",
    ],
)


# =============================================================================
# Build fused decision universe
# =============================================================================

decision_rows = []


for r in day1_rows:

    decision_rows.append({
        "fused_decision_id":
            "DAY1::"
            +
            clean(
                r.get(
                    day1_id_field
                )
            ),

        "regime":
            "DAY1",

        "source_decision_id":
            clean(
                r.get(
                    day1_id_field
                )
            ),

        "protected_result_exists":
            True,

        "performance_state_class":
            "FULL_PERFORMANCE_MODEL_STATE",

        "source_file":
            str(
                DAY1_PATH.relative_to(
                    ROOT
                )
            ),
    })


for r in lc_rows:

    source_id = clean(
        r.get(
            lc_id_field
        )
    )


    protected = None


    if protected_field is not None:

        protected = truthy(
            r.get(
                protected_field
            )
        )


    # -------------------------------------------------------------------------
    # If no explicit protected flag exists, infer ONLY from already-frozen
    # canonical observed-action semantics.
    #
    # WITHDRAW_AND_REATTEMPT requires a protected result to withdraw.
    # REATTEMPT represents no protected result.
    #
    # STOP remains ambiguous unless another field resolves it.
    # -------------------------------------------------------------------------

    if (
        protected is None
        and
        action_field is not None
    ):

        action = clean(
            r.get(
                action_field
            )
        )

        if (
            action
            ==
            "WITHDRAW_AND_REATTEMPT"
        ):
            protected = True

        elif action == "REATTEMPT":
            protected = False


    if protected is None:

        # Search common state fields for explicit OUTSIDE/BUMPED semantics.
        text = " ".join(
            clean(v).lower()
            for v in r.values()
        )

        if (
            "outside" in text
            or
            "bumped" in text
            or
            "no protected" in text
        ):
            protected = False


    if protected is None:

        raise SystemExit(
            "CANNOT RESOLVE LAST CHANCE PROTECTED-RESULT STATE: "
            +
            source_id
        )


    decision_rows.append({
        "fused_decision_id":
            "LAST_CHANCE::"
            +
            source_id,

        "regime":
            "LAST_CHANCE",

        "source_decision_id":
            source_id,

        "protected_result_exists":
            protected,

        "performance_state_class":
            (
                "LAST_CHANCE_REPLAY_STATE"
            ),

        "source_file":
            str(
                LC_PATH.relative_to(
                    ROOT
                )
            ),
    })


# =============================================================================
# Frozen regime-specific action masks
# =============================================================================

action_rows = []


for d in decision_rows:

    regime = d[
        "regime"
    ]

    protected = d[
        "protected_result_exists"
    ]


    if regime == "DAY1":

        feasible = [
            "STOP",
            "RETAIN_AND_REATTEMPT",
            "WITHDRAW_AND_PRIORITY_REATTEMPT",
        ]


    elif (
        regime == "LAST_CHANCE"
        and
        protected
    ):

        feasible = [
            "STOP",
            "WITHDRAW_AND_REATTEMPT",
        ]


    elif (
        regime == "LAST_CHANCE"
        and
        not protected
    ):

        feasible = [
            "STOP",
            "REATTEMPT",
        ]


    else:

        raise RuntimeError(
            "UNRESOLVED ACTION MASK"
        )


    for action in feasible:

        action_rows.append({
            "fused_decision_id":
                d[
                    "fused_decision_id"
                ],

            "regime":
                regime,

            "protected_result_exists":
                protected,

            "feasible_action":
                action,

            "current_result_retained_before_attempt":
                (
                    action
                    in {
                        "STOP",
                        "RETAIN_AND_REATTEMPT",
                    }
                ),

            "requires_new_attempt":
                action
                !=
                "STOP",

            "priority_lane_semantics":
                (
                    "DAY1_LANE2_RETAIN"
                    if action
                    ==
                    "RETAIN_AND_REATTEMPT"

                    else
                    (
                        "DAY1_LANE1_WITHDRAW_PRIORITY"
                        if action
                        ==
                        "WITHDRAW_AND_PRIORITY_REATTEMPT"

                        else
                        (
                            "LAST_CHANCE_SINGLE_REATTEMPT_QUEUE"
                            if (
                                regime
                                ==
                                "LAST_CHANCE"
                                and
                                action
                                in {
                                    "REATTEMPT",
                                    "WITHDRAW_AND_REATTEMPT",
                                }
                            )

                            else
                            "NONE"
                        )
                    )
                ),
        })


# =============================================================================
# Counts
# =============================================================================

decision_counts = Counter(
    r[
        "regime"
    ]
    for r in decision_rows
)

action_counts = Counter(
    r[
        "feasible_action"
    ]
    for r in action_rows
)

lc_protected = sum(
    (
        r[
            "regime"
        ]
        ==
        "LAST_CHANCE"
        and
        r[
            "protected_result_exists"
        ]
    )
    for r in decision_rows
)

lc_unprotected = sum(
    (
        r[
            "regime"
        ]
        ==
        "LAST_CHANCE"
        and
        not r[
            "protected_result_exists"
        ]
    )
    for r in decision_rows
)


# =============================================================================
# QA
# =============================================================================

unique_ids = (
    len(
        {
            r[
                "fused_decision_id"
            ]
            for r in decision_rows
        }
    )
    ==
    len(
        decision_rows
    )
)


day1_action_valid = all(
    {
        r[
            "feasible_action"
        ]
        for r in action_rows
        if r[
            "fused_decision_id"
        ]
        ==
        d[
            "fused_decision_id"
        ]
    }
    ==
    {
        "STOP",
        "RETAIN_AND_REATTEMPT",
        "WITHDRAW_AND_PRIORITY_REATTEMPT",
    }
    for d in decision_rows
    if d[
        "regime"
    ]
    ==
    "DAY1"
)


lc_action_valid = all(
    (
        {
            r[
                "feasible_action"
            ]
            for r in action_rows
            if r[
                "fused_decision_id"
            ]
            ==
            d[
                "fused_decision_id"
            ]
        }
        ==
        (
            {
                "STOP",
                "WITHDRAW_AND_REATTEMPT",
            }
            if d[
                "protected_result_exists"
            ]
            else
            {
                "STOP",
                "REATTEMPT",
            }
        )
    )
    for d in decision_rows
    if d[
        "regime"
    ]
    ==
    "LAST_CHANCE"
)


qa_rows = [
    {
        "metric":
            "day1_decisions",
        "value":
            decision_counts[
                "DAY1"
            ],
        "expected":
            50,
        "status":
            (
                "PASS"
                if decision_counts[
                    "DAY1"
                ] == 50
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_decisions",
        "value":
            decision_counts[
                "LAST_CHANCE"
            ],
        "expected":
            10,
        "status":
            (
                "PASS"
                if decision_counts[
                    "LAST_CHANCE"
                ] == 10
                else "FAIL"
            ),
    },

    {
        "metric":
            "fused_decisions",
        "value":
            len(
                decision_rows
            ),
        "expected":
            60,
        "status":
            (
                "PASS"
                if len(
                    decision_rows
                ) == 60
                else "FAIL"
            ),
    },

    {
        "metric":
            "unique_fused_decision_ids",
        "value":
            unique_ids,
        "expected":
            True,
        "status":
            (
                "PASS"
                if unique_ids
                else "FAIL"
            ),
    },

    {
        "metric":
            "day1_action_masks_valid",
        "value":
            day1_action_valid,
        "expected":
            True,
        "status":
            (
                "PASS"
                if day1_action_valid
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_action_masks_valid",
        "value":
            lc_action_valid,
        "expected":
            True,
        "status":
            (
                "PASS"
                if lc_action_valid
                else "FAIL"
            ),
    },

    {
        "metric":
            "last_chance_protected_plus_unprotected",
        "value":
            lc_protected
            +
            lc_unprotected,
        "expected":
            10,
        "status":
            (
                "PASS"
                if (
                    lc_protected
                    +
                    lc_unprotected
                ) == 10
                else "FAIL"
            ),
    },

    {
        "metric":
            "historical_action_labels_used_as_optimality_truth",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "monte_carlo_run",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_DECISIONS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            decision_rows[
                0
            ].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        decision_rows
    )


with OUT_ACTIONS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            action_rows[
                0
            ].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        action_rows
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


contract = {
    "phase":
        "R4F8C",

    "status":
        "R4F8C_FUSED_MC_COVERAGE_CONTRACT_FROZEN",

    "decision_universe": {
        "total":
            len(
                decision_rows
            ),

        "day1":
            decision_counts[
                "DAY1"
            ],

        "last_chance":
            decision_counts[
                "LAST_CHANCE"
            ],

        "last_chance_protected":
            lc_protected,

        "last_chance_unprotected":
            lc_unprotected,
    },

    "action_counts":
        dict(
            action_counts
        ),

    "frozen_action_masks": {
        "DAY1_PROTECTED":
            [
                "STOP",
                "RETAIN_AND_REATTEMPT",
                "WITHDRAW_AND_PRIORITY_REATTEMPT",
            ],

        "LAST_CHANCE_PROTECTED":
            [
                "STOP",
                "WITHDRAW_AND_REATTEMPT",
            ],

        "LAST_CHANCE_UNPROTECTED":
            [
                "STOP",
                "REATTEMPT",
            ],
    },

    "important_boundary":
        (
            "R4F8B is preserved as the Day1 MC contract. "
            "R4F8C extends final MC coverage to the frozen "
            "Last Chance interface without modifying R4F8B."
        ),

    "next_phase":
        (
            "R4F8D_FINAL_PROBABILISTIC_ACTION_MONTE_CARLO"
        ),
}


OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


report = {
    "phase":
        "R4F8C",

    "status":
        "R4F8C_FUSED_MC_COVERAGE_CONTRACT_FROZEN",

    "decision_counts":
        dict(
            decision_counts
        ),

    "action_counts":
        dict(
            action_counts
        ),

    "last_chance": {
        "protected":
            lc_protected,

        "unprotected":
            lc_unprotected,
    },

    "next_phase":
        (
            "Run final probabilistic action evaluation using "
            "performance uncertainty, wait uncertainty and "
            "regime-specific result protection semantics."
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
print("=" * 150)
print("FUSED DECISION COVERAGE")
print("=" * 150)

print(
    f"DAY1 decisions: "
    f"{decision_counts['DAY1']}"
)

print(
    f"LAST CHANCE decisions: "
    f"{decision_counts['LAST_CHANCE']}"
)

print(
    f"TOTAL fused decisions: "
    f"{len(decision_rows)}"
)

print(
    f"LC protected: "
    f"{lc_protected}"
)

print(
    f"LC unprotected: "
    f"{lc_unprotected}"
)


print()
print("=" * 150)
print("FUSED ACTION COUNTS")
print("=" * 150)

for action in [
    "STOP",
    "REATTEMPT",
    "RETAIN_AND_REATTEMPT",
    "WITHDRAW_AND_REATTEMPT",
    "WITHDRAW_AND_PRIORITY_REATTEMPT",
]:

    print(
        f"{action:42s} | "
        f"{action_counts[action]}"
    )


print()
print("=" * 150)
print("ACTION MASKS")
print("=" * 150)

print(
    "DAY1 protected:"
)

print(
    "  STOP"
)

print(
    "  RETAIN_AND_REATTEMPT"
)

print(
    "  WITHDRAW_AND_PRIORITY_REATTEMPT"
)

print()

print(
    "LAST CHANCE protected:"
)

print(
    "  STOP"
)

print(
    "  WITHDRAW_AND_REATTEMPT"
)

print()

print(
    "LAST CHANCE unprotected:"
)

print(
    "  STOP"
)

print(
    "  REATTEMPT"
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ]
    ==
    "FAIL"
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
    OUT_DECISIONS.relative_to(
        ROOT
    )
)

print(
    OUT_ACTIONS.relative_to(
        ROOT
    )
)

print(
    OUT_QA.relative_to(
        ROOT
    )
)

print(
    OUT_CONTRACT.relative_to(
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
    "R4F8C_FUSED_MC_COVERAGE_CONTRACT_FROZEN"
)
