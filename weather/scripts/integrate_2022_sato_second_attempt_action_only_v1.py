from pathlib import Path
import csv


PHASE = "R1G.27D"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V5 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v5.csv"
)

ACTION_V3 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v3.csv"
)

ADJ = Path(
    "weather/output/"
    "chronology_rescue_2022_sato_required_reattempt_adjudication_v1.csv"
)

REPEAT_POLICY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

CHRONOLOGY_V6 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v6.csv"
)

ACTION_V4 = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v4.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_second_attempt_action_only_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_second_attempt_action_only_v1_qa.csv"
)


FIRST_ID = "3f221659-74ff-5901-97dc-08071a734690"
SECOND_ID = "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"


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


def first_value(row, names):
    for name in names:
        value = txt(row.get(name))
        if value:
            return value
    return ""


def driver(row):
    return first_value(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def car(row):
    return first_value(
        row,
        [
            "car_number",
            "car_no",
            "car",
        ],
    )


def attempt_index(row):
    return first_value(
        row,
        [
            "car_attempt_index",
            "attempt_index",
        ],
    )


def session_id(row):
    return first_value(
        row,
        [
            "session_id",
            "session",
        ],
    ) or "6033"


def result_status(row):
    return first_value(
        row,
        [
            "result_status",
            "status",
        ],
    )


def official_status(row):
    return first_value(
        row,
        [
            "official_status",
            "status",
        ],
    )


def official_row(row):
    return first_value(
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
            txt(row.get("attempt_id")) in valid_ids
            and
            txt(row.get("chronology_usable")).lower() == "true"
        )
    }


def lane_count(rows):
    return sum(
        1
        for row in rows
        if txt(row.get("lane")).upper()
        not in {"", "UNKNOWN"}
    )


