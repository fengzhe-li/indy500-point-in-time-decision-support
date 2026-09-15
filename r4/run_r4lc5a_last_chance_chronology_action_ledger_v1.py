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
    "r4lc5a_last_chance_chronology_action_ledger_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4lc5a_last_chance_chronology_action_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc5a_last_chance_chronology_action_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc5a_last_chance_chronology_action_report_v1.json"
)


# =============================================================================
# Evidence policy
#
# EXACT:
#   directly stated / structurally explicit in source
#
# PARTIAL_ORDER:
#   relative chronology is known, exact timestamp is not
#
# BOUNDED:
#   event known within session/final-attempt context
#
# UNKNOWN:
#   must not be fabricated
# =============================================================================


rows = []


def add(
    year,
    car,
    driver,
    event_kind,
    attempt_ordinal,
    attempt_ordinal_quality,
    performance_mph,
    completion_status,
    chronology_quality,
    relative_order,
    strategy_event,
    result_before,
    result_after,
    source_class,
    source_name,
    source_url,
    evidence_note,
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

        "event_kind":
            event_kind,

        "attempt_ordinal":
            (
                attempt_ordinal
                if attempt_ordinal is not None
                else ""
            ),

        "attempt_ordinal_quality":
            attempt_ordinal_quality,

        "performance_mph":
            (
                f"{performance_mph:.3f}"
                if performance_mph is not None
                else ""
            ),

        "completion_status":
            completion_status,

        "chronology_quality":
            chronology_quality,

        "relative_order":
            relative_order,

        "strategy_event":
            strategy_event,

        "result_before":
            result_before,

        "result_after":
            result_after,

        "exact_timestamp":
            "",

        "timestamp_status":
            "UNKNOWN",

        "source_class":
            source_class,

        "source_name":
            source_name,

        "source_url":
            source_url,

        "evidence_note":
            evidence_note,

        "safe_for_action_training":
            False,

        "safe_for_performance_training":
            (
                performance_mph is not None
                and
                completion_status == "COMPLETE"
            ),
    })


# =============================================================================
# 2021
# =============================================================================

SOURCE_2021_ORDER = (
    "https://www.indycar.com/news/2021/05/05-23-greenflag"
)

SOURCE_2021_RECAP = (
    "https://www.indycar.com/news/2021/05/05-23-paddockbuzz"
)


# Guaranteed first-run order.
initial_2021 = [
    ("24", "Sage Karam", 229.156, 1),
    ("12", "Will Power", 228.876, 2),
    ("75", "RC Enerson", None, 3),
    ("16", "Simona De Silvestro", 228.353, 4),
    ("11", "Charlie Kimball", None, 5),
]

for car, driver, speed, order in initial_2021:

    add(
        year=2021,
        car=car,
        driver=driver,
        event_kind="GUARANTEED_FIRST_ATTEMPT",
        attempt_ordinal=1,
        attempt_ordinal_quality="EXACT",
        performance_mph=speed,
        completion_status="COMPLETE",
        chronology_quality="PARTIAL_ORDER",
        relative_order=f"INITIAL_ORDER_{order}_OF_5",
        strategy_event="INITIAL_ATTEMPT",
        result_before="NO_LAST_ROW_RESULT",
        result_after=(
            "OFFICIAL_RESULT_AVAILABLE"
            if speed is not None
            else "RESULT_VALUE_NOT_BOUND_TO_THIS_ATTEMPT_YET"
        ),
        source_class="OFFICIAL_INDYCAR_REPORT",
        source_name="Green Flag: Crown Royal Armed Forces Qualifying Day 2",
        source_url=SOURCE_2021_ORDER,
        evidence_note=(
            "Official source establishes initial Last Row order. "
            "For Kimball and Enerson, API contains two complete records "
            "but this ledger does not yet assign which speed belongs to "
            "attempt 1 versus attempt 2."
        ),
    )


# Kimball has two official complete API records.
for speed in [
    227.811,
    227.584,
]:

    add(
        year=2021,
        car="11",
        driver="Charlie Kimball",
        event_kind="COMPLETE_REPEAT_RECORD",
        attempt_ordinal=None,
        attempt_ordinal_quality="UNRESOLVED_BETWEEN_ATTEMPT_1_AND_2",
        performance_mph=speed,
        completion_status="COMPLETE",
        chronology_quality="UNRESOLVED_WITHIN_ENTRY",
        relative_order="ONE_OF_TWO_SHOTS",
        strategy_event="REATTEMPT_EVIDENCE",
        result_before="UNKNOWN",
        result_after="UNKNOWN",
        source_class="OFFICIAL_API_PLUS_OFFICIAL_REPORT",
        source_name="INDYCAR EventsSessionDetails + Paddock Buzz",
        source_url=SOURCE_2021_RECAP,
        evidence_note=(
            "Official API preserves two complete Kimball records. "
            "INDYCAR states Kimball took two shots. "
            "Record ordering is not assumed chronological."
        ),
    )


