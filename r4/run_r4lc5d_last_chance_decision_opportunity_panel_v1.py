from pathlib import Path
import csv
import json
from collections import Counter

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_PANEL = (
    OUT /
    "r4lc5d_last_chance_decision_opportunity_panel_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4lc5d_last_chance_decision_opportunity_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc5d_last_chance_decision_opportunity_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc5d_last_chance_decision_opportunity_report_v1.json"
)


rows = []


def add(
    year,
    car,
    driver,
    decision_stage,
    current_speed,
    current_rank,
    qualification_state,
    bubble_speed,
    gap_to_bubble,
    observed_action,
    feasible_actions,
    action_quality,
    state_quality,
    outcome,
    evidence_role,
    note,
):
    rows.append({
        "decision_id":
            f"{year}_{car}_{decision_stage}",

        "year":
            year,

        "session_regime":
            (
                "LAST_ROW"
                if year == 2021
                else "LAST_CHANCE"
            ),

        "car_number":
            car,

        "driver_name":
            driver,

        "decision_stage":
            decision_stage,

        "current_speed_mph":
            (
                f"{current_speed:.3f}"
                if current_speed is not None
                else ""
            ),

        "current_rank_within_last_chance":
            (
                current_rank
                if current_rank is not None
                else ""
            ),

        "qualification_state":
            qualification_state,

        "bubble_speed_mph":
            (
                f"{bubble_speed:.3f}"
                if bubble_speed is not None
                else ""
            ),

        "gap_to_bubble_mph":
            (
                f"{gap_to_bubble:.3f}"
                if gap_to_bubble is not None
                else ""
            ),

        "observed_action":
            observed_action,

        "feasible_actions":
            feasible_actions,

        "action_quality":
            action_quality,

        "state_quality":
            state_quality,

        "exact_timestamp":
            "",

        "exact_session_remaining_seconds":
            "",

        "outcome":
            outcome,

        "evidence_role":
            evidence_role,

        "safe_for_policy_fit":
            (
                action_quality == "HIGH"
                and
                state_quality
                in {
                    "HIGH",
                    "MEDIUM",
                }
            ),

        "note":
            note,
    })


# =============================================================================
# 2021 — post guaranteed-attempt break
#
# Official first-run order:
# Karam, Power, Enerson, De Silvestro, Kimball.
#
# Known final/official valid speeds:
# Karam 229.156
# Power 228.876
# De Silvestro 228.353
#
# Enerson/Kimball each have two API records, but within-entry speed chronology
# is unresolved. Therefore their exact current first-run speed is not assigned.
#
# Observed behavior:
# Karam, Power, De Silvestro stopped.
# Enerson and Kimball each made a second attempt.
# =============================================================================

bubble_2021 = 228.353

add(
    2021,
    "24",
    "Sage Karam",
    "POST_GUARANTEED_BREAK",
    229.156,
    1,
    "PROVISIONALLY_QUALIFIED",
    bubble_2021,
    229.156 - bubble_2021,
    "STOP",
    "STOP|WITHDRAW_AND_REATTEMPT",
    "HIGH",
    "MEDIUM",
    "QUALIFIED_P31",
    "POLICY_FIT_CANDIDATE",
    (
        "Karam held one of the three qualifying positions after the "
        "guaranteed pass and did not make another attempt."
    ),
)

add(
    2021,
    "12",
    "Will Power",
    "POST_GUARANTEED_BREAK",
    228.876,
    2,
    "PROVISIONALLY_QUALIFIED",
    bubble_2021,
    228.876 - bubble_2021,
    "STOP",
    "STOP|WITHDRAW_AND_REATTEMPT",
    "HIGH",
    "MEDIUM",
    "QUALIFIED_P32",
    "POLICY_FIT_CANDIDATE",
    (
        "Power remained inside the qualifying three and did not make "
        "another Last Row attempt."
    ),
)

add(
    2021,
    "16",
    "Simona De Silvestro",
    "POST_GUARANTEED_BREAK",
    228.353,
    3,
    "PROVISIONALLY_ON_BUBBLE",
    bubble_2021,
    0.0,
    "STOP",
    "STOP|WITHDRAW_AND_REATTEMPT",
    "HIGH",
    "MEDIUM",
    "QUALIFIED_P33",
    "POLICY_FIT_CANDIDATE",
    (
        "De Silvestro occupied the third qualifying position and did "
        "not make another attempt."
    ),
)

add(
    2021,
    "75",
    "RC Enerson",
    "POST_GUARANTEED_BREAK",
    None,
    4,
    "OUTSIDE_FIELD",
    bubble_2021,
    None,
    "REATTEMPT",
    "STOP|REATTEMPT",
    "HIGH",
    "LOW",
    "FAILED_TO_QUALIFY",
    "ACTION_ONLY_UNTIL_FIRST_RUN_SPEED_RESOLVED",
    (
        "Enerson is known to have taken a second shot. "
        "His two official speeds exist but first-versus-second ordering "
        "is not yet independently resolved."
    ),
)

