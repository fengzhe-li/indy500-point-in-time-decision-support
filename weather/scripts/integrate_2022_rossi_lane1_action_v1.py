from pathlib import Path
import csv


PHASE = "R2B.3"

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V7 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v7.csv"
)

EVIDENCE = Path(
    "weather/output/"
    "lane_rescue_2022_rossi_lane1_evidence_v2.csv"
)

OUTPUT_DIR = Path("weather/output")

ACTION_V8 = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v8.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_rossi_lane1_integration_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_rossi_lane1_integration_v1_qa.csv"
)


FIRST_ID = "1e2facfd-2c67-5b5a-9556-04ef28eeb0d8"
SECOND_ID = "b3147013-0fda-5982-bea1-85788019ef89"

FIRST_SPEED = "231.341"
SECOND_SPEED = "230.812"

DRIVER = "Alexander Rossi"


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


def lane_count(rows):
    return sum(
        1
        for row in rows
        if txt(row.get("lane")).upper()
        not in {
            "",
            "UNKNOWN",
        }
    )


def lane_drivers(rows):
    return sorted({
        txt(row.get("driver_name"))
        for row in rows
        if txt(row.get("lane")).upper()
        not in {
            "",
            "UNKNOWN",
        }
        and
        txt(row.get("driver_name"))
    })