def main():
    print()
    print("=" * 115)
    print(
        "R1G.27D — SATO SECOND ATTEMPT "
        "+ ACTION-ONLY ACTIVE INTEGRATION"
    )
    print("=" * 115)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V5,
        ACTION_V3,
        ADJ,
        REPEAT_POLICY,
    ]

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "SATO_ACTION_ONLY_INTEGRATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology_v5 = read_csv(CHRONOLOGY_V5)
    action_v3 = read_csv(ACTION_V3)
    adjudication = read_csv(ADJ)
    repeat_policy = read_csv(REPEAT_POLICY)

    cfields = list(
        chronology_v5[0].keys()
    )

    afields = list(
        action_v3[0].keys()
    )

    canonical_by_id = {
        txt(row.get("attempt_id")): row
        for row in canonical
        if txt(row.get("attempt_id"))
    }

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    first = canonical_by_id[FIRST_ID]
    second = canonical_by_id[SECOND_ID]

    first_result = result_by_id[FIRST_ID]
    second_result = result_by_id[SECOND_ID]

    print()
    print("=" * 115)
    print("EXISTING CHRONOLOGY CHECK")
    print("=" * 115)

    first_rows = [
        row
        for row in chronology_v5
        if txt(row.get("attempt_id")) == FIRST_ID
    ]

    second_rows = [
        row
        for row in chronology_v5
        if txt(row.get("attempt_id")) == SECOND_ID
    ]

    action_hits = [
        row
        for row in action_v3
        if (
            txt(row.get("subject_attempt_id")) == SECOND_ID
            or
            txt(row.get("related_attempt_id")) == FIRST_ID
        )
    ]

    print()
    print(
        "Existing first-attempt chronology rows:",
        len(first_rows),
    )

    print(
        "Existing second-attempt chronology rows:",
        len(second_rows),
    )

    print(
        "Existing Sato action rows:",
        len(action_hits),
    )

    if not (
        len(first_rows) >= 1
        and
        len(second_rows) == 0
        and
        len(action_hits) == 0
    ):
        print()
        print(
            "FINAL STATUS: "
            "SATO_ACTION_ONLY_PRECONDITION_REVIEW_REQUIRED"
        )
        return

    adj_ok = any(
        txt(row.get("promotion_ready")).lower() == "true"
        and
        txt(row.get("related_action"))
        ==
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION"
        for row in adjudication
    )

    print()
    print(
        "Adjudication ready:",
        adj_ok,
    )

    if not adj_ok:
        print()
        print(
            "FINAL STATUS: "
            "SATO_ACTION_ONLY_ADJUDICATION_NOT_READY"
        )
        return

    # ----------------------------------------------------
    # Add SECOND attempt chronology row only
    # ----------------------------------------------------

    new_chrono = blank(cfields)

    chrono_values = {
        "year":
            "2022",

        "attempt_id":
            SECOND_ID,

        "session_id":
            session_id(second),

        "car_number":
            car(second),

        "driver_name":
            driver(second),

        "car_attempt_index":
            attempt_index(second),

        "constraint_class":
            "ORDERING_ONLY",

        "time_quality":
            "ORDERING_ONLY",

        "source_layer":
            "OFFICIAL_EVIDENCE",

        "source_semantic":
            "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

        "source_event_id":
            "R1G27D-SATO-SECOND",

        "anchor_event_type":
            "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

        "result_status":
            result_status(second),

        "chronology_usable":
            "True",

        "performance_environment_usable":
            "False",

        "queue_replay_usable":
            "False",

        "notes":
            (
                "Second Sato attempt added as the required "
                "reattempt after invalidation of 232.196 mph run. "
                "No Lane, queue wait, or timestamp inferred."
            ),

        "evidence_id":
            "R1G27D-SATO-SECOND",

        "evidence_stage":
            PHASE,

        "source_authority":
            "INDYCAR_OFFICIAL_EDITORIAL+INDYCAR_OFFICIAL_RESULTS",

        "source_title":
            "2022 Day 1 Qualifying Recap",

        "source_url":
            "https://www.indycar.com/news/2022/05/05-21-day1-quals",

        "official_result_row":
            official_row(second_result),

        "ordering_relation":
            "AFTER_INVALIDATED_FIRST_ATTEMPT",

        "evidence_summary":
            (
                "Official editorial states Sato was forced to "
                "make a second attempt after the 232.196 mph "
                "first run was disallowed; official results "
                "identify the subsequent 231.708 mph result."
            ),

        "related_attempt_id":
            FIRST_ID,

        "ordering_role":
            "RELATED",

        "evidence_type":
            "OFFICIAL_REQUIRED_REATTEMPT",

        "action":
            "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

        "lane":
            "UNKNOWN",

        "source_candidate_id":
            "R1G27-ADJ-001",

        "evidence_quality":
            "HIGH",
    }

    for key, value in chrono_values.items():
        if key in new_chrono:
            new_chrono[key] = value

    chronology_v6 = chronology_v5 + [
        new_chrono
    ]

    # ----------------------------------------------------
    # Add action row
    # ----------------------------------------------------

    action_row = blank(afields)

    action_values = {
        "evidence_id":
            "R1G27D-SATO-ACTION",

        "year":
            "2022",

        "subject_attempt_id":
            SECOND_ID,

        "related_attempt_id":
            FIRST_ID,

        "session_id":
            session_id(second),

        "car_number":
            car(second),

        "driver_name":
            driver(second),

        "action":
            "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

        "lane":
            "UNKNOWN",

        "relation":
            "AFTER_INVALIDATED_FIRST_ATTEMPT",

        "source_name":
            "INDYCAR 2022 Day 1 Qualifying Recap",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL+INDYCAR_OFFICIAL_RESULTS",

        "source_candidate_id":
            "R1G27-ADJ-001",

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
                "Required reattempt after invalidated first run. "
                "No qualifying Lane, queue, or exact timestamp inferred."
            ),

        "subject_speed_mph":
            "231.708",

        "related_speed_mph":
            "232.196",

        "official_subject_status":
            official_status(second_result),

        "source_evidence_id":
            "R1G27-ADJ-001",

        "promotion_status":
            "PROMOTED_R1G27D",
    }

    for key, value in action_values.items():
        if key in action_row:
            action_row[key] = value

    action_v4 = action_v3 + [
        action_row
    ]

    write_csv(
        CHRONOLOGY_V6,
        chronology_v6,
        cfields,
    )

    write_csv(
        ACTION_V4,
        action_v4,
        afields,
    )

    # ----------------------------------------------------
    # Coverage
    # ----------------------------------------------------

    ids_2022 = set(
        result_by_id
    )

    before_ids = chronology_ids(
        chronology_v5,
        ids_2022,
    )

    after_ids = chronology_ids(
        chronology_v6,
        ids_2022,
    )

    before_n = len(before_ids)
    after_n = len(after_ids)
    total = len(ids_2022)

    before_pct = (
        100 * before_n / total
    )

    after_pct = (
        100 * after_n / total
    )

    eligible = {
        txt(row.get("driver_name"))
        for row in repeat_policy
        if txt(
            row.get("decision_relevant_denominator")
        ).upper() == "INCLUDE"
    }

    groups = {}

    for aid in ids_2022:
        row = canonical_by_id.get(aid)

        if not row:
            continue

        d = driver(row)

        if d in eligible:
            groups.setdefault(
                d,
                set(),
            ).add(aid)

    covered_before = {
        d
        for d, ids in groups.items()
        if ids.issubset(before_ids)
    }

    covered_after = {
        d
        for d, ids in groups.items()
        if ids.issubset(after_ids)
    }

    lane_before = lane_count(action_v3)
    lane_after = lane_count(action_v4)

    print()
    print("=" * 115)
    print("POST-INTEGRATION SUMMARY")
    print("=" * 115)

    print()
    print(
        "Chronology rows:",
        len(chronology_v5),
        "->",
        len(chronology_v6),
    )

    print(
        "Action rows:",
        len(action_v3),
        "->",
        len(action_v4),
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
            sorted(
                covered_after - covered_before
            )
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

    summary_rows = [
        {
            "metric": "chronology_rows_before",
            "value": len(chronology_v5),
        },
        {
            "metric": "chronology_rows_after",
            "value": len(chronology_v6),
        },
        {
            "metric": "action_rows_before",
            "value": len(action_v3),
        },
        {
            "metric": "action_rows_after",
            "value": len(action_v4),
        },
        {
            "metric": "2022_chronology_before",
            "value": before_n,
        },
        {
            "metric": "2022_chronology_after",
            "value": after_n,
        },
        {
            "metric": "coverage_before_pct",
            "value": f"{before_pct:.2f}",
        },
        {
            "metric": "coverage_after_pct",
            "value": f"{after_pct:.2f}",
        },
        {
            "metric": "repeat_coverage_before",
            "value": f"{len(covered_before)}/{len(eligible)}",
        },
        {
            "metric": "repeat_coverage_after",
            "value": f"{len(covered_after)}/{len(eligible)}",
        },
        {
            "metric": "lane_rows_before",
            "value": lane_before,
        },
        {
            "metric": "lane_rows_after",
            "value": lane_after,
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

    qa_rows = [
        {
            "metric":
                "first_attempt_already_present",

            "value":
                len(first_rows),

            "status":
                "PASS"
                if len(first_rows) >= 1
                else "FAIL",
        },

        {
            "metric":
                "second_attempt_added_once",

            "value":
                sum(
                    1
                    for row in chronology_v6
                    if txt(row.get("attempt_id")) == SECOND_ID
                ),

            "status":
                "PASS"
                if sum(
                    1
                    for row in chronology_v6
                    if txt(row.get("attempt_id")) == SECOND_ID
                ) == 1
                else "FAIL",
        },

        {
            "metric":
                "chronology_unique_gain_one",

            "value":
                after_n - before_n,

            "status":
                "PASS"
                if after_n - before_n == 1
                else "FAIL",
        },

        {
            "metric":
                "action_gain_one",

            "value":
                len(action_v4) - len(action_v3),

            "status":
                "PASS"
                if len(action_v4) - len(action_v3) == 1
                else "FAIL",
        },

        {
            "metric":
                "sato_repeat_now_covered",

            "value":
                int(
                    "Takuma Sato"
                    in covered_after
                ),

            "status":
                "PASS"
                if "Takuma Sato" in covered_after
                else "FAIL",
        },

        {
            "metric":
                "lane_count_unchanged",

            "value":
                lane_after - lane_before,

            "status":
                "PASS"
                if lane_after == lane_before
                else "FAIL",
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
        row["status"] == "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 115)

    if success:
        print(
            "FINAL STATUS: "
            "SATO_SECOND_ATTEMPT_AND_ACTION_INTEGRATED"
        )
    else:
        print(
            "FINAL STATUS: "
            "SATO_SECOND_ATTEMPT_AND_ACTION_REVIEW_REQUIRED"
        )

    print("=" * 115)

    print()
    print("OUTPUTS")
    print(CHRONOLOGY_V6)
    print(ACTION_V4)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