add(
    2021,
    "11",
    "Charlie Kimball",
    "POST_GUARANTEED_BREAK",
    None,
    5,
    "OUTSIDE_FIELD",
    bubble_2021,
    None,
    "REATTEMPT",
    "STOP|REATTEMPT",
    "HIGH",
    "LOW",
    "FAILED_TO_QUALIFY",
    "ACTION_ONLY_UNTIL_FIRST_RUN_SPEED_RESOLVED",
    (
        "Kimball is known to have taken a second shot. "
        "His two official speeds exist but first-versus-second ordering "
        "is not yet independently resolved."
    ),
)


# =============================================================================
# 2023 — post guaranteed-attempt break
#
# Official reports establish Harvey was the only driver to make multiple
# attempts. The three other drivers therefore provide genuine STOP outcomes.
#
# Known ranking after the first guaranteed pass:
# Lundgaard 229.649
# Robb      229.549
# Rahal     229.159
# Harvey    outside top three
# =============================================================================

bubble_2023 = 229.159

add(
    2023,
    "45",
    "Christian Lundgaard",
    "POST_GUARANTEED_BREAK",
    229.649,
    1,
    "PROVISIONALLY_QUALIFIED",
    bubble_2023,
    229.649 - bubble_2023,
    "STOP",
    "STOP|WITHDRAW_AND_REATTEMPT",
    "HIGH",
    "HIGH",
    "QUALIFIED_P31",
    "POLICY_FIT_CANDIDATE",
    (
        "Held the fastest Last Chance result after the guaranteed pass "
        "and made no further attempt."
    ),
)

add(
    2023,
    "51",
    "Sting Ray Robb",
    "POST_GUARANTEED_BREAK",
    229.549,
    2,
    "PROVISIONALLY_QUALIFIED",
    bubble_2023,
    229.549 - bubble_2023,
    "STOP",
    "STOP|WITHDRAW_AND_REATTEMPT",
    "HIGH",
    "HIGH",
    "QUALIFIED_P32",
    "POLICY_FIT_CANDIDATE",
    (
        "Held P32 after the guaranteed pass and made no further attempt."
    ),
)

add(
    2023,
    "15",
    "Graham Rahal",
    "POST_GUARANTEED_BREAK",
    229.159,
    3,
    "PROVISIONALLY_ON_BUBBLE",
    bubble_2023,
    0.0,
    "STOP",
    "STOP|WITHDRAW_AND_REATTEMPT",
    "HIGH",
    "HIGH",
    "ULTIMATELY_BUMPED_BY_HARVEY",
    "POLICY_FIT_CANDIDATE",
    (
        "Rahal held the bubble after the guaranteed pass and chose not "
        "to withdraw his 229.159 mph result for another attempt."
    ),
)

add(
    2023,
    "30",
    "Jack Harvey",
    "POST_GUARANTEED_BREAK",
    None,
    4,
    "OUTSIDE_FIELD",
    bubble_2023,
    None,
    "REATTEMPT",
    "STOP|REATTEMPT",
    "HIGH",
    "MEDIUM",
    "ULTIMATELY_QUALIFIED_P33",
    "POLICY_FIT_CANDIDATE_WITH_PARTIAL_NUMERIC_STATE",
    (
        "Harvey was the only driver making multiple attempts. "
        "His precise first-run speed is not assigned in this panel yet."
    ),
)


# =============================================================================
# 2024
#
# We currently have strong individual episodes, but the full post-guaranteed
# state is less clean because Ericsson's earlier failed sequence complicates
# a single four-car first-pass ranking.
#
# Therefore only the clean final Siegel state is admitted here.
# =============================================================================

add(
    2024,
    "18",
    "Nolan Siegel",
    "FINAL_DECISION",
    229.566,
    4,
    "OUTSIDE_FIELD_AFTER_BUMP",
    229.974,
    229.566 - 229.974,
    "REATTEMPT",
    "STOP|REATTEMPT",
    "HIGH",
    "HIGH",
    "CRASH_INCOMPLETE_FAILED_TO_QUALIFY",
    "HIGH_VALUE_REPLAY_AND_POLICY_CANDIDATE",
    (
        "Siegel was outside the field with a known 229.566 mph prior run. "
        "Rahal held the bubble at 229.974 mph. "
        "Siegel attempted the final run and crashed."
    ),
)


# =============================================================================
# QA and summaries
# =============================================================================

actions = Counter(
    r["observed_action"]
    for r in rows
)

fit_rows = [
    r
    for r in rows
    if r["safe_for_policy_fit"]
]