def main():

    print()
    print("=" * 118)
    print(
        "R2B.3 — 2022 ALEXANDER ROSSI "
        "LANE 1 ACTION-LEDGER INTEGRATION"
    )
    print("=" * 118)

    required = [
        CHRONOLOGY_V10,
        ACTION_V7,
        EVIDENCE,
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
            "ROSSI_LANE1_INTEGRATION_INPUT_MISSING"
        )
        return

    chronology = read_csv(
        CHRONOLOGY_V10
    )

    action_v7 = read_csv(
        ACTION_V7
    )

    evidence = read_csv(
        EVIDENCE
    )

    afields = list(
        action_v7[0].keys()
    )

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
                "driver_name"
            )
        )
        ==
        DRIVER
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
                "lane"
            )
        )
        ==
        "LANE_1"
        and
        txt(
            row.get(
                "action"
            )
        )
        ==
        "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1"
        for row in evidence
    )

    first_chrono = [
        row
        for row in chronology
        if (
            txt(
                row.get(
                    "attempt_id"
                )
            )
            ==
            FIRST_ID
            and
            txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            ==
            "true"
        )
    ]

    second_chrono = [
        row
        for row in chronology
        if (
            txt(
                row.get(
                    "attempt_id"
                )
            )
            ==
            SECOND_ID
            and
            txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            ==
            "true"
        )
    ]

    existing_lane_rows = [
        row
        for row in action_v7
        if (
            txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            DRIVER
            and
            txt(
                row.get(
                    "lane"
                )
            ).upper()
            not in {
                "",
                "UNKNOWN",
            }
        )
    ]

    existing_transition_rows = [
        row
        for row in action_v7
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
                    "related_attempt_id"
                )
            )
            ==
            FIRST_ID
        )
    ]

    print()
    print("=" * 118)
    print("GROUNDING / DUPLICATE CHECK")
    print("=" * 118)

    print()
    print(
        "Evidence promotion ready:",
        evidence_ready,
    )

    print(
        "First chronology rows:",
        len(
            first_chrono
        ),
    )

    print(
        "Second chronology rows:",
        len(
            second_chrono
        ),
    )

    print(
        "Existing Rossi explicit Lane rows:",
        len(
            existing_lane_rows
        ),
    )

    print(
        "Existing Rossi transition rows:",
        len(
            existing_transition_rows
        ),
    )

    if not (
        evidence_ready
        and
        len(
            first_chrono
        )
        >=
        1
        and
        len(
            second_chrono
        )
        >=
        1
        and
        len(
            existing_lane_rows
        )
        ==
        0
        and
        len(
            existing_transition_rows
        )
        ==
        0
    ):
        print()
        print(
            "FINAL STATUS: "
            "ROSSI_LANE1_INTEGRATION_REVIEW_REQUIRED"
        )
        return

    lane_before = lane_count(
        action_v7
    )

    drivers_before = lane_drivers(
        action_v7
    )

    row = blank(
        afields
    )

    values = {
        "evidence_id":
            "R2B3-ROSSI-LANE1-ACTION",

        "year":
            "2022",

        "subject_attempt_id":
            SECOND_ID,

        "related_attempt_id":
            FIRST_ID,

        "session_id":
            "6033",

        "car_number":
            "27",

        "driver_name":
            DRIVER,

        "action":
            "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1",

        "lane":
            "LANE_1",

        "relation":
            "AFTER_WITHDRAWN_FIRST_ATTEMPT",

        "source_name":
            "Autosport + INDYCAR Official Qualification Results",

        "source_class":
            "REPUTABLE_SECONDARY_EDITORIAL+OFFICIAL_RESULTS",

        "source_candidate_id":
            "R2B2A-ROSSI-LANE1-AUTOSPORT",

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
                "Autosport explicitly identifies Alexander Rossi "
                "choosing Lane 1, the priority lane, for his second "
                "run. Official result-match V3 marks the prior "
                "231.341 result Withdrawn. The second run is "
                "230.812. Lane 1 is directly supported. "
                "Exact queue position, number of cars ahead, "
                "queue wait, and exact timestamp remain UNKNOWN."
            ),

        "subject_speed_mph":
            SECOND_SPEED,

        "related_speed_mph":
            FIRST_SPEED,

        "official_subject_status":
            "",

        "source_evidence_id":
            "R2B2A-ROSSI-LANE1-AUTOSPORT",

        "promotion_status":
            "PROMOTED_R2B3",
    }

    for key, value in values.items():
        if key in row:
            row[key] = value

    action_v8 = (
        action_v7
        +
        [row]
    )

    write_csv(
        ACTION_V8,
        action_v8,
        afields,
    )

    lane_after = lane_count(
        action_v8
    )

    drivers_after = lane_drivers(
        action_v8
    )

    rossi_after = [
        r
        for r in action_v8
        if (
            txt(
                r.get(
                    "driver_name"
                )
            )
            ==
            DRIVER
            and
            txt(
                r.get(
                    "lane"
                )
            )
            ==
            "LANE_1"
            and
            txt(
                r.get(
                    "subject_attempt_id"
                )
            )
            ==
            SECOND_ID
        )
    ]

    print()
    print("=" * 118)
    print("POST-INTEGRATION SUMMARY")
    print("=" * 118)

    print()
    print(
        "Action rows:",
        len(
            action_v7
        ),
        "->",
        len(
            action_v8
        ),
    )

    print(
        "Chronology ledger:",
        "V10 unchanged",
    )

    print()
    print(
        "Explicit historical Lane rows:",
        lane_before,
        "->",
        lane_after,
    )

    print(
        "Drivers with explicit Lane before:",
        "|".join(
            drivers_before
        )
        or
        "NONE",
    )

    print(
        "Drivers with explicit Lane after:",
        "|".join(
            drivers_after
        )
        or
        "NONE",
    )

    print()
    print(
        "Rossi action:",
        "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1",
    )

    print(
        "Rossi Lane:",
        "LANE_1",
    )

    print(
        "Queue wait:",
        "UNKNOWN",
    )

    print(
        "Exact queue position:",
        "UNKNOWN",
    )

    summary_rows = [
        {
            "metric":
                "chronology_ledger",
            "value":
                "V10_UNCHANGED",
        },
        {
            "metric":
                "action_rows_before",
            "value":
                len(
                    action_v7
                ),
        },
        {
            "metric":
                "action_rows_after",
            "value":
                len(
                    action_v8
                ),
        },
        {
            "metric":
                "explicit_lane_rows_before",
            "value":
                lane_before,
        },
        {
            "metric":
                "explicit_lane_rows_after",
            "value":
                lane_after,
        },
        {
            "metric":
                "lane_drivers_before",
            "value":
                "|".join(
                    drivers_before
                ),
        },
        {
            "metric":
                "lane_drivers_after",
            "value":
                "|".join(
                    drivers_after
                ),
        },
        {
            "metric":
                "rossi_lane",
            "value":
                "LANE_1",
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
                "evidence_ready",

            "value":
                int(
                    evidence_ready
                ),

            "status":
                "PASS"
                if evidence_ready
                else
                "FAIL",
        },

        {
            "metric":
                "first_chronology_exists",

            "value":
                len(
                    first_chrono
                ),

            "status":
                "PASS"
                if len(
                    first_chrono
                )
                >=
                1
                else
                "FAIL",
        },

        {
            "metric":
                "second_chronology_exists",

            "value":
                len(
                    second_chrono
                ),

            "status":
                "PASS"
                if len(
                    second_chrono
                )
                >=
                1
                else
                "FAIL",
        },

        {
            "metric":
                "rossi_lane_added_once",

            "value":
                len(
                    rossi_after
                ),

            "status":
                "PASS"
                if len(
                    rossi_after
                )
                ==
                1
                else
                "FAIL",
        },

        {
            "metric":
                "lane_row_gain_one",

            "value":
                lane_after
                -
                lane_before,

            "status":
                "PASS"
                if (
                    lane_after
                    -
                    lane_before
                )
                ==
                1
                else
                "FAIL",
        },

        {
            "metric":
                "explicit_lane_rows_now_two",

            "value":
                lane_after,

            "status":
                "PASS"
                if lane_after
                ==
                2
                else
                "FAIL",
        },

        {
            "metric":
                "rossi_and_mclaughlin_both_present",

            "value":
                int(
                    DRIVER
                    in
                    drivers_after
                    and
                    "Scott McLaughlin"
                    in
                    drivers_after
                ),

            "status":
                "PASS"
                if (
                    DRIVER
                    in
                    drivers_after
                    and
                    "Scott McLaughlin"
                    in
                    drivers_after
                )
                else
                "FAIL",
        },

        {
            "metric":
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "exact_queue_position_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "chronology_mutated",

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
            "ROSSI_LANE1_ACTION_INTEGRATED_EXPLICIT_LANE_ROWS_2"
        )
    else:
        print(
            "FINAL STATUS: "
            "ROSSI_LANE1_ACTION_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 118)

    print()
    print("OUTPUTS")
    print(ACTION_V8)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
