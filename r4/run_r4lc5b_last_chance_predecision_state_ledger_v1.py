from pathlib import Path
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_LEDGER = (
    OUT /
    "r4lc5b_last_chance_predecision_state_ledger_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4lc5b_last_chance_predecision_state_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc5b_last_chance_predecision_state_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc5b_last_chance_predecision_state_report_v1.json"
)


rows = []


def add(
    year,
    car,
    driver,
    decision_id,
    attempt_ordinal_next,
    current_result_mph,
    current_result_status,
    current_field_status,
    bubble_reference_driver,
    bubble_reference_mph,
    gap_to_bubble_mph,
    session_remaining_status,
    chronology_quality,
    observed_action,
    action_semantics_quality,
    outcome_status,
    resulting_speed_mph,
    source_basis,
    training_role,
    note,
):
    rows.append({
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

        "decision_id":
            decision_id,

        "attempt_ordinal_next":
            attempt_ordinal_next,

        "current_result_mph":
            (
                f"{current_result_mph:.3f}"
                if current_result_mph is not None
                else ""
            ),

        "current_result_status":
            current_result_status,

        "current_field_status":
            current_field_status,

        "bubble_reference_driver":
            bubble_reference_driver,

        "bubble_reference_mph":
            (
                f"{bubble_reference_mph:.3f}"
                if bubble_reference_mph is not None
                else ""
            ),

        "gap_to_bubble_mph":
            (
                f"{gap_to_bubble_mph:.3f}"
                if gap_to_bubble_mph is not None
                else ""
            ),

        "session_remaining_status":
            session_remaining_status,

        "exact_session_remaining_seconds":
            "",

        "chronology_quality":
            chronology_quality,

        "observed_action":
            observed_action,

        "action_semantics_quality":
            action_semantics_quality,

        "outcome_status":
            outcome_status,

        "resulting_speed_mph":
            (
                f"{resulting_speed_mph:.3f}"
                if resulting_speed_mph is not None
                else ""
            ),

        "source_basis":
            source_basis,

        "training_role":
            training_role,

        "safe_for_action_policy_fit":
            False,

        "note":
            note,
    })


# =============================================================================
# 2021
#
# Official evidence:
# - Kimball and Enerson each made two attempts.
# - Exact within-entry speed chronology remains unresolved.
# - Exact pre-second-attempt leaderboard state remains unresolved.
# =============================================================================

for car, driver in [
    ("11", "Charlie Kimball"),
    ("75", "RC Enerson"),
]:

    add(
        year=2021,
        car=car,
        driver=driver,
        decision_id=f"2021_{car}_BEFORE_ATTEMPT_2",
        attempt_ordinal_next=2,
        current_result_mph=None,
        current_result_status="EXISTING_COMPLETE_RESULT_BUT_NUMERIC_ORDER_UNRESOLVED",
        current_field_status="OUTSIDE_TOP_33_OR_ATTEMPTING_TO_BUMP_IN",
        bubble_reference_driver="UNKNOWN",
        bubble_reference_mph=None,
        gap_to_bubble_mph=None,
        session_remaining_status="WITHIN_ONE_HOUR_LAST_ROW_SESSION_EXACT_TIME_UNKNOWN",
        chronology_quality="PARTIAL",
        observed_action="REATTEMPT",
        action_semantics_quality="REATTEMPT_CONFIRMED_WITHDRAW_RETAIN_MECHANISM_UNRESOLVED",
        outcome_status="FAILED_TO_QUALIFY",
        resulting_speed_mph=None,
        source_basis="OFFICIAL_INDYCAR_RECAP_PLUS_OFFICIAL_API",
        training_role="ACTION_EXISTENCE_ONLY",
        note=(
            "Official reporting confirms two shots. "
            "The API provides two complete speeds, but this phase does not "
            "assign one as the current result and one as the second-attempt "
            "outcome until chronology is independently resolved."
        ),
    )


