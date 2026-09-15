from pathlib import Path
import csv


PHASE = "R2B.2"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V7 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v7.csv"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_rossi_lane1_evidence_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_rossi_lane1_evidence_v1_qa.csv"
)


DRIVER = "Alexander Rossi"

FIRST_SPEED = "231.341"
SECOND_SPEED = "230.812"

SOURCE_NAME = "Autosport"

SOURCE_CLASS = (
    "REPUTABLE_SECONDARY_EDITORIAL"
)

SOURCE_TITLE = (
    "Indy 500: Sato, Grosjean, Johnson into top 12 fight"
)

SOURCE_DATE_LABEL = "EDITED"

SOURCE_DATE_DISPLAY = (
    "May 22, 2022, 2:31 AM"
)

SOURCE_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-"
    "p13-33-set/10308540/"
)

SOURCE_QUOTE = (
    "Alexander Rossi elected to go to lane one - "
    "the priority lane - for his second run"
)


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


def speed(row):
    return first(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
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


def main():

    print()
    print("=" * 118)
    print(
        "R2B.2 — 2022 ALEXANDER ROSSI "
        "LANE 1 EVIDENCE CAPTURE + ADJUDICATION"
    )
    print("=" * 118)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V10,
        ACTION_V7,
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
            "ROSSI_LANE1_CAPTURE_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V10)
    action = read_csv(ACTION_V7)

    # --------------------------------------------------
    # Resolve Rossi attempt IDs from canonical identity
    # and speeds rather than hardcoding UUIDs.
    # --------------------------------------------------

    rossi_rows = [
        row
        for row in canonical
        if (
            txt(row.get("year")) == "2022"
            and
            driver(row) == DRIVER
        )
    ]

    first_matches = [
        row
        for row in rossi_rows
        if (
            attempt_index(row) == "1"
            and
            speed(row) == FIRST_SPEED
        )
    ]

    second_matches = [
        row
        for row in rossi_rows
        if (
            attempt_index(row) == "2"
            and
            speed(row) == SECOND_SPEED
        )
    ]

    if (
        len(first_matches) != 1
        or
        len(second_matches) != 1
    ):
        print()
        print(
            "Rossi canonical rows:",
            len(rossi_rows),
        )

        print(
            "First matches:",
            len(first_matches),
        )

        print(
            "Second matches:",
            len(second_matches),
        )

        print()
        print(
            "FINAL STATUS: "
            "ROSSI_LANE1_CANONICAL_IDENTITY_REVIEW_REQUIRED"
        )
        return

    first_row = first_matches[0]
    second_row = second_matches[0]

    first_id = txt(
        first_row.get(
            "attempt_id"
        )
    )

    second_id = txt(
        second_row.get(
            "attempt_id"
        )
    )

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    first_result = result_by_id.get(
        first_id
    )

    second_result = result_by_id.get(
        second_id
    )

    if (
        first_result is None
        or
        second_result is None
    ):
        print()
        print(
            "FINAL STATUS: "
            "ROSSI_LANE1_RESULT_GROUNDING_FAILED"
        )
        return

    first_ok = all([
        driver(first_row) == DRIVER,
        attempt_index(first_row) == "1",
        speed(first_row) == FIRST_SPEED,
    ])

    second_ok = all([
        driver(second_row) == DRIVER,
        attempt_index(second_row) == "2",
        speed(second_row) == SECOND_SPEED,
    ])

    first_withdrawn = (
        official_status(
            first_result
        )
        ==
        "Withdrawn"
    )

    first_chrono = any(
        txt(row.get("attempt_id")) == first_id
        and
        txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        ==
        "true"
        for row in chronology
    )

    second_chrono = any(
        txt(row.get("attempt_id")) == second_id
        and
        txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        ==
        "true"
        for row in chronology
    )

    existing_lane_rows = [
        row
        for row in action
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

    print()
    print("=" * 118)
    print("CANONICAL / OFFICIAL GROUNDING")
    print("=" * 118)

    print()
    print(
        "First ID:",
        first_id,
    )

    print(
        "First:",
        FIRST_SPEED,
        "| index",
        attempt_index(first_row),
        "| official status",
        repr(
            official_status(
                first_result
            )
        ),
    )

    print()
    print(
        "Second ID:",
        second_id,
    )

    print(
        "Second:",
        SECOND_SPEED,
        "| index",
        attempt_index(second_row),
        "| official row",
        repr(
            official_result_row(
                second_result
            )
        ),
    )

    print()
    print(
        "First grounding:",
        first_ok,
    )

    print(
        "Second grounding:",
        second_ok,
    )

    print(
        "First official Withdrawn:",
        first_withdrawn,
    )

    print(
        "First chronology-covered:",
        first_chrono,
    )

    print(
        "Second chronology-covered:",
        second_chrono,
    )

    print(
        "Existing Rossi explicit Lane rows:",
        len(
            existing_lane_rows
        ),
    )

    print()
    print("=" * 118)
    print("SOURCE-NATIVE LANE EVIDENCE")
    print("=" * 118)

    print()
    print(
        "Source:",
        SOURCE_NAME,
    )

    print(
        "Title:",
        SOURCE_TITLE,
    )

    print(
        "Date label:",
        SOURCE_DATE_LABEL,
    )

    print(
        "Date display:",
        SOURCE_DATE_DISPLAY,
    )

    print()
    print(
        "Source-native quote:",
        repr(
            SOURCE_QUOTE
        ),
    )

    print()
    print(
        "Source semantics:"
    )

    print(
        "  driver = Alexander Rossi"
    )

    print(
        "  attempt = second run"
    )

    print(
        "  lane = Lane 1"
    )

    print(
        "  lane role = priority lane"
    )

    print(
        "  first existing time must be pulled"
    )

    print(
        "  second run failed to improve"
    )

    #
    # This evidence is unusually strong:
    #
    # Autosport explicitly binds:
    # Rossi -> second run -> Lane 1 -> priority lane.
    #
    # Official results independently mark the earlier
    # 231.341 result Withdrawn.
    #
    # We may therefore support Lane 1 and the withdrawal
    # semantics for the transition from attempt 1 to 2.
    #
    # We still do NOT infer:
    # queue wait, exact queue position beyond "priority
    # lane" semantics, exact timestamp, or number of cars
    # ahead.
    #

    promotion_ready = all([
        first_ok,
        second_ok,
        first_withdrawn,
        first_chrono,
        second_chrono,
        len(existing_lane_rows) == 0,
    ])

    relation = (
        "ROSSI_FIRST_RESULT_WITHDRAWN_BEFORE_SECOND_RUN_IN_LANE_1"
        if promotion_ready
        else
        "REVIEW_REQUIRED"
    )

    action_label = (
        "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1"
        if promotion_ready
        else
        "REVIEW_REQUIRED"
    )

    print()
    print("=" * 118)
    print("ADJUDICATION")
    print("=" * 118)

    print()
    print(
        "Promotion ready:",
        promotion_ready,
    )

    print(
        "Supported relation:",
        relation
        if promotion_ready
        else
        "NOT_YET",
    )

    print(
        "Supported action:",
        action_label
        if promotion_ready
        else
        "NOT_YET",
    )

    print(
        "Supported Lane:",
        "LANE_1"
        if promotion_ready
        else
        "UNKNOWN",
    )

    print()
    print(
        "Queue wait:",
        "UNKNOWN",
    )

    print(
        "Exact queue position:",
        "UNKNOWN",
    )

    print(
        "Exact timestamp:",
        "UNKNOWN",
    )

    evidence_rows = [
        {
            "evidence_id":
                "R2B2-ROSSI-LANE1-AUTOSPORT",

            "phase":
                PHASE,

            "year":
                "2022",

            "driver_name":
                DRIVER,

            "first_attempt_id":
                first_id,

            "first_speed_mph":
                FIRST_SPEED,

            "first_official_status":
                official_status(
                    first_result
                ),

            "second_attempt_id":
                second_id,

            "second_speed_mph":
                SECOND_SPEED,

            "second_official_result_row":
                official_result_row(
                    second_result
                ),

            "source_name":
                SOURCE_NAME,

            "source_class":
                SOURCE_CLASS,

            "source_title":
                SOURCE_TITLE,

            "source_date_label":
                SOURCE_DATE_LABEL,

            "source_date_display":
                SOURCE_DATE_DISPLAY,

            "source_url":
                SOURCE_URL,

            "source_quote":
                SOURCE_QUOTE,

            "source_semantic":
                "EXPLICIT_SECOND_RUN_LANE1_PRIORITY",

            "relation":
                relation,

            "action":
                action_label,

            "lane":
                (
                    "LANE_1"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "lane_role":
                (
                    "PRIORITY"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "queue_wait":
                "UNKNOWN",

            "exact_queue_position":
                "UNKNOWN",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Autosport explicitly identifies Alexander "
                    "Rossi choosing Lane 1, the priority lane, "
                    "for his second run. The source explains that "
                    "this requires pulling the first time. "
                    "Official results independently mark Rossi's "
                    "231.341 first result Withdrawn. No queue wait, "
                    "exact queue position, or exact timestamp inferred."
                ),
        }
    ]

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "evidence_id",
            "phase",
            "year",
            "driver_name",
            "first_attempt_id",
            "first_speed_mph",
            "first_official_status",
            "second_attempt_id",
            "second_speed_mph",
            "second_official_result_row",
            "source_name",
            "source_class",
            "source_title",
            "source_date_label",
            "source_date_display",
            "source_url",
            "source_quote",
            "source_semantic",
            "relation",
            "action",
            "lane",
            "lane_role",
            "queue_wait",
            "exact_queue_position",
            "exact_timestamp",
            "promotion_ready",
            "notes",
        ],
    )

    qa_rows = [
        {
            "metric":
                "first_grounding",
            "value":
                int(first_ok),
            "status":
                "PASS"
                if first_ok
                else "FAIL",
        },

        {
            "metric":
                "second_grounding",
            "value":
                int(second_ok),
            "status":
                "PASS"
                if second_ok
                else "FAIL",
        },

        {
            "metric":
                "first_official_withdrawn",
            "value":
                int(first_withdrawn),
            "status":
                "PASS"
                if first_withdrawn
                else "FAIL",
        },

        {
            "metric":
                "first_chronology_covered",
            "value":
                int(first_chrono),
            "status":
                "PASS"
                if first_chrono
                else "FAIL",
        },

        {
            "metric":
                "second_chronology_covered",
            "value":
                int(second_chrono),
            "status":
                "PASS"
                if second_chrono
                else "FAIL",
        },

        {
            "metric":
                "existing_explicit_rossi_lane_rows",
            "value":
                len(existing_lane_rows),
            "status":
                "PASS"
                if len(existing_lane_rows) == 0
                else "REVIEW",
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
                "exact_timestamp_inferred",
            "value":
                0,
            "status":
                "PASS",
        },

        {
            "metric":
                "ledger_mutation",
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

    print()
    print("=" * 118)

    if promotion_ready:
        print(
            "FINAL STATUS: "
            "ROSSI_SECOND_RUN_LANE1_EVIDENCE_PROMOTION_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "ROSSI_SECOND_RUN_LANE1_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 118)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
