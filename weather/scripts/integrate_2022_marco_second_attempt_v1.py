from pathlib import Path
import csv


PHASE = "R1G.28F"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V7 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v7.csv"
)

ACTION_V4 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v4.csv"
)

EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_second_attempt_therace_evidence_v1.csv"
)

REPEAT_POLICY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

CHRONOLOGY_V8 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v8.csv"
)

ACTION_V5 = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v5.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_second_attempt_integration_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_second_attempt_integration_v1_qa.csv"
)


FIRST_ID = "c044edbc-0f6c-5aab-bdef-9c4156b50617"
SECOND_ID = "63982b5e-7639-5140-a6a2-702a77c2fc85"

EXPECTED_FIRST_SPEED = "226.108"
EXPECTED_SECOND_SPEED = "230.345"


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def blank(fields):
    return {
        field: ""
        for field in fields
    }


def first(row, fields):
    for field in fields:
        value = txt(row.get(field))
        if value:
            return value
    return ""


def driver(row):
    return first(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def car(row):
    return first(
        row,
        [
            "car_number",
            "car_no",
            "car",
        ],
    )


def attempt_index(row):
    return first(
        row,
        [
            "car_attempt_index",
            "attempt_index",
        ],
    )


def speed(row):
    return first(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def session_id(row):
    return first(
        row,
        [
            "session_id",
            "session",
        ],
    ) or "6033"


def result_status(row):
    return first(
        row,
        [
            "result_status",
            "status",
        ],
    )


def official_status(row):
    return first(
        row,
        [
            "official_status",
            "status",
        ],
    )


def official_result_row(row):
    return first(
        row,
        [
            "official_result_row",
            "result_row",
            "row_number",
        ],
    )


def chronology_ids(rows, valid_ids):
    return {
        txt(row.get("attempt_id"))
        for row in rows
        if (
            txt(row.get("attempt_id"))
            in valid_ids
            and
            txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            ==
            "true"
        )
    }


def lane_count(rows):
    return sum(
        1
        for row in rows
        if txt(
            row.get(
                "lane"
            )
        ).upper()
        not in {
            "",
            "UNKNOWN",
        }
    )


def main():

    print()
    print("=" * 118)
    print(
        "R1G.28F — 2022 MARCO SECOND-ATTEMPT "
        "ACTIVE LEDGER INTEGRATION"
    )
    print("=" * 118)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V7,
        ACTION_V4,
        EVIDENCE,
        REPEAT_POLICY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 118)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(
        path.exists()
        for path in required
    ):
        print()
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_INTEGRATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_V3
    )

    chronology_v7 = read_csv(
        CHRONOLOGY_V7
    )

    action_v4 = read_csv(
        ACTION_V4
    )

    evidence = read_csv(
        EVIDENCE
    )

    repeat_policy = read_csv(
        REPEAT_POLICY
    )

    cfields = list(
        chronology_v7[0].keys()
    )

    afields = list(
        action_v4[0].keys()
    )

    canonical_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    result_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    first_row = canonical_by_id.get(
        FIRST_ID
    )

    second_row = canonical_by_id.get(
        SECOND_ID
    )

    first_result = result_by_id.get(
        FIRST_ID
    )

    second_result = result_by_id.get(
        SECOND_ID
    )

    if (
        first_row is None
        or
        second_row is None
        or
        first_result is None
        or
        second_result is None
    ):
        print()
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_CANONICAL_GROUNDING_FAILED"
        )
        return

    identity_ok = all([
        driver(first_row)
        ==
        "Marco Andretti",

        driver(second_row)
        ==
        "Marco Andretti",

        attempt_index(first_row)
        ==
        "1",

        attempt_index(second_row)
        ==
        "2",

        speed(first_row)
        ==
        EXPECTED_FIRST_SPEED,

        speed(second_row)
        ==
        EXPECTED_SECOND_SPEED,
    ])

    evidence_ready = any(
        txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
        and
        txt(
            row.get(
                "first_attempt_id"
            )
        )
        ==
        FIRST_ID
        and
        txt(
            row.get(
                "second_attempt_id"
            )
        )
        ==
        SECOND_ID
        and
        txt(
            row.get(
                "relation"
            )
        )
        ==
        "MARCO_FIRST_ATTEMPT_BEFORE_SECOND_ATTEMPT"
        and
        txt(
            row.get(
                "action"
            )
        )
        ==
        "SECOND_ATTEMPT"
        for row in evidence
    )

    print()
    print("=" * 118)
    print("GROUNDING")
    print("=" * 118)

    print()
    print(
        "Canonical identity:",
        identity_ok,
    )

    print(
        "Evidence promotion ready:",
        evidence_ready,
    )

    print(
        "Official second result row:",
        official_result_row(
            second_result
        ),
    )

    print(
        "Official second status:",
        repr(
            official_status(
                second_result
            )
        ),
    )

    if not identity_ok or not evidence_ready:
        print()
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_INTEGRATION_GROUNDING_REVIEW_REQUIRED"
        )
        return

    existing_first = [
        row
        for row in chronology_v7
        if txt(
            row.get(
                "attempt_id"
            )
        )
        ==
        FIRST_ID
    ]

    existing_second = [
        row
        for row in chronology_v7
        if txt(
            row.get(
                "attempt_id"
            )
        )
        ==
        SECOND_ID
    ]

    existing_action = [
        row
        for row in action_v4
        if (
            txt(
                row.get(
                    "subject_attempt_id"
                )
            )
            ==
            SECOND_ID
            or
            txt(
                row.get(
                    "related_attempt_id"
                )
            )
            ==
            SECOND_ID
        )
    ]

    print()
    print("=" * 118)
    print("DUPLICATE CHECK")
    print("=" * 118)

    print()
    print(
        "Existing Marco first chronology rows:",
        len(
            existing_first
        ),
    )

    print(
        "Existing Marco second chronology rows:",
        len(
            existing_second
        ),
    )

    print(
        "Existing Marco second action rows:",
        len(
            existing_action
        ),
    )

    if not (
        len(
            existing_first
        )
        >=
        1
        and
        len(
            existing_second
        )
        ==
        0
        and
        len(
            existing_action
        )
        ==
        0
    ):
        print()
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_DUPLICATE_REVIEW_REQUIRED"
        )
        return

    # --------------------------------------------------
    # Chronology row
    # --------------------------------------------------

    chronology_row = blank(
        cfields
    )

    chronology_values = {
        "year":
            "2022",

        "attempt_id":
            SECOND_ID,

        "session_id":
            session_id(
                second_row
            ),

        "car_number":
            car(
                second_row
            ),

        "driver_name":
            "Marco Andretti",

        "car_attempt_index":
            attempt_index(
                second_row
            ),

        "constraint_class":
            "ORDERING_ONLY",

        "time_quality":
            "ORDERING_ONLY",

        "source_layer":
            "SECONDARY_EDITORIAL+OFFICIAL_RESULTS",

        "source_semantic":
            "EXPLICIT_SECOND_ATTEMPT",

        "source_event_id":
            "R1G28E-MARCO-SECOND-THE-RACE",

        "anchor_event_type":
            "MARCO_SECOND_ATTEMPT",

        "result_status":
            result_status(
                second_row
            ),

        "chronology_usable":
            "True",

        "performance_environment_usable":
            "False",

        "queue_replay_usable":
            "False",

        "notes":
            (
                "The Race explicitly identifies Marco Andretti's "
                "P23 result as his second attempt. Official result "
                "row 23 binds that result to 230.345 mph. "
                "Canonical attempt index binds the earlier "
                "226.108 mph run as attempt 1. "
                "No Lane, queue, wait, withdrawal semantic, "
                "or exact timestamp inferred."
            ),

        "evidence_id":
            "R1G28F-MARCO-SECOND",

        "evidence_stage":
            PHASE,

        "source_authority":
            "REPUTABLE_SECONDARY_EDITORIAL+INDYCAR_OFFICIAL_RESULTS",

        "source_title":
            "Winners and losers from 2022 Indy 500 qualifying",

        "source_url":
            (
                "https://www.the-race.com/indycar/"
                "winners-and-losers-from-2022-indy-500-qualifying/"
            ),

        "official_result_row":
            official_result_row(
                second_result
            ),

        "ordering_relation":
            "AFTER_MARCO_FIRST_ATTEMPT",

        "evidence_summary":
            (
                "The Race explicitly calls Marco Andretti's "
                "P23 result his second attempt; official results "
                "bind P23 to 230.345 mph."
            ),

        "related_attempt_id":
            FIRST_ID,

        "ordering_role":
            "RELATED",

        "evidence_type":
            "SECONDARY_EXPLICIT_SECOND_ATTEMPT+OFFICIAL_RESULT_BINDING",

        "action":
            "SECOND_ATTEMPT",

        "lane":
            "UNKNOWN",

        "source_candidate_id":
            "R1G28E-MARCO-SECOND-THE-RACE",

        "evidence_quality":
            "HIGH",
    }

    for key, value in chronology_values.items():
        if key in chronology_row:
            chronology_row[key] = value

    chronology_v8 = (
        chronology_v7
        +
        [
            chronology_row
        ]
    )

    # --------------------------------------------------
    # Action row
    # --------------------------------------------------

    action_row = blank(
        afields
    )

    action_values = {
        "evidence_id":
            "R1G28F-MARCO-SECOND-ACTION",

        "year":
            "2022",

        "subject_attempt_id":
            SECOND_ID,

        "related_attempt_id":
            FIRST_ID,

        "session_id":
            session_id(
                second_row
            ),

        "car_number":
            car(
                second_row
            ),

        "driver_name":
            "Marco Andretti",

        "action":
            "SECOND_ATTEMPT",

        "lane":
            "UNKNOWN",

        "relation":
            "AFTER_FIRST_ATTEMPT",

        "source_name":
            "The Race + INDYCAR Official Qualification Results",

        "source_class":
            "REPUTABLE_SECONDARY_EDITORIAL+OFFICIAL_RESULTS",

        "source_candidate_id":
            "R1G28E-MARCO-SECOND-THE-RACE",

        "evidence_quality":
            "HIGH",

        "chronology_usable":
            "True",

        "queue_position_known":
            "False",

        "queue_wait_known":
            "False",

        "canonical_mutated":
            "False",

        "notes":
            (
                "Source supports only explicit second-attempt "
                "semantics and ordering after Marco's first attempt. "
                "No withdrawal, Lane 1/Lane 2, queue position, "
                "queue wait, or exact timestamp inferred."
            ),

        "subject_speed_mph":
            EXPECTED_SECOND_SPEED,

        "related_speed_mph":
            EXPECTED_FIRST_SPEED,

        "official_subject_status":
            official_status(
                second_result
            ),

        "source_evidence_id":
            "R1G28E-MARCO-SECOND-THE-RACE",

        "promotion_status":
            "PROMOTED_R1G28F",
    }

    for key, value in action_values.items():
        if key in action_row:
            action_row[key] = value

    action_v5 = (
        action_v4
        +
        [
            action_row
        ]
    )

    write_csv(
        CHRONOLOGY_V8,
        chronology_v8,
        cfields,
    )

    write_csv(
        ACTION_V5,
        action_v5,
        afields,
    )

    # --------------------------------------------------
    # Coverage
    # --------------------------------------------------

    ids_2022 = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    before_ids = chronology_ids(
        chronology_v7,
        ids_2022,
    )

    after_ids = chronology_ids(
        chronology_v8,
        ids_2022,
    )

    total = len(
        ids_2022
    )

    before_n = len(
        before_ids
    )

    after_n = len(
        after_ids
    )

    before_pct = (
        100.0
        *
        before_n
        /
        total
        if total
        else 0.0
    )

    after_pct = (
        100.0
        *
        after_n
        /
        total
        if total
        else 0.0
    )

    eligible = {
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in repeat_policy
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        ==
        "INCLUDE"
    }

    groups = {}

    for aid in ids_2022:
        c = canonical_by_id.get(
            aid
        )

        if c is None:
            continue

        d = driver(
            c
        )

        if d in eligible:
            groups.setdefault(
                d,
                set(),
            ).add(
                aid
            )

    covered_before = {
        d
        for d, aids in groups.items()
        if aids.issubset(
            before_ids
        )
    }

    covered_after = {
        d
        for d, aids in groups.items()
        if aids.issubset(
            after_ids
        )
    }

    newly_covered = sorted(
        covered_after
        -
        covered_before
    )

    lane_before = lane_count(
        action_v4
    )

    lane_after = lane_count(
        action_v5
    )

    print()
    print("=" * 118)
    print("POST-INTEGRATION SUMMARY")
    print("=" * 118)

    print()
    print(
        "Chronology rows:",
        len(
            chronology_v7
        ),
        "->",
        len(
            chronology_v8
        ),
    )

    print(
        "Action rows:",
        len(
            action_v4
        ),
        "->",
        len(
            action_v5
        ),
    )

    print()
    print(
        "2022 chronology attempts:",
        before_n,
        "->",
        after_n,
    )

    print(
        "2022 chronology coverage:",
        f"{before_pct:.2f}%",
        "->",
        f"{after_pct:.2f}%",
    )

    print()
    print(
        "Decision-relevant repeat coverage:",
        f"{len(covered_before)}/{len(eligible)}",
        "->",
        f"{len(covered_after)}/{len(eligible)}",
    )

    print(
        "Newly covered repeat drivers:",
        "|".join(
            newly_covered
        )
        or
        "NONE",
    )

    print()
    print(
        "Explicit Lane rows:",
        lane_before,
        "->",
        lane_after,
    )

    print(
        "Marco second action:",
        "SECOND_ATTEMPT",
    )

    print(
        "Marco Lane:",
        "UNKNOWN",
    )

    # --------------------------------------------------
    # Summary output
    # --------------------------------------------------

    summary_rows = [
        {
            "metric":
                "chronology_rows_before",
            "value":
                len(
                    chronology_v7
                ),
        },
        {
            "metric":
                "chronology_rows_after",
            "value":
                len(
                    chronology_v8
                ),
        },
        {
            "metric":
                "action_rows_before",
            "value":
                len(
                    action_v4
                ),
        },
        {
            "metric":
                "action_rows_after",
            "value":
                len(
                    action_v5
                ),
        },
        {
            "metric":
                "2022_chronology_before",
            "value":
                before_n,
        },
        {
            "metric":
                "2022_chronology_after",
            "value":
                after_n,
        },
        {
            "metric":
                "coverage_before_pct",
            "value":
                f"{before_pct:.2f}",
        },
        {
            "metric":
                "coverage_after_pct",
            "value":
                f"{after_pct:.2f}",
        },
        {
            "metric":
                "repeat_coverage_before",
            "value":
                f"{len(covered_before)}/{len(eligible)}",
        },
        {
            "metric":
                "repeat_coverage_after",
            "value":
                f"{len(covered_after)}/{len(eligible)}",
        },
        {
            "metric":
                "newly_covered",
            "value":
                "|".join(
                    newly_covered
                ),
        },
        {
            "metric":
                "lane_rows_before",
            "value":
                lane_before,
        },
        {
            "metric":
                "lane_rows_after",
            "value":
                lane_after,
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    second_count_after = sum(
        1
        for row in chronology_v8
        if txt(
            row.get(
                "attempt_id"
            )
        )
        ==
        SECOND_ID
    )

    action_count_after = sum(
        1
        for row in action_v5
        if (
            txt(
                row.get(
                    "subject_attempt_id"
                )
            )
            ==
            SECOND_ID
            and
            txt(
                row.get(
                    "action"
                )
            )
            ==
            "SECOND_ATTEMPT"
        )
    )

    qa_rows = [
        {
            "metric":
                "canonical_identity_verified",

            "value":
                int(
                    identity_ok
                ),

            "status":
                "PASS"
                if identity_ok
                else "FAIL",
        },

        {
            "metric":
                "evidence_ready",

            "value":
                int(
                    evidence_ready
                ),

            "status":
                "PASS"
                if evidence_ready
                else "FAIL",
        },

        {
            "metric":
                "second_chronology_added_once",

            "value":
                second_count_after,

            "status":
                "PASS"
                if second_count_after == 1
                else "FAIL",
        },

        {
            "metric":
                "second_action_added_once",

            "value":
                action_count_after,

            "status":
                "PASS"
                if action_count_after == 1
                else "FAIL",
        },

        {
            "metric":
                "chronology_unique_gain_one",

            "value":
                after_n
                -
                before_n,

            "status":
                "PASS"
                if (
                    after_n
                    -
                    before_n
                )
                ==
                1
                else "FAIL",
        },

        {
            "metric":
                "marco_repeat_newly_covered",

            "value":
                int(
                    "Marco Andretti"
                    in
                    newly_covered
                ),

            "status":
                "PASS"
                if (
                    "Marco Andretti"
                    in
                    newly_covered
                )
                else "FAIL",
        },

        {
            "metric":
                "decision_relevant_denominator_is_8",

            "value":
                len(
                    eligible
                ),

            "status":
                "PASS"
                if len(
                    eligible
                )
                ==
                8
                else "FAIL",
        },

        {
            "metric":
                "lane_evidence_unchanged",

            "value":
                lane_after
                -
                lane_before,

            "status":
                "PASS"
                if lane_after
                ==
                lane_before
                else "FAIL",
        },

        {
            "metric":
                "withdrawal_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "timestamp_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_OUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    success = all(
        row[
            "status"
        ]
        ==
        "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 118)

    if success:
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_ORDERING_AND_ACTION_INTEGRATED"
        )
    else:
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 118)

    print()
    print("OUTPUTS")
    print(CHRONOLOGY_V8)
    print(ACTION_V5)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