# =============================================================================
# 2023 Jack Harvey
#
# Rahal held P33 at 229.159 after his first attempt.
# Harvey was the only driver making multiple attempts.
# Attempt 2 waved off after 2 laps.
# Attempt 3 failed to beat Rahal.
# Attempt 4 started as session time expired and achieved 229.166.
# =============================================================================

add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    decision_id="2023_30_BEFORE_ATTEMPT_2",
    attempt_ordinal_next=2,
    current_result_mph=None,
    current_result_status="PRIOR_COMPLETE_RESULT_EXISTS_NUMERIC_VALUE_UNRESOLVED",
    current_field_status="OUTSIDE_OR_BELOW_TRANSFER_POSITION",
    bubble_reference_driver="Graham Rahal",
    bubble_reference_mph=229.159,
    gap_to_bubble_mph=None,
    session_remaining_status="POSITIVE_TIME_REMAINING_EXACT_VALUE_UNKNOWN",
    chronology_quality="PARTIAL_ORDER",
    observed_action="REATTEMPT",
    action_semantics_quality="REATTEMPT_CONFIRMED_EXACT_WITHDRAW_RETAIN_STATE_UNRESOLVED",
    outcome_status="WAVED_OFF_AFTER_TWO_LAPS",
    resulting_speed_mph=None,
    source_basis="OFFICIAL_INDYCAR_2023_PADDOCK_BUZZ",
    training_role="PARTIAL_DECISION_EPISODE",
    note=(
        "Harvey made a second attempt after setup changes. "
        "The run was waved off after two laps."
    ),
)

add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    decision_id="2023_30_BEFORE_ATTEMPT_3",
    attempt_ordinal_next=3,
    current_result_mph=None,
    current_result_status="PRIOR_RESULT_STATE_PRESENT_BUT_NUMERIC_VALUE_UNRESOLVED",
    current_field_status="OUTSIDE_TRANSFER_POSITION",
    bubble_reference_driver="Graham Rahal",
    bubble_reference_mph=229.159,
    gap_to_bubble_mph=None,
    session_remaining_status="POSITIVE_TIME_REMAINING_EXACT_VALUE_UNKNOWN",
    chronology_quality="PARTIAL_ORDER",
    observed_action="REATTEMPT",
    action_semantics_quality="REATTEMPT_CONFIRMED_EXACT_WITHDRAW_RETAIN_STATE_UNRESOLVED",
    outcome_status="COMPLETE_BUT_FAILED_TO_BEAT_BUBBLE",
    resulting_speed_mph=None,
    source_basis="OFFICIAL_INDYCAR_2023_PADDOCK_BUZZ",
    training_role="PARTIAL_DECISION_EPISODE",
    note=(
        "Third attempt was complete enough to be evaluated but failed "
        "to dislodge Rahal. Exact run speed is not assigned here."
    ),
)

add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    decision_id="2023_30_BEFORE_ATTEMPT_4",
    attempt_ordinal_next=4,
    current_result_mph=None,
    current_result_status="PRIOR_RESULT_INSUFFICIENT_FOR_P33",
    current_field_status="OUTSIDE_FIELD",
    bubble_reference_driver="Graham Rahal",
    bubble_reference_mph=229.159,
    gap_to_bubble_mph=None,
    session_remaining_status="SESSION_CLOCK_EXPIRED_AS_WARMUP_LAP_BEGAN",
    chronology_quality="BOUNDED_SESSION_END",
    observed_action="REATTEMPT",
    action_semantics_quality="REATTEMPT_CONFIRMED_FINAL_AVAILABLE_SHOT",
    outcome_status="QUALIFIED_P33",
    resulting_speed_mph=229.166,
    source_basis="OFFICIAL_INDYCAR_2023_PADDOCK_BUZZ_PLUS_OFFICIAL_API",
    training_role="HIGH_VALUE_HISTORICAL_REPLAY_EPISODE",
    note=(
        "This is the cleanest Last Chance decision episode currently recovered. "
        "Harvey was outside the field, Rahal held the bubble at 229.159 mph, "
        "and Harvey started the decisive run as session time expired."
    ),
)


