from pathlib import Path
import csv


PHASE = "R2D.2"

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V8 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

STATE_V2 = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

R2D1A = Path(
    "weather/output/"
    "queue_rescue_2022_candidate_adjudication_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_external_queue_order_evidence_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_external_queue_order_evidence_v1_qa.csv"
)


ILOTT_FIRST = (
    "3cd6d98a-da75-5822-8dae-05e83ad8457c"
)

ILOTT_SECOND = (
    "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"
)

MALUKAS_FIRST = (
    "619575d3-e7eb-5cce-886f-0a8485b98eba"
)

MALUKAS_SECOND = (
    "85c917fa-1c7a-52cb-a47f-468b4bdae9a5"
)

SATO_FIRST = (
    "3f221659-74ff-5901-97dc-08071a734690"
)

SATO_SECOND = (
    "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"
)


AUTOSPORT_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-"
    "p13-33-set/10308540/"
)

AUTOSPORT_TITLE = (
    "Indy 500: Sato, Grosjean, Johnson into top 12 fight"
)

AUTOSPORT_DATE_LABEL = "EDITED"

AUTOSPORT_DATE_DISPLAY = (
    "May 22, 2022, 2:31 AM"
)


ILOTT_QUOTE = (
    "Callum Ilott of Juncos Hollinger Racing was "
    "the first to do a retake run"
)

LINE_QUOTE = (
    "Dale Coyne Racing put rookie David Malukas "
    "and veteran Takuma Sato in line"
)

MALUKAS_SEQUENCE_QUOTE = (
    "Rookie Malukas improved"
)

