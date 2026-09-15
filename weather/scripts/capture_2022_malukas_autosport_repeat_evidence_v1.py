from pathlib import Path
import csv


PHASE = "R1G.29B"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V8 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v8.csv"
)

OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_malukas_autosport_repeat_evidence_v1.csv"
)

QA_OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_malukas_autosport_repeat_evidence_v1_qa.csv"
)


FIRST_ID = "619575d3-e7eb-5cce-886f-0a8485b98eba"
SECOND_ID = "85c917fa-1c7a-52cb-a47f-468b4bdae9a5"

FIRST_SPEED = "231.233"
SECOND_SPEED = "231.607"

SOURCE_NAME = "Autosport"

SOURCE_CLASS = (
    "REPUTABLE_SECONDARY_EDITORIAL"
)

SOURCE_TITLE = (
    "Indy 500: Sato, Grosjean, Johnson into top 12 fight"
)

SOURCE_AUTHOR = "David Malsher-Lopez"

SOURCE_DATE_LABEL = "EDITED"

SOURCE_DATE_DISPLAY = (
    "May 22, 2022, 2:31 AM"
)

SOURCE_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-"
    "p13-33-set/10308540/"
)

# Keep quotations short.
QUOTE_QUEUE = (
    "put rookie David Malukas and veteran Takuma Sato in line"
)