# =============================================================================
# 2024 Marcus Ericsson
#
# Earlier attempt failed to establish a secure valid four-lap result after
# Ericsson lifted early/miscounted the qualifying sequence.
# He then reattempted and posted 230.027.
# =============================================================================

add(
    year=2024,
    car="28",
    driver="Marcus Ericsson",
    decision_id="2024_28_BEFORE_SUCCESSFUL_REATTEMPT",
    attempt_ordinal_next=2,
    current_result_mph=None,
    current_result_status="NO_SECURE_VALID_FOUR_LAP_RESULT",
    current_field_status="AT_RISK_NOT_SECURELY_QUALIFIED",
    bubble_reference_driver="UNKNOWN",
    bubble_reference_mph=None,
    gap_to_bubble_mph=None,
    session_remaining_status="POSITIVE_TIME_REMAINING_EXACT_VALUE_UNKNOWN",
    chronology_quality="PARTIAL_ORDER",
    observed_action="REATTEMPT",
    action_semantics_quality="REATTEMPT_REQUIRED_AFTER_FAILED_VALID_RESULT",
    outcome_status="QUALIFIED_P32",
    resulting_speed_mph=230.027,
    source_basis="OFFICIAL_INDYCAR_2024_LAST_CHANCE_REPORT_PLUS_OFFICIAL_API",
    training_role="HIGH_VALUE_FAILURE_RECOVERY_EPISODE",
    note=(
        "Ericsson's earlier attempt did not leave a secure valid result. "
        "The subsequent complete attempt produced 230.027 mph and qualified P32."
    ),
)


# =============================================================================
# 2024 Nolan Siegel
#
# First recorded complete run = 229.566.
# He was later bumped out.
# Final attempt was made to recover a starting position and ended in a crash.
# =============================================================================

add(
    year=2024,
    car="18",
    driver="Nolan Siegel",
    decision_id="2024_18_BEFORE_FINAL_REATTEMPT",
    attempt_ordinal_next=2,
    current_result_mph=229.566,
    current_result_status="EXISTING_COMPLETE_RESULT_NO_LONGER_SUFFICIENT",
    current_field_status="OUTSIDE_FIELD_AFTER_BEING_BUMPED",
    bubble_reference_driver="Graham Rahal",
    bubble_reference_mph=229.974,
    gap_to_bubble_mph=(229.566 - 229.974),
    session_remaining_status="FINAL_ATTEMPT_OF_SESSION",
    chronology_quality="BOUNDED_SESSION_END",
    observed_action="REATTEMPT",
    action_semantics_quality="FINAL_REATTEMPT_CONFIRMED",
    outcome_status="CRASH_INCOMPLETE_FAILED_TO_QUALIFY",
    resulting_speed_mph=None,
    source_basis="OFFICIAL_INDYCAR_2024_LAST_CHANCE_REPORT_PLUS_OFFICIAL_API",
    training_role="HIGH_VALUE_DOWNSIDE_RISK_EPISODE",
    note=(
        "Siegel held a prior complete 229.566 mph run but had been bumped. "
        "Rahal's final qualifying speed was 229.974 mph. "
        "Siegel's final attempt ended in a crash."
    ),
)


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
        if r["year"] == year
    ]

    high_value = [
        r
        for r in subset
        if r[
            "training_role"
        ].startswith(
            "HIGH_VALUE"
        )
    ]

    numeric_current = [
        r
        for r in subset
        if r[
            "current_result_mph"
        ]
    ]

    numeric_bubble = [
        r
        for r in subset
        if r[
            "bubble_reference_mph"
        ]
    ]

    bounded_end = [
        r
        for r in subset
        if (
            "SESSION_END"
            in r[
                "chronology_quality"
            ]
            or
            "FINAL"
            in r[
                "session_remaining_status"
            ]
        )
    ]

    summary_rows.append({
        "year":
            year,

        "decision_episodes":
            len(subset),

        "high_value_replay_episodes":
            len(high_value),

        "numeric_current_result_rows":
            len(numeric_current),

        "numeric_bubble_reference_rows":
            len(numeric_bubble),

        "session_end_bounded_rows":
            len(bounded_end),

        "safe_for_action_policy_fit":
            0,
    })