complete_numeric_fit = [
    r
    for r in fit_rows
    if (
        r["current_speed_mph"]
        and
        r["bubble_speed_mph"]
    )
]

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
        if r["year"] == year
    ]

    summary_rows.append({
        "year":
            year,

        "decision_rows":
            len(subset),

        "stop_rows":
            sum(
                r["observed_action"] == "STOP"
                for r in subset
            ),

        "reattempt_rows":
            sum(
                r["observed_action"] == "REATTEMPT"
                for r in subset
            ),

        "policy_fit_rows":
            sum(
                bool(r["safe_for_policy_fit"])
                for r in subset
            ),

        "complete_numeric_state_rows":
            sum(
                bool(
                    r["current_speed_mph"]
                    and
                    r["bubble_speed_mph"]
                )
                for r in subset
            ),
    })


qa_rows = [
    {
        "metric":
            "action_diversity",

        "value":
            ";".join(
                sorted(
                    actions.keys()
                )
            ),

        "expected":
            "REATTEMPT;STOP",

        "status":
            (
                "PASS"
                if set(
                    actions.keys()
                )
                == {
                    "STOP",
                    "REATTEMPT",
                }
                else "FAIL"
            ),
    },

    {
        "metric":
            "stop_examples",

        "value":
            actions.get(
                "STOP",
                0
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if actions.get(
                    "STOP",
                    0
                ) > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "reattempt_examples",

        "value":
            actions.get(
                "REATTEMPT",
                0
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if actions.get(
                    "REATTEMPT",
                    0
                ) > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_post_break_four_cars",

        "value":
            sum(
                1
                for r in rows
                if (
                    r["year"] == 2023
                    and
                    r["decision_stage"]
                    == "POST_GUARANTEED_BREAK"
                )
            ),

        "expected":
            4,

        "status":
            (
                "PASS"
                if sum(
                    1
                    for r in rows
                    if (
                        r["year"] == 2023
                        and
                        r["decision_stage"]
                        == "POST_GUARANTEED_BREAK"
                    )
                ) == 4
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_action_pattern",

        "value":
            ";".join(
                r["observed_action"]
                for r in rows
                if (
                    r["year"] == 2023
                    and
                    r["decision_stage"]
                    == "POST_GUARANTEED_BREAK"
                )
            ),

        "expected":
            "STOP;STOP;STOP;REATTEMPT",

        "status":
            (
                "PASS"
                if [
                    r["observed_action"]
                    for r in rows
                    if (
                        r["year"] == 2023
                        and
                        r["decision_stage"]
                        == "POST_GUARANTEED_BREAK"
                    )
                ]
                == [
                    "STOP",
                    "STOP",
                    "STOP",
                    "REATTEMPT",
                ]
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_exact_timestamps_fabricated",

        "value":
            sum(
                bool(
                    r[
                        "exact_timestamp"
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
                        "exact_timestamp"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },
]


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


report = {
    "phase":
        "R4LC5D",

    "status":
        "R4LC5D_LAST_CHANCE_DECISION_OPPORTUNITY_PANEL_READY",

    "rows":
        len(rows),

    "action_counts":
        dict(actions),

    "policy_fit_candidate_rows":
        len(
            fit_rows
        ),

    "fully_numeric_policy_fit_rows":
        len(
            complete_numeric_fit
        ),

    "critical_semantics": {
        "day1":
            [
                "STOP",
                "RETAIN_AND_REATTEMPT",
                "WITHDRAW_AND_PRIORITY_REATTEMPT",
            ],

        "last_chance_qualified":
            [
                "STOP",
                "WITHDRAW_AND_REATTEMPT",
            ],

        "last_chance_unqualified":
            [
                "STOP",
                "REATTEMPT",
            ],
    },

    "interpretation":
        (
            "Action diversity becomes available once decision opportunities "
            "include cars that had the opportunity to reattempt but chose STOP. "
            "The 2023 post-guaranteed-attempt state is the cleanest current "
            "Last Chance policy supervision block."
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


print("=" * 118)
print("R4LC5D — LAST CHANCE DECISION OPPORTUNITY PANEL")
print("=" * 118)

print()
print("ACTION COUNTS")

for action in sorted(
    actions
):

    print(
        f"{action:12s} | "
        f"{actions[action]}"
    )


print()
print("YEAR SUMMARY")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"rows={r['decision_rows']} | "
        f"STOP={r['stop_rows']} | "
        f"REATTEMPT={r['reattempt_rows']} | "
        f"policy_fit={r['policy_fit_rows']} | "
        f"numeric_state={r['complete_numeric_state_rows']}"
    )


print()
print("POLICY-FIT CANDIDATES")

for r in fit_rows:

    print(
        f"{r['decision_id']} | "
        f"state={r['qualification_state']} | "
        f"speed={r['current_speed_mph'] or '-'} | "
        f"bubble={r['bubble_speed_mph'] or '-'} | "
        f"gap={r['gap_to_bubble_mph'] or '-'} | "
        f"action={r['observed_action']} | "
        f"feasible={r['feasible_actions']}"
    )


print()
print(
    "Fully numeric policy-fit rows: "
    f"{len(complete_numeric_fit)}"
)


fails = [
    r
    for r in qa_rows
    if r["status"] == "FAIL"
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
    "R4LC5D_LAST_CHANCE_DECISION_OPPORTUNITY_PANEL_READY"
)