QUOTE_IMPROVED = (
    "Rookie Malukas improved"
)


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(
            csv.DictReader(f)
        )


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
        value = txt(
            row.get(field)
        )

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
        "R1G.29B — AUTOSPORT MALUKAS "
        "REPEAT / IMPROVEMENT EVIDENCE CAPTURE"
    )
    print("=" * 118)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V8,
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
            "MALUKAS_AUTOSPORT_CAPTURE_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_V3
    )

    chronology = read_csv(
        CHRONOLOGY_V8
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
            "MALUKAS_AUTOSPORT_CANONICAL_GROUNDING_FAILED"
        )
        return

    first_ok = all([
        driver(first_row)
        ==
        "David Malukas",

        attempt_index(first_row)
        ==
        "1",

        speed(first_row)
        ==
        FIRST_SPEED,
    ])

    second_ok = all([
        driver(second_row)
        ==
        "David Malukas",

        attempt_index(second_row)
        ==
        "2",

        speed(second_row)
        ==
        SECOND_SPEED,
    ])

    first_status_ok = (
        official_status(
            first_result
        )
        ==
        "Retired"
    )

    second_final_binding_ok = all([
        official_result_row(
            second_result
        )
        ==
        "13",

        speed(
            second_row
        )
        ==
        SECOND_SPEED,
    ])

    first_in_v8 = any(
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
        for row in chronology
    )

    second_in_v8 = any(
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
        for row in chronology
    )

    improvement_delta = (
        float(
            SECOND_SPEED
        )
        -
        float(
            FIRST_SPEED
        )
    )

    delta_ok = (
        improvement_delta
        >
        0.0
    )

    print()
    print("=" * 118)
    print("CANONICAL / OFFICIAL GROUNDING")
    print("=" * 118)

    print()
    print(
        "First:",
        FIRST_ID,
        "| index",
        repr(
            attempt_index(
                first_row
            )
        ),
        "| speed",
        repr(
            speed(
                first_row
            )
        ),
        "| official status",
        repr(
            official_status(
                first_result
            )
        ),
    )

    print(
        "Second:",
        SECOND_ID,
        "| index",
        repr(
            attempt_index(
                second_row
            )
        ),
        "| speed",
        repr(
            speed(
                second_row
            )
        ),
        "| official result row",
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
        "First Retired status:",
        first_status_ok,
    )

    print(
        "Official P13 -> 231.607 binding:",
        second_final_binding_ok,
    )

    print(
        "Speed improvement:",
        f"{improvement_delta:.3f}",
        "mph",
    )

    print()
    print(
        "First already chronology-covered:",
        first_in_v8,
    )

    print(
        "Second already chronology-covered:",
        second_in_v8,
    )

    # --------------------------------------------------
    # Evidence semantics
    # --------------------------------------------------

    print()
    print("=" * 118)
    print("SOURCE-NATIVE EVIDENCE")
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

    print(
        "Author:",
        SOURCE_AUTHOR,
    )

    print()
    print(
        "Queue/run context quote:",
        repr(
            QUOTE_QUEUE
        ),
    )

    print(
        "Improvement quote:",
        repr(
            QUOTE_IMPROVED
        ),
    )

    print()
    print(
        "Interpretation:"
    )

    print(
        (
            "Autosport reports that after the initial "
            "qualifying sequence, Dale Coyne Racing put "
            "Malukas back in line, then explicitly states "
            "that Malukas improved."
        )
    )

    # --------------------------------------------------
    # Adjudication
    #
    # This supports:
    #   first attempt before later improvement run
    #   second/repeat attempt
    #   improved result
    #
    # This does NOT support:
    #   Lane 1 / Lane 2
    #   withdrawal of previous result
    #   queue position
    #   queue wait
    #   exact timestamp
    # --------------------------------------------------

    promotion_ready = all([
        first_ok,
        second_ok,
        first_status_ok,
        second_final_binding_ok,
        delta_ok,
        not first_in_v8,
        not second_in_v8,
    ])

    relation = (
        "MALUKAS_231.233_FIRST_ATTEMPT_BEFORE_231.607_IMPROVEMENT_RUN"
        if promotion_ready
        else
        "REVIEW_REQUIRED"
    )

    action = (
        "REPEAT_ATTEMPT_IMPROVED"
        if promotion_ready
        else
        "REVIEW_REQUIRED"
    )

    evidence_rows = [
        {
            "evidence_id":
                "R1G29B-MALUKAS-AUTOSPORT",

            "phase":
                PHASE,

            "year":
                "2022",

            "driver_name":
                "David Malukas",

            "car_number":
                "18",

            "first_attempt_id":
                FIRST_ID,

            "first_speed_mph":
                FIRST_SPEED,

            "first_official_status":
                official_status(
                    first_result
                ),

            "second_attempt_id":
                SECOND_ID,

            "second_speed_mph":
                SECOND_SPEED,

            "second_official_result_row":
                official_result_row(
                    second_result
                ),

            "improvement_mph":
                f"{improvement_delta:.3f}",

            "source_name":
                SOURCE_NAME,

            "source_class":
                SOURCE_CLASS,

            "source_title":
                SOURCE_TITLE,

            "source_author":
                SOURCE_AUTHOR,

            "source_date_label":
                SOURCE_DATE_LABEL,

            "source_date_display":
                SOURCE_DATE_DISPLAY,

            "source_url":
                SOURCE_URL,

            "source_quote_queue":
                QUOTE_QUEUE,

            "source_quote_improved":
                QUOTE_IMPROVED,

            "source_semantic":
                "REPEAT_RUN_IMPROVEMENT",

            "relation":
                relation,

            "action":
                action,

            "time_quality":
                (
                    "ORDERING_ONLY"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "queue_wait":
                "UNKNOWN",

            "exact_timestamp":
                "UNKNOWN",

            "withdrawal_semantic":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Autosport reports Malukas being put in line "
                    "during the retake sequence and then explicitly "
                    "states that he improved. Canonical attempt "
                    "index and official result grounding bind "
                    "231.233 as attempt 1 and 231.607 as attempt 2. "
                    "No Lane, withdrawal, queue position, queue wait, "
                    "or exact timestamp inferred."
                ),
        }
    ]

    write_csv(
        OUT,
        evidence_rows,
        [
            "evidence_id",
            "phase",
            "year",
            "driver_name",
            "car_number",
            "first_attempt_id",
            "first_speed_mph",
            "first_official_status",
            "second_attempt_id",
            "second_speed_mph",
            "second_official_result_row",
            "improvement_mph",
            "source_name",
            "source_class",
            "source_title",
            "source_author",
            "source_date_label",
            "source_date_display",
            "source_url",
            "source_quote_queue",
            "source_quote_improved",
            "source_semantic",
            "relation",
            "action",
            "time_quality",
            "lane",
            "queue_position",
            "queue_wait",
            "exact_timestamp",
            "withdrawal_semantic",
            "promotion_ready",
            "notes",
        ],
    )

    qa_rows = [
        {
            "metric":
                "first_grounding",

            "value":
                int(
                    first_ok
                ),

            "status":
                "PASS"
                if first_ok
                else "FAIL",
        },

        {
            "metric":
                "second_grounding",

            "value":
                int(
                    second_ok
                ),

            "status":
                "PASS"
                if second_ok
                else "FAIL",
        },

        {
            "metric":
                "first_retired_status",

            "value":
                int(
                    first_status_ok
                ),

            "status":
                "PASS"
                if first_status_ok
                else "FAIL",
        },

        {
            "metric":
                "official_p13_binding",

            "value":
                int(
                    second_final_binding_ok
                ),

            "status":
                "PASS"
                if second_final_binding_ok
                else "FAIL",
        },

        {
            "metric":
                "positive_speed_improvement",

            "value":
                f"{improvement_delta:.3f}",

            "status":
                "PASS"
                if delta_ok
                else "FAIL",
        },

        {
            "metric":
                "first_not_yet_in_v8",

            "value":
                int(
                    not first_in_v8
                ),

            "status":
                "PASS"
                if not first_in_v8
                else "FAIL",
        },

        {
            "metric":
                "second_not_yet_in_v8",

            "value":
                int(
                    not second_in_v8
                ),

            "status":
                "PASS"
                if not second_in_v8
                else "FAIL",
        },

        {
            "metric":
                "lane_inferred",

            "value":
                0,

            "status":
                "PASS",
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
                "queue_wait_inferred",

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
        action
        if promotion_ready
        else
        "NOT_YET",
    )

    print()
    print(
        "Lane:",
        "UNKNOWN",
    )

    print(
        "Withdrawal semantic:",
        "UNKNOWN",
    )

    print(
        "Queue position:",
        "UNKNOWN",
    )

    print(
        "Queue wait:",
        "UNKNOWN",
    )

    print(
        "Exact timestamp:",
        "UNKNOWN",
    )

    print()
    print("=" * 118)

    if promotion_ready:
        print(
            "FINAL STATUS: "
            "MALUKAS_AUTOSPORT_REPEAT_EVIDENCE_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "MALUKAS_AUTOSPORT_REPEAT_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 118)

    print()
    print("OUTPUTS")
    print(OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