# =============================================================================
# QA
# =============================================================================

ids = [
    r[
        "decision_id"
    ]
    for r in rows
]

qa_rows = [
    {
        "metric":
            "decision_ids_unique",

        "value":
            len(set(ids)),

        "expected":
            len(ids),

        "status":
            (
                "PASS"
                if len(set(ids))
                == len(ids)
                else "FAIL"
            ),
    },

    {
        "metric":
            "years_present",

        "value":
            ";".join(
                str(y)
                for y in sorted(
                    {
                        r["year"]
                        for r in rows
                    }
                )
            ),

        "expected":
            "2021;2023;2024",

        "status":
            (
                "PASS"
                if sorted(
                    {
                        r["year"]
                        for r in rows
                    }
                )
                == [
                    2021,
                    2023,
                    2024,
                ]
                else "FAIL"
            ),
    },

    {
        "metric":
            "harvey_attempt4_episode",

        "value":
            sum(
                1
                for r in rows
                if r[
                    "decision_id"
                ]
                == "2023_30_BEFORE_ATTEMPT_4"
            ),

        "expected":
            1,

        "status":
            (
                "PASS"
                if sum(
                    1
                    for r in rows
                    if r[
                        "decision_id"
                    ]
                    == "2023_30_BEFORE_ATTEMPT_4"
                )
                == 1
                else "FAIL"
            ),
    },

    {
        "metric":
            "siegel_final_episode",

        "value":
            sum(
                1
                for r in rows
                if r[
                    "decision_id"
                ]
                == "2024_18_BEFORE_FINAL_REATTEMPT"
            ),

        "expected":
            1,

        "status":
            (
                "PASS"
                if sum(
                    1
                    for r in rows
                    if r[
                        "decision_id"
                    ]
                    == "2024_18_BEFORE_FINAL_REATTEMPT"
                )
                == 1
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_fabricated_exact_clock_seconds",

        "value":
            sum(
                1
                for r in rows
                if r[
                    "exact_session_remaining_seconds"
                ]
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not r[
                        "exact_session_remaining_seconds"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_premature_policy_fit",

        "value":
            sum(
                1
                for r in rows
                if r[
                    "safe_for_action_policy_fit"
                ]
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not r[
                        "safe_for_action_policy_fit"
                    ]
                    for r in rows
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_LEDGER.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = list(
        rows[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fields
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
        "R4LC5B",

    "status":
        "R4LC5B_LAST_CHANCE_PREDECISION_STATE_LEDGER_READY",

    "decision_episode_count":
        len(rows),

    "important_interpretation":
        (
            "This ledger reconstructs observable pre-decision state "
            "only where supported. Reattempt existence does not yet "
            "imply a Day-1-style retain/withdraw action label."
        ),

    "next_gate":
        (
            "Recover time bounds, prior-run values, and exact rules/action "
            "semantics sufficiently to decide which episodes can enter "
            "Last-Chance-only policy fitting versus replay-only evaluation."
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
print("R4LC5B — LAST CHANCE PRE-DECISION STATE LEDGER")
print("=" * 118)

print()
print("YEAR SUMMARY")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"episodes={r['decision_episodes']} | "
        f"high_value={r['high_value_replay_episodes']} | "
        f"current_numeric={r['numeric_current_result_rows']} | "
        f"bubble_numeric={r['numeric_bubble_reference_rows']} | "
        f"session_end_bound={r['session_end_bounded_rows']}"
    )


print()
print("DECISION EPISODES")

for r in rows:

    print(
        f"{r['decision_id']} | "
        f"state={r['current_field_status']} | "
        f"current={r['current_result_mph'] or '-'} | "
        f"bubble={r['bubble_reference_mph'] or '-'} | "
        f"action={r['observed_action']} | "
        f"outcome={r['outcome_status']} | "
        f"role={r['training_role']}"
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
    OUT_LEDGER.relative_to(ROOT)
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
    "R4LC5B_LAST_CHANCE_PREDECISION_STATE_LEDGER_READY"
)