# Enerson has two official complete API records.
for speed in [
    227.298,
    226.813,
]:

    add(
        year=2021,
        car="75",
        driver="RC Enerson",
        event_kind="COMPLETE_REPEAT_RECORD",
        attempt_ordinal=None,
        attempt_ordinal_quality="UNRESOLVED_BETWEEN_ATTEMPT_1_AND_2",
        performance_mph=speed,
        completion_status="COMPLETE",
        chronology_quality="UNRESOLVED_WITHIN_ENTRY",
        relative_order="ONE_OF_TWO_SHOTS",
        strategy_event="REATTEMPT_EVIDENCE",
        result_before="UNKNOWN",
        result_after="UNKNOWN",
        source_class="OFFICIAL_API_PLUS_OFFICIAL_REPORT",
        source_name="INDYCAR EventsSessionDetails + Paddock Buzz",
        source_url=SOURCE_2021_RECAP,
        evidence_note=(
            "Official API preserves two complete Enerson records. "
            "INDYCAR states Enerson took two shots. "
            "Record ordering is not assumed chronological."
        ),
    )


# =============================================================================
# 2023
# =============================================================================

SOURCE_2023 = (
    "https://www.indycar.com/News/2023/05/05-21-Buzz"
)

SOURCE_2023_RLL = (
    "https://www.indycar.com/news/2023/05/05-21-rll-lastchance"
)


# Three non-Harvey final official results.
for car, driver, speed in [
    ("45", "Christian Lundgaard", 229.649),
    ("51", "Sting Ray Robb", 229.549),
    ("15", "Graham Rahal", 229.159),
]:

    add(
        year=2023,
        car=car,
        driver=driver,
        event_kind="OFFICIAL_COMPLETE_RESULT",
        attempt_ordinal=1,
        attempt_ordinal_quality=(
            "EXACT"
            if driver == "Graham Rahal"
            else "NOT_PROVEN_SINGLE_ATTEMPT_BUT_NO_REPEAT_REPORTED"
        ),
        performance_mph=speed,
        completion_status="COMPLETE",
        chronology_quality=(
            "PARTIAL_ORDER"
            if driver == "Graham Rahal"
            else "UNKNOWN"
        ),
        relative_order=(
            "LAST_OF_GUARANTEED_FIRST_ATTEMPTS"
            if driver == "Graham Rahal"
            else "UNKNOWN"
        ),
        strategy_event="INITIAL_OR_ONLY_ATTEMPT",
        result_before="NO_LAST_CHANCE_RESULT",
        result_after="OFFICIAL_RESULT",
        source_class="OFFICIAL_API_PLUS_OFFICIAL_REPORT",
        source_name="RLL Rides Roller Coaster of Agony",
        source_url=SOURCE_2023_RLL,
        evidence_note=(
            "Rahal is explicitly reported as the last driver to make "
            "his first attempt. Harvey is explicitly reported as the "
            "only driver to make multiple attempts."
            if driver == "Graham Rahal"
            else
            "Official final result; no repeat attempt attributed to "
            "this driver in the cited official chronology."
        ),
    )


# Harvey attempt 1: existence certain, exact speed not yet recovered.
add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    event_kind="ATTEMPT",
    attempt_ordinal=1,
    attempt_ordinal_quality="EXACT",
    performance_mph=None,
    completion_status="COMPLETE_OR_RESULT_NOT_YET_RECOVERED",
    chronology_quality="PARTIAL_ORDER",
    relative_order="BEFORE_ATTEMPT_2",
    strategy_event="INITIAL_ATTEMPT",
    result_before="NO_LAST_CHANCE_RESULT",
    result_after="UNKNOWN",
    source_class="OFFICIAL_INDYCAR_REPORT",
    source_name="Paddock Buzz: Mixed Emotions for Harvey",
    source_url=SOURCE_2023,
    evidence_note=(
        "Official source establishes Harvey later made attempts 2, 3 and 4; "
        "attempt-1 numeric result is not assigned here without source evidence."
    ),
)


