from pathlib import Path
import csv


PHASE = "R1G.28E"

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

OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_second_attempt_therace_evidence_v1.csv"
)

QA_OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_second_attempt_therace_evidence_v1_qa.csv"
)


FIRST_ID = "c044edbc-0f6c-5aab-bdef-9c4156b50617"
SECOND_ID = "63982b5e-7639-5140-a6a2-702a77c2fc85"

EXPECTED_FIRST_SPEED = "226.108"
EXPECTED_SECOND_SPEED = "230.345"

SOURCE_TITLE = "Winners and losers from 2022 Indy 500 qualifying"
SOURCE_NAME = "The Race"
SOURCE_CLASS = "REPUTABLE_SECONDARY_EDITORIAL"
SOURCE_AUTHOR = "Jack Benyon"
SOURCE_DATE = "2022-05-23"
SOURCE_URL = (
    "https://www.the-race.com/indycar/"
    "winners-and-losers-from-2022-indy-500-qualifying/"
)

# Short source-native quote, kept deliberately brief.
SOURCE_QUOTE = "could only manage 23rd on his second attempt"


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
    print("=" * 116)
    print(
        "R1G.28E — THE RACE MARCO "
        "SECOND-ATTEMPT EVIDENCE CAPTURE"
    )
    print("=" * 116)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V7,
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
            "MARCO_SECOND_ATTEMPT_CAPTURE_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V7)

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

    first_row = canonical_by_id.get(FIRST_ID)
    second_row = canonical_by_id.get(SECOND_ID)

    first_result = result_by_id.get(FIRST_ID)
    second_result = result_by_id.get(SECOND_ID)

    if (
        first_row is None
        or second_row is None
        or first_result is None
        or second_result is None
    ):
        print()
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_CAPTURE_GROUNDING_FAILED"
        )
        return

    first_ok = all([
        driver(first_row) == "Marco Andretti",
        attempt_index(first_row) == "1",
        speed(first_row) == EXPECTED_FIRST_SPEED,
    ])

    second_ok = all([
        driver(second_row) == "Marco Andretti",
        attempt_index(second_row) == "2",
        speed(second_row) == EXPECTED_SECOND_SPEED,
    ])

    official_p23_binding = (
        official_result_row(second_result) == "23"
        and
        speed(second_row) == EXPECTED_SECOND_SPEED
    )

    first_in_v7 = any(
        txt(row.get("attempt_id")) == FIRST_ID
        and
        txt(row.get("chronology_usable")).lower() == "true"
        for row in chronology
    )

    second_in_v7 = any(
        txt(row.get("attempt_id")) == SECOND_ID
        and
        txt(row.get("chronology_usable")).lower() == "true"
        for row in chronology
    )

    print()
    print("=" * 116)
    print("GROUNDING")
    print("=" * 116)

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
        "Official P23 -> 230.345 binding:",
        official_p23_binding,
    )

    print(
        "First already chronology-covered:",
        first_in_v7,
    )

    print(
        "Second already chronology-covered:",
        second_in_v7,
    )

    print()
    print("=" * 116)
    print("SOURCE EVIDENCE")
    print("=" * 116)

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
        "Date:",
        SOURCE_DATE,
    )

    print(
        "Author:",
        SOURCE_AUTHOR,
    )

    print(
        "Source-native quote:",
        repr(SOURCE_QUOTE),
    )

    print()
    print(
        "Interpretation:",
        (
            "The Race explicitly identifies Marco's "
            "P23 result as his second attempt."
        ),
    )

    promotion_ready = all([
        first_ok,
        second_ok,
        official_p23_binding,
        first_in_v7,
        not second_in_v7,
    ])

    evidence_rows = [
        {
            "evidence_id":
                "R1G28E-MARCO-SECOND-THE-RACE",

            "phase":
                PHASE,

            "year":
                "2022",

            "driver_name":
                "Marco Andretti",

            "car_number":
                "98",

            "first_attempt_id":
                FIRST_ID,

            "first_speed_mph":
                EXPECTED_FIRST_SPEED,

            "second_attempt_id":
                SECOND_ID,

            "second_speed_mph":
                EXPECTED_SECOND_SPEED,

            "official_second_result_row":
                official_result_row(
                    second_result
                ),

            "official_second_status":
                official_status(
                    second_result
                ),

            "source_name":
                SOURCE_NAME,

            "source_class":
                SOURCE_CLASS,

            "source_title":
                SOURCE_TITLE,

            "source_author":
                SOURCE_AUTHOR,

            "source_date":
                SOURCE_DATE,

            "source_url":
                SOURCE_URL,

            "source_quote":
                SOURCE_QUOTE,

            "source_semantic":
                "EXPLICIT_SECOND_ATTEMPT",

            "relation":
                (
                    "MARCO_FIRST_ATTEMPT_BEFORE_SECOND_ATTEMPT"
                    if promotion_ready
                    else
                    "REVIEW_REQUIRED"
                ),

            "action":
                (
                    "SECOND_ATTEMPT"
                    if promotion_ready
                    else
                    "REVIEW_REQUIRED"
                ),

            "time_quality":
                (
                    "ORDERING_ONLY"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "lane":
                "UNKNOWN",

            "queue":
                "UNKNOWN",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "The Race explicitly calls Marco's P23 result "
                    "his second attempt. Official result row 23 "
                    "binds P23 to 230.345 mph. Canonical index 1 "
                    "is 226.108 mph and index 2 is 230.345 mph. "
                    "No Lane, queue, wait, withdrawal semantics, "
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
            "second_attempt_id",
            "second_speed_mph",
            "official_second_result_row",
            "official_second_status",
            "source_name",
            "source_class",
            "source_title",
            "source_author",
            "source_date",
            "source_url",
            "source_quote",
            "source_semantic",
            "relation",
            "action",
            "time_quality",
            "lane",
            "queue",
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
                "official_p23_binding",

            "value":
                int(official_p23_binding),

            "status":
                "PASS"
                if official_p23_binding
                else "FAIL",
        },

        {
            "metric":
                "first_in_v7",

            "value":
                int(first_in_v7),

            "status":
                "PASS"
                if first_in_v7
                else "FAIL",
        },

        {
            "metric":
                "second_not_yet_in_v7",

            "value":
                int(not second_in_v7),

            "status":
                "PASS"
                if not second_in_v7
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
                "queue_inferred",

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
    print("=" * 116)
    print("ADJUDICATION")
    print("=" * 116)

    print()
    print(
        "Promotion ready:",
        promotion_ready,
    )

    print(
        "Supported relation:",
        (
            "MARCO_226.108_FIRST_ATTEMPT_BEFORE_230.345_SECOND_ATTEMPT"
            if promotion_ready
            else
            "NOT_YET"
        ),
    )

    print(
        "Supported action:",
        (
            "SECOND_ATTEMPT"
            if promotion_ready
            else
            "NOT_YET"
        ),
    )

    print(
        "Lane:",
        "UNKNOWN",
    )

    print(
        "Queue:",
        "UNKNOWN",
    )

    print(
        "Exact timestamp:",
        "UNKNOWN",
    )

    print()
    print("=" * 116)

    if promotion_ready:
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_THE_RACE_EVIDENCE_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_ATTEMPT_THE_RACE_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 116)

    print()
    print("OUTPUTS")
    print(OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
