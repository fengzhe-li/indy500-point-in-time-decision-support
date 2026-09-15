from pathlib import Path
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT = (
    OUT /
    "r4lc5b_last_chance_predecision_state_ledger_v1.csv"
)

OUT_GATE = (
    OUT /
    "r4lc5c_last_chance_evidence_role_gate_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4lc5c_last_chance_evidence_role_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc5c_last_chance_evidence_role_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc5c_last_chance_evidence_role_report_v1.json"
)


def clean(v):
    return (
        ""
        if v is None
        else str(v).strip()
    )


if not INPUT.exists():
    raise SystemExit(
        f"MISSING INPUT: {INPUT}"
    )


with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    rows = list(
        csv.DictReader(f)
    )


def classify(row):

    decision_id = clean(
        row.get("decision_id")
    )

    current_numeric = bool(
        clean(
            row.get(
                "current_result_mph"
            )
        )
    )

    bubble_numeric = bool(
        clean(
            row.get(
                "bubble_reference_mph"
            )
        )
    )

    action = clean(
        row.get(
            "observed_action"
        )
    )

    chronology = clean(
        row.get(
            "chronology_quality"
        )
    )

    remaining = clean(
        row.get(
            "session_remaining_status"
        )
    )

    high_value = clean(
        row.get(
            "training_role"
        )
    ).startswith(
        "HIGH_VALUE"
    )

    # ---------------------------------------------------------
    # Strict policy-fit gate
    #
    # We require:
    # 1. observable current result
    # 2. benchmark/bubble state
    # 3. time context
    # 4. clearly observed action
    # 5. enough action diversity at dataset level
    #
    # The final dataset-level action-diversity test is applied later.
    # ---------------------------------------------------------

    state_complete = (
        current_numeric
        and bubble_numeric
        and bool(remaining)
        and action not in {
            "",
            "UNKNOWN",
        }
    )

    # Even if one row has state_complete, current Last Chance
    # dataset has only REATTEMPT examples, so none are promoted
    # to policy fitting in v1.
    policy_fit = False

    if decision_id.startswith(
        "2021_"
    ):
        role = (
            "PERFORMANCE_OR_ACTION_EVIDENCE_ONLY"
        )

        reason = (
            "Repeat existence is confirmed, but numeric "
            "pre-second-attempt state and bubble state "
            "remain unresolved."
        )

    elif high_value:
        role = (
            "HISTORICAL_REPLAY_ONLY"
        )

        reason = (
            "High-value real decision episode with useful "
            "outcome/risk information, but not sufficiently "
            "complete or balanced for direct action-policy fitting."
        )

    else:
        role = (
            "HISTORICAL_REPLAY_ONLY"
        )

        reason = (
            "Sequential decision episode is partially reconstructed "
            "but lacks enough complete state and counter-action evidence "
            "for direct policy fitting."
        )

    replay_value = "HIGH" if high_value else "MEDIUM"

    if role == (
        "PERFORMANCE_OR_ACTION_EVIDENCE_ONLY"
    ):
        replay_value = "LOW"

    return {
        "evidence_role":
            role,

        "policy_fit_eligible":
            policy_fit,

        "state_complete_candidate":
            state_complete,

        "replay_value":
            replay_value,

        "gate_reason":
            reason,

        "chronology_usable":
            chronology not in {
                "",
                "UNKNOWN",
            },

        "session_time_context_present":
            bool(
                remaining
            ),

        "current_result_numeric":
            current_numeric,

        "bubble_reference_numeric":
            bubble_numeric,
    }


out_rows = []

for row in rows:

    gate = classify(
        row
    )

    merged = dict(
        row
    )

    merged.update(
        gate
    )

    out_rows.append(
        merged
    )


# =============================================================================
# Dataset-level action diversity
# =============================================================================

actions = sorted(
    {
        clean(
            r.get(
                "observed_action"
            )
        )
        for r in out_rows
        if clean(
            r.get(
                "observed_action"
            )
        )
    }
)

action_diversity_ok = (
    len(actions) >= 2
)


# =============================================================================
# Summary
# =============================================================================

roles = sorted(
    {
        r[
            "evidence_role"
        ]
        for r in out_rows
    }
)

summary_rows = []