# Harvey attempt 2 waved off after two laps.
add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    event_kind="ATTEMPT",
    attempt_ordinal=2,
    attempt_ordinal_quality="EXACT",
    performance_mph=None,
    completion_status="WAVED_OFF_AFTER_TWO_LAPS",
    chronology_quality="PARTIAL_ORDER",
    relative_order="AFTER_ATTEMPT_1_BEFORE_ATTEMPT_3",
    strategy_event="REATTEMPT",
    result_before="PREVIOUS_RESULT_STATE_UNKNOWN",
    result_after="NO_COMPLETE_NEW_FOUR_LAP_RESULT",
    source_class="OFFICIAL_INDYCAR_REPORT",
    source_name="Paddock Buzz: Mixed Emotions for Harvey",
    source_url=SOURCE_2023,
    evidence_note=(
        "Official source states Harvey's second qualifying attempt "
        "was waved off after two laps."
    ),
)


# Harvey attempt 3 complete but failed to beat Rahal.
add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    event_kind="ATTEMPT",
    attempt_ordinal=3,
    attempt_ordinal_quality="EXACT",
    performance_mph=None,
    completion_status="COMPLETE_BUT_BELOW_RAHAL",
    chronology_quality="PARTIAL_ORDER",
    relative_order="AFTER_ATTEMPT_2_BEFORE_FINAL_ATTEMPT",
    strategy_event="REATTEMPT",
    result_before="PREVIOUS_RESULT_STATE_UNKNOWN",
    result_after="STILL_OUTSIDE_FINAL_TRANSFER_POSITION",
    source_class="OFFICIAL_INDYCAR_REPORT",
    source_name="Paddock Buzz: Mixed Emotions for Harvey",
    source_url=SOURCE_2023,
    evidence_note=(
        "Official source states Harvey's third attempt also failed "
        "to dislodge Rahal."
    ),
)


# Harvey final fourth run.
add(
    year=2023,
    car="30",
    driver="Jack Harvey",
    event_kind="ATTEMPT",
    attempt_ordinal=4,
    attempt_ordinal_quality="EXACT",
    performance_mph=229.166,
    completion_status="COMPLETE",
    chronology_quality="BOUNDED_SESSION_END",
    relative_order="FINAL_DECISIVE_RUN_AS_SESSION_EXPIRED",
    strategy_event="REATTEMPT",
    result_before="OUTSIDE_FIELD",
    result_after="QUALIFIED_POSITION_33",
    source_class="OFFICIAL_API_PLUS_OFFICIAL_REPORT",
    source_name="Paddock Buzz: Mixed Emotions for Harvey",
    source_url=SOURCE_2023,
    evidence_note=(
        "Official source describes Harvey starting the decisive fourth run "
        "as session time expired. API final record is 229.166 mph, "
        "0.007 mph faster than Rahal's 229.159."
    ),
)


# =============================================================================
# 2024
# =============================================================================

SOURCE_2024 = (
    "https://www.indycar.com/news/2024/05/05-19-lastchance"
)

SOURCE_2024_FINAL = (
    "https://www.indycar.com/news/2024/05/05-19-top12-update"
)


# Legge and Rahal final official runs.
for car, driver, speed in [
    ("51", "Katherine Legge", 230.092),
    ("15", "Graham Rahal", 229.974),
]:

    add(
        year=2024,
        car=car,
        driver=driver,
        event_kind="OFFICIAL_COMPLETE_RESULT",
        attempt_ordinal=1,
        attempt_ordinal_quality="PROVISIONAL_SINGLE_ATTEMPT",
        performance_mph=speed,
        completion_status="COMPLETE",
        chronology_quality="UNKNOWN",
        relative_order="UNKNOWN",
        strategy_event="INITIAL_OR_ONLY_ATTEMPT",
        result_before="NO_LAST_CHANCE_RESULT",
        result_after="QUALIFIED",
        source_class="OFFICIAL_API",
        source_name="INDYCAR EventsSessionDetails",
        source_url=SOURCE_2024,
        evidence_note=(
            "Official API complete four-lap result. "
            "No additional attempt is assigned without chronology evidence."
        ),
    )


# Ericsson failed/mistaken earlier run.
add(
    year=2024,
    car="28",
    driver="Marcus Ericsson",
    event_kind="ATTEMPT",
    attempt_ordinal=1,
    attempt_ordinal_quality="PROVISIONAL_EARLIER_ATTEMPT",
    performance_mph=None,
    completion_status="FAILED_VALID_FOUR_LAP_RESULT",
    chronology_quality="PARTIAL_ORDER",
    relative_order="BEFORE_SUCCESSFUL_230.027_RUN",
    strategy_event="INITIAL_ATTEMPT",
    result_before="NO_LAST_CHANCE_RESULT",
    result_after="NO_SECURE_RESULT",
    source_class="OFFICIAL_INDYCAR_REPORT",
    source_name="Ericsson, Rahal Ride Turbulent Waves of Bump Drama",
    source_url=SOURCE_2024,
    evidence_note=(
        "Official report states Ericsson miscounted the qualifying lap "
        "and lifted after taking the white flag, requiring another run."
    ),
)