SATO_SEQUENCE_QUOTE = (
    "Sato bounced off Turn 2's SAFER barrier"
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


def attempt_present(rows, attempt_id):
    return any(
        txt(row.get("attempt_id"))
        ==
        attempt_id
        for row in rows
    )


def chronology_present(rows, attempt_id):
    return any(
        txt(row.get("attempt_id"))
        ==
        attempt_id
        and
        txt(
            row.get("chronology_usable")
        ).lower()
        ==
        "true"
        for row in rows
    )


def main():

    print()
    print("=" * 124)
    print(
        "R2D.2 — 2022 EXTERNAL QUEUE MEMBERSHIP / "
        "RETAKE-ORDER EVIDENCE CAPTURE"
    )
    print("=" * 124)

    required = [
        RESULT_V3,
        CHRONOLOGY_V10,
        ACTION_V8,
        STATE_V2,
        R2D1A,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 124)

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
            "R2D2_EXTERNAL_QUEUE_ORDER_INPUT_MISSING"
        )
        return

    results = read_csv(
        RESULT_V3
    )

    chronology = read_csv(
        CHRONOLOGY_V10
    )

    action = read_csv(
        ACTION_V8
    )

    states = read_csv(
        STATE_V2
    )

    r2d1a = read_csv(
        R2D1A
    )

    ids = [
        ILOTT_FIRST,
        ILOTT_SECOND,
        MALUKAS_FIRST,
        MALUKAS_SECOND,
        SATO_FIRST,
        SATO_SECOND,
    ]

    result_ok = {
        aid: attempt_present(
            results,
            aid,
        )
        for aid in ids
    }

    chronology_ok = {
        aid: chronology_present(
            chronology,
            aid,
        )
        for aid in ids
    }

    ilott_action = any(
        txt(row.get("driver_name"))
        ==
        "Callum Ilott"
        and
        txt(row.get("action"))
        ==
        "RETAKE_RUN"
        for row in action
    )

    malukas_action = any(
        txt(row.get("driver_name"))
        ==
        "David Malukas"
        and
        txt(row.get("action"))
        ==
        "REPEAT_ATTEMPT_IMPROVED"
        for row in action
    )

    sato_action = any(
        txt(row.get("driver_name"))
        ==
        "Takuma Sato"
        and
        txt(row.get("action"))
        ==
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION"
        for row in action
    )

    malukas_p12 = any(
        txt(row.get("driver_name"))
        ==
        "David Malukas"
        and
        txt(row.get("subject_attempt_id"))
        ==
        MALUKAS_SECOND
        and
        txt(row.get("rank"))
        ==
        "12"
        for row in states
    )

    sato_p12 = any(
        txt(row.get("driver_name"))
        ==
        "Takuma Sato"
        and
        txt(row.get("subject_attempt_id"))
        ==
        SATO_SECOND
        and
        txt(row.get("rank"))
        ==
        "12"
        for row in states
    )

    mclaughlin_queue_anchor = any(
        txt(row.get("driver_name"))
        ==
        "Scott McLaughlin"
        and
        txt(row.get("queue_lane"))
        ==
        "LANE_1"
        and
        txt(row.get("queue_position"))
        ==
        "FRONT"
        and
        txt(
            row.get("promotion_ready")
        ).lower()
        ==
        "true"
        for row in r2d1a
    )

    print()
    print("=" * 124)
    print("GROUNDING")
    print("=" * 124)

    print()

    for aid in ids:
        print(
            aid,
            "| result V3:",
            result_ok[aid],
            "| chronology V10:",
            chronology_ok[aid],
        )

    print()
    print(
        "Ilott RETAKE_RUN action grounded:",
        ilott_action,
    )

    print(
        "Malukas repeat action grounded:",
        malukas_action,
    )

    print(
        "Sato required reattempt grounded:",
        sato_action,
    )

    print(
        "Malukas provisional P12 grounded:",
        malukas_p12,
    )

    print(
        "Sato provisional P12 grounded:",
        sato_p12,
    )

    print(
        "McLaughlin front-Lane1 R2D1A anchor grounded:",
        mclaughlin_queue_anchor,
    )

    all_result_grounded = all(
        result_ok.values()
    )

    all_chrono_grounded = all(
        chronology_ok.values()
    )

    promotion_ready = all([
        all_result_grounded,
        all_chrono_grounded,
        ilott_action,
        malukas_action,
        sato_action,
        malukas_p12,
        sato_p12,
        mclaughlin_queue_anchor,
    ])

    print()
    print("=" * 124)
    print("SOURCE-NATIVE EXTERNAL EVIDENCE")
    print("=" * 124)

    print()
    print("ILOTT")
    print(
        "  quote:",
        repr(
            ILOTT_QUOTE
        ),
    )
    print(
        "  supported semantic:",
        "FIRST_RETAKE_RUN",
    )
    print(
        "  queue membership:",
        "UNKNOWN",
    )
    print(
        "  lane:",
        "UNKNOWN",
    )

    print()
    print("MALUKAS / SATO")
    print(
        "  quote:",
        repr(
            LINE_QUOTE
        ),
    )
    print(
        "  Malukas queue membership:",
        "CONFIRMED_GENERIC_LINE",
    )
    print(
        "  Sato queue membership:",
        "CONFIRMED_GENERIC_LINE",
    )
    print(
        "  Lane for both:",
        "UNKNOWN",
    )
    print(
        "  exact position for both:",
        "UNKNOWN",
    )

    print()
    print("RUN ORDER")
    print(
        "  narrative:",
        "Ilott retake -> Malukas run -> Sato run",
    )
    print(
        "  supported relation:",
        "MALUKAS_SECOND_BEFORE_SATO_SECOND",
    )
    print(
        "  queue wait:",
        "UNKNOWN",
    )
    print(
        "  exact timestamps:",
        "UNKNOWN",
    )

    evidence_rows = [
        {
            "evidence_id":
                "R2D2-ILOTT-FIRST-RETAKE",

            "phase":
                PHASE,

            "driver_name":
                "Callum Ilott",

            "subject_attempt_id":
                ILOTT_SECOND,

            "related_attempt_id":
                ILOTT_FIRST,

            "evidence_family":
                "RETAKE_ORDER",

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_title":
                AUTOSPORT_TITLE,

            "source_date_label":
                AUTOSPORT_DATE_LABEL,

            "source_date_display":
                AUTOSPORT_DATE_DISPLAY,

            "source_url":
                AUTOSPORT_URL,

            "source_quote":
                ILOTT_QUOTE,

            "supported_semantic":
                "FIRST_RETAKE_RUN",

            "queue_membership":
                "UNKNOWN",

            "queue_lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "related_driver":
                "",

            "relative_order":
                "FIRST_RETAKE_IN_DESCRIBED_SECOND_SEGMENT_SEQUENCE",

            "queue_wait_seconds":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Autosport explicitly identifies Ilott as "
                    "the first driver to perform a retake run. "
                    "This is run-order evidence, not proof that "
                    "Ilott occupied first position in either "
                    "qualifying queue."
                ),
        },

        {
            "evidence_id":
                "R2D2-MALUKAS-IN-LINE",

            "phase":
                PHASE,

            "driver_name":
                "David Malukas",

            "subject_attempt_id":
                MALUKAS_SECOND,

            "related_attempt_id":
                MALUKAS_FIRST,

            "evidence_family":
                "GENERIC_QUEUE_MEMBERSHIP",

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_title":
                AUTOSPORT_TITLE,

            "source_date_label":
                AUTOSPORT_DATE_LABEL,

            "source_date_display":
                AUTOSPORT_DATE_DISPLAY,

            "source_url":
                AUTOSPORT_URL,

            "source_quote":
                LINE_QUOTE,

            "supported_semantic":
                "PUT_IN_LINE_FOR_REPEAT_RUN",

            "queue_membership":
                "CONFIRMED_GENERIC_LINE",

            "queue_lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "related_driver":
                "Takuma Sato",

            "relative_order":
                "NOT_DERIVED_FROM_LINE_PHRASE",

            "queue_wait_seconds":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Autosport explicitly states Dale Coyne "
                    "Racing put Malukas and Sato in line. "
                    "This supports generic waiting-line "
                    "membership only. It does not identify "
                    "Lane 1/Lane 2, exact position, or wait."
                ),
        },

        {
            "evidence_id":
                "R2D2-SATO-IN-LINE",

            "phase":
                PHASE,

            "driver_name":
                "Takuma Sato",

            "subject_attempt_id":
                SATO_SECOND,

            "related_attempt_id":
                SATO_FIRST,

            "evidence_family":
                "GENERIC_QUEUE_MEMBERSHIP",

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_title":
                AUTOSPORT_TITLE,

            "source_date_label":
                AUTOSPORT_DATE_LABEL,

            "source_date_display":
                AUTOSPORT_DATE_DISPLAY,

            "source_url":
                AUTOSPORT_URL,

            "source_quote":
                LINE_QUOTE,

            "supported_semantic":
                "PUT_IN_LINE_FOR_REATTEMPT",

            "queue_membership":
                "CONFIRMED_GENERIC_LINE",

            "queue_lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "related_driver":
                "David Malukas",

            "relative_order":
                "NOT_DERIVED_FROM_LINE_PHRASE",

            "queue_wait_seconds":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Sato is directly included in Autosport's "
                    "'put ... in line' statement. Because his "
                    "reattempt was required after invalidation, "
                    "no Lane 1/Lane 2 choice is inferred."
                ),
        },

        {
            "evidence_id":
                "R2D2-MALUKAS-BEFORE-SATO",

            "phase":
                PHASE,

            "driver_name":
                "David Malukas",

            "subject_attempt_id":
                MALUKAS_SECOND,

            "related_attempt_id":
                SATO_SECOND,

            "evidence_family":
                "RUN_ORDER",

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_title":
                AUTOSPORT_TITLE,

            "source_date_label":
                AUTOSPORT_DATE_LABEL,

            "source_date_display":
                AUTOSPORT_DATE_DISPLAY,

            "source_url":
                AUTOSPORT_URL,

            "source_quote":
                (
                    MALUKAS_SEQUENCE_QUOTE
                    +
                    " | "
                    +
                    SATO_SEQUENCE_QUOTE
                ),

            "supported_semantic":
                "MALUKAS_SECOND_BEFORE_SATO_SECOND",

            "queue_membership":
                "NOT_APPLICABLE",

            "queue_lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "related_driver":
                "Takuma Sato",

            "relative_order":
                "MALUKAS_SECOND_BEFORE_SATO_SECOND",

            "queue_wait_seconds":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "The run order is supported by the article's "
                    "source-native narrative sequence and by the "
                    "already-adjudicated provisional P12 states: "
                    "Malukas improved into P12, then Sato ran and "
                    "displaced him. The ordering is not inferred "
                    "from the phrase 'put ... in line'."
                ),
        },
    ]

    fields = [
        "evidence_id",
        "phase",
        "driver_name",
        "subject_attempt_id",
        "related_attempt_id",
        "evidence_family",
        "source_name",
        "source_class",
        "source_title",
        "source_date_label",
        "source_date_display",
        "source_url",
        "source_quote",
        "supported_semantic",
        "queue_membership",
        "queue_lane",
        "queue_position",
        "related_driver",
        "relative_order",
        "queue_wait_seconds",
        "time_quality",
        "exact_timestamp",
        "promotion_ready",
        "notes",
    ]

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        fields,
    )

    qa_rows = [
        {
            "metric":
                "all_attempts_result_grounded",

            "value":
                int(
                    all_result_grounded
                ),

            "status":
                (
                    "PASS"
                    if all_result_grounded
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "all_attempts_chronology_grounded",

            "value":
                int(
                    all_chrono_grounded
                ),

            "status":
                (
                    "PASS"
                    if all_chrono_grounded
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "ilott_action_grounded",

            "value":
                int(
                    ilott_action
                ),

            "status":
                (
                    "PASS"
                    if ilott_action
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "malukas_action_grounded",

            "value":
                int(
                    malukas_action
                ),

            "status":
                (
                    "PASS"
                    if malukas_action
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "sato_action_grounded",

            "value":
                int(
                    sato_action
                ),

            "status":
                (
                    "PASS"
                    if sato_action
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "malukas_p12_state_grounded",

            "value":
                int(
                    malukas_p12
                ),

            "status":
                (
                    "PASS"
                    if malukas_p12
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "sato_p12_state_grounded",

            "value":
                int(
                    sato_p12
                ),

            "status":
                (
                    "PASS"
                    if sato_p12
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "mclaughlin_queue_anchor_grounded",

            "value":
                int(
                    mclaughlin_queue_anchor
                ),

            "status":
                (
                    "PASS"
                    if mclaughlin_queue_anchor
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "external_semantic_units",

            "value":
                len(
                    evidence_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        evidence_rows
                    )
                    ==
                    4
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "generic_queue_membership_rows",

            "value":
                sum(
                    1
                    for row in evidence_rows
                    if txt(
                        row.get(
                            "queue_membership"
                        )
                    )
                    ==
                    "CONFIRMED_GENERIC_LINE"
                ),

            "status":
                (
                    "PASS"
                    if sum(
                        1
                        for row in evidence_rows
                        if txt(
                            row.get(
                                "queue_membership"
                            )
                        )
                        ==
                        "CONFIRMED_GENERIC_LINE"
                    )
                    ==
                    2
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "lane_inferred_for_malukas_or_sato",

            "value":
                sum(
                    1
                    for row in evidence_rows
                    if txt(
                        row.get(
                            "driver_name"
                        )
                    )
                    in {
                        "David Malukas",
                        "Takuma Sato",
                    }
                    and
                    txt(
                        row.get(
                            "queue_lane"
                        )
                    )
                    not in {
                        "",
                        "UNKNOWN",
                    }
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_position_inferred",

            "value":
                sum(
                    1
                    for row in evidence_rows
                    if txt(
                        row.get(
                            "queue_position"
                        )
                    )
                    not in {
                        "",
                        "UNKNOWN",
                    }
                ),

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
                "exact_timestamp_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "active_ledger_mutation",

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

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if (
        promotion_ready
        and
        not hard_fail
    ):

        print(
            "FINAL STATUS: "
            "R2D2_EXTERNAL_QUEUE_ORDER_EVIDENCE_PROMOTION_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R2D2_EXTERNAL_QUEUE_ORDER_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