for role in roles:

    subset = [
        r
        for r in out_rows
        if r[
            "evidence_role"
        ] == role
    ]

    summary_rows.append({
        "evidence_role":
            role,

        "rows":
            len(subset),

        "years":
            ";".join(
                str(y)
                for y in sorted(
                    {
                        int(
                            r["year"]
                        )
                        for r in subset
                    }
                )
            ),

        "high_replay_value":
            sum(
                1
                for r in subset
                if r[
                    "replay_value"
                ] == "HIGH"
            ),

        "policy_fit_eligible":
            sum(
                1
                for r in subset
                if r[
                    "policy_fit_eligible"
                ]
                in {
                    True,
                    "True",
                    "true",
                    "1",
                }
            ),
    })


# =============================================================================
# QA
# =============================================================================

policy_fit_rows = [
    r
    for r in out_rows
    if r[
        "policy_fit_eligible"
    ]
    in {
        True,
        "True",
        "true",
        "1",
    }
]

replay_rows = [
    r
    for r in out_rows
    if r[
        "evidence_role"
    ]
    == "HISTORICAL_REPLAY_ONLY"
]

evidence_only_rows = [
    r
    for r in out_rows
    if r[
        "evidence_role"
    ]
    == "PERFORMANCE_OR_ACTION_EVIDENCE_ONLY"
]


qa_rows = [
    {
        "metric":
            "input_rows_preserved",

        "value":
            len(out_rows),

        "expected":
            len(rows),

        "status":
            (
                "PASS"
                if len(out_rows)
                == len(rows)
                else "FAIL"
            ),
    },

    {
        "metric":
            "dataset_action_diversity",

        "value":
            ";".join(
                actions
            ),

        "expected":
            ">=2 distinct actions for direct policy fit",

        "status":
            (
                "WARN"
                if not action_diversity_ok
                else "PASS"
            ),
    },

    {
        "metric":
            "direct_policy_fit_rows",

        "value":
            len(
                policy_fit_rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if len(
                    policy_fit_rows
                ) == 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "historical_replay_rows",

        "value":
            len(
                replay_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if replay_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "evidence_only_rows",

        "value":
            len(
                evidence_only_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if evidence_only_rows
                else "WARN"
            ),
    },

    {
        "metric":
            "no_policy_fit_without_action_diversity",

        "value":
            len(
                policy_fit_rows
            ),

        "expected":
            0
            if not action_diversity_ok
            else "not constrained",

        "status":
            (
                "PASS"
                if (
                    action_diversity_ok
                    or
                    len(
                        policy_fit_rows
                    ) == 0
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Write
# =============================================================================

with OUT_GATE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        out_rows[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        out_rows
    )


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        summary_rows[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
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
        "R4LC5C",

    "status":
        "R4LC5C_LAST_CHANCE_EVIDENCE_ROLE_GATE_READY",

    "input_decision_episodes":
        len(
            rows
        ),

    "observed_actions":
        actions,

    "action_diversity_sufficient_for_policy_fit":
        action_diversity_ok,

    "policy_fit_eligible_rows":
        len(
            policy_fit_rows
        ),

    "historical_replay_rows":
        len(
            replay_rows
        ),

    "performance_or_action_evidence_only_rows":
        len(
            evidence_only_rows
        ),

    "methodological_decision":
        (
            "Current Last Chance evidence is not used to fit "
            "a standalone action classifier because observed "
            "decision episodes are action-imbalanced and often "
            "state-incomplete. Last Chance instead contributes "
            "regime-specific payoff/risk structure, performance "
            "evidence, and historical replay validation."
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

print("=" * 118)
print("R4LC5C — LAST CHANCE EVIDENCE ROLE GATE")
print("=" * 118)

print()
print(
    "OBSERVED ACTIONS:",
    ", ".join(
        actions
    )
    or "NONE"
)

print(
    "ACTION DIVERSITY SUFFICIENT FOR POLICY FIT:",
    action_diversity_ok
)


print()
print("ROLE SUMMARY")

for r in summary_rows:

    print(
        f"{r['evidence_role']} | "
        f"rows={r['rows']} | "
        f"years={r['years']} | "
        f"high_replay={r['high_replay_value']} | "
        f"policy_fit={r['policy_fit_eligible']}"
    )


print()
print("EPISODE GATE")

for r in out_rows:

    print(
        f"{r['decision_id']} | "
        f"role={r['evidence_role']} | "
        f"replay={r['replay_value']} | "
        f"current={r['current_result_numeric']} | "
        f"bubble={r['bubble_reference_numeric']} | "
        f"state_complete={r['state_complete_candidate']}"
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
    OUT_GATE.relative_to(ROOT)
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
    "R4LC5C_LAST_CHANCE_EVIDENCE_ROLE_GATE_READY"
)