# Ericsson later successful run.
add(
    year=2024,
    car="28",
    driver="Marcus Ericsson",
    event_kind="ATTEMPT",
    attempt_ordinal=2,
    attempt_ordinal_quality="PROVISIONAL_SECOND_ATTEMPT",
    performance_mph=230.027,
    completion_status="COMPLETE",
    chronology_quality="PARTIAL_ORDER",
    relative_order="AFTER_FAILED_EARLIER_RUN_BEFORE_SIEGEL_FINAL_RUN",
    strategy_event="REATTEMPT",
    result_before="NO_SECURE_RESULT",
    result_after="QUALIFIED_POSITION_32",
    source_class="OFFICIAL_API_PLUS_OFFICIAL_REPORT",
    source_name="Ericsson, Rahal Ride Turbulent Waves of Bump Drama",
    source_url=SOURCE_2024,
    evidence_note=(
        "Successful official four-lap result; article states Ericsson "
        "then had to wait through Siegel's final attempt."
    ),
)


# Siegel first valid result.
add(
    year=2024,
    car="18",
    driver="Nolan Siegel",
    event_kind="ATTEMPT",
    attempt_ordinal=1,
    attempt_ordinal_quality="EXACT",
    performance_mph=229.566,
    completion_status="COMPLETE",
    chronology_quality="PARTIAL_ORDER",
    relative_order="EARLY_VALID_RUN_BEFORE_BEING_BUMPED",
    strategy_event="INITIAL_ATTEMPT",
    result_before="NO_LAST_CHANCE_RESULT",
    result_after="PROVISIONALLY_QUALIFIED_THEN_LATER_BUMPED",
    source_class="OFFICIAL_API_PLUS_OFFICIAL_REPORT",
    source_name="Ericsson, Rahal Ride Turbulent Waves of Bump Drama",
    source_url=SOURCE_2024,
    evidence_note=(
        "Official report explicitly identifies 229.566 mph as "
        "Siegel's first qualifying attempt."
    ),
)


# Siegel final crash attempt.
add(
    year=2024,
    car="18",
    driver="Nolan Siegel",
    event_kind="ATTEMPT",
    attempt_ordinal=2,
    attempt_ordinal_quality="EXACT_FINAL_ATTEMPT",
    performance_mph=None,
    completion_status="CRASH_INCOMPLETE",
    chronology_quality="BOUNDED_SESSION_END",
    relative_order="FINAL_ATTEMPT_OF_SESSION",
    strategy_event="REATTEMPT",
    result_before="OUTSIDE_FIELD",
    result_after="FAILED_TO_QUALIFY",
    source_class="OFFICIAL_INDYCAR_REPORT",
    source_name="Penske Back on Track for Front Row Sweep; Siegel Out",
    source_url=SOURCE_2024_FINAL,
    evidence_note=(
        "Official report states Siegel crashed on the final qualifying "
        "attempt of the session while trying to bump Rahal."
    ),
)


# =============================================================================
# Training-safety policy
# =============================================================================

for r in rows:

    # Action training requires more than the existence of a reattempt:
    # we still need the decision state immediately before the action.
    #
    # Therefore R4LC5A remains evidence-only.
    r[
        "safe_for_action_training"
    ] = False


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

    complete_numeric = [
        r
        for r in subset
        if (
            r["performance_mph"]
            and
            r["completion_status"]
            == "COMPLETE"
        )
    ]

    reattempt_events = [
        r
        for r in subset
        if r[
            "strategy_event"
        ] == "REATTEMPT"
    ]

    summary_rows.append({
        "year":
            year,

        "ledger_rows":
            len(subset),

        "complete_numeric_performance_rows":
            len(
                complete_numeric
            ),

        "reattempt_events":
            len(
                reattempt_events
            ),

        "exact_attempt_ordinals":
            sum(
                1
                for r in subset
                if r[
                    "attempt_ordinal_quality"
                ] in {
                    "EXACT",
                    "EXACT_FINAL_ATTEMPT",
                }
            ),

        "exact_timestamps":
            0,

        "action_training_rows":
            0,

        "status":
            "CHRONOLOGY_ACTION_EVIDENCE_PARTIAL",
    })


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "years_present",

        "value":
            sorted(
                {
                    r["year"]
                    for r in rows
                }
            ),

        "expected":
            [2021, 2023, 2024],

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
            "2021_initial_order_rows",

        "value":
            sum(
                1
                for r in rows
                if (
                    r["year"] == 2021
                    and
                    r["event_kind"]
                    == "GUARANTEED_FIRST_ATTEMPT"
                )
            ),

        "expected":
            5,

        "status":
            (
                "PASS"
                if sum(
                    1
                    for r in rows
                    if (
                        r["year"] == 2021
                        and
                        r["event_kind"]
                        == "GUARANTEED_FIRST_ATTEMPT"
                    )
                )
                == 5
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_repeat_complete_records",

        "value":
            sum(
                1
                for r in rows
                if (
                    r["year"] == 2021
                    and
                    r["event_kind"]
                    == "COMPLETE_REPEAT_RECORD"
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
                        r["year"] == 2021
                        and
                        r["event_kind"]
                        == "COMPLETE_REPEAT_RECORD"
                    )
                )
                == 4
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_harvey_attempts_represented",

        "value":
            sum(
                1
                for r in rows
                if (
                    r["year"] == 2023
                    and
                    r["driver_name"]
                    == "Jack Harvey"
                    and
                    r["event_kind"]
                    == "ATTEMPT"
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
                        r["driver_name"]
                        == "Jack Harvey"
                        and
                        r["event_kind"]
                        == "ATTEMPT"
                    )
                )
                == 4
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_siegel_attempts_represented",

        "value":
            sum(
                1
                for r in rows
                if (
                    r["year"] == 2024
                    and
                    r["driver_name"]
                    == "Nolan Siegel"
                    and
                    r["event_kind"]
                    == "ATTEMPT"
                )
            ),

        "expected":
            2,

        "status":
            (
                "PASS"
                if sum(
                    1
                    for r in rows
                    if (
                        r["year"] == 2024
                        and
                        r["driver_name"]
                        == "Nolan Siegel"
                        and
                        r["event_kind"]
                        == "ATTEMPT"
                    )
                )
                == 2
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_fabricated_exact_timestamps",

        "value":
            sum(
                1
                for r in rows
                if r[
                    "exact_timestamp"
                ]
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

    {
        "metric":
            "no_premature_action_training_labels",

        "value":
            sum(
                1
                for r in rows
                if r[
                    "safe_for_action_training"
                ]
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if all(
                    not r[
                        "safe_for_action_training"
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
        "R4LC5A",

    "status":
        "R4LC5A_LAST_CHANCE_CHRONOLOGY_ACTION_EVIDENCE_READY",

    "ledger_rows":
        len(rows),

    "research_interpretation":
        (
            "Public and official evidence confirms multiple reattempt "
            "episodes in 2021, 2023 and 2024, but exact timestamps and "
            "complete pre-decision state remain unresolved. "
            "This phase is therefore evidence reconstruction, not yet "
            "action-policy training."
        ),

    "critical_findings": [
        (
            "2021 official API record order must not be treated as "
            "chronology because official initial qualifying order differs."
        ),
        (
            "2023 Jack Harvey has four documented attempts, including "
            "a two-lap waved-off second attempt and a decisive fourth run."
        ),
        (
            "2024 Marcus Ericsson and Nolan Siegel both have important "
            "reattempt chronology absent from the final-results API rows."
        ),
    ],
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
print("R4LC5A — LAST CHANCE CHRONOLOGY + ACTION EVIDENCE")
print("=" * 118)

print()
print("YEAR SUMMARY")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"rows={r['ledger_rows']} | "
        f"numeric_complete={r['complete_numeric_performance_rows']} | "
        f"reattempt_events={r['reattempt_events']} | "
        f"exact_attempt_ordinals={r['exact_attempt_ordinals']} | "
        f"action_train={r['action_training_rows']}"
    )


print()
print("KEY REATTEMPT EVIDENCE")

for r in rows:

    if (
        r["strategy_event"]
        == "REATTEMPT"
        or
        r["event_kind"]
        == "COMPLETE_REPEAT_RECORD"
    ):

        print(
            f"{r['year']} | "
            f"car={r['car_number']} | "
            f"{r['driver_name']} | "
            f"attempt={r['attempt_ordinal'] or '?'} | "
            f"status={r['completion_status']} | "
            f"speed={r['performance_mph'] or '-'} | "
            f"order={r['relative_order']}"
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
    "R4LC5A_LAST_CHANCE_CHRONOLOGY_ACTION_EVIDENCE_READY"
)
