from pathlib import Path
import csv


PHASE = "R2E.2"

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

R2E1A = Path(
    "weather/output/"
    "pit_service_rescue_2022_candidate_adjudication_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_external_technical_evidence_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_external_technical_evidence_v1_qa.csv"
)


MARCO_FIRST = (
    "c044edbc-0f6c-5aab-bdef-9c4156b50617"
)

MARCO_SECOND = (
    "63982b5e-7639-5140-a6a2-702a77c2fc85"
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

MARCO_QUOTE = (
    "Andretti was next up again, having suffered "
    "an electrical issue on his initial run"
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
        "R2E.2 — 2022 EXTERNAL PIT / SERVICE / "
        "TECHNICAL-STATE EVIDENCE CAPTURE"
    )
    print("=" * 124)

    required = [
        RESULT_V3,
        CHRONOLOGY_V10,
        ACTION_V8,
        R2E1A,
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
            "R2E2_EXTERNAL_SERVICE_INPUT_MISSING"
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

    r2e1a = read_csv(
        R2E1A
    )

    first_result = attempt_present(
        results,
        MARCO_FIRST,
    )

    second_result = attempt_present(
        results,
        MARCO_SECOND,
    )

    first_chrono = chronology_present(
        chronology,
        MARCO_FIRST,
    )

    second_chrono = chronology_present(
        chronology,
        MARCO_SECOND,
    )

    marco_second_action = any(
        txt(row.get("driver_name"))
        ==
        "Marco Andretti"
        and
        txt(row.get("action"))
        ==
        "SECOND_ATTEMPT"
        for row in action
    )

    local_service_promotions = [
        row
        for row in r2e1a
        if txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
    ]

    grounding_ok = all([
        first_result,
        second_result,
        first_chrono,
        second_chrono,
        marco_second_action,
        len(local_service_promotions) == 0,
    ])

    print()
    print("=" * 124)
    print("GROUNDING")
    print("=" * 124)

    print()
    print(
        "Marco first result V3:",
        first_result,
    )

    print(
        "Marco second result V3:",
        second_result,
    )

    print(
        "Marco first chronology V10:",
        first_chrono,
    )

    print(
        "Marco second chronology V10:",
        second_chrono,
    )

    print(
        "Marco SECOND_ATTEMPT action grounded:",
        marco_second_action,
    )

    print(
        "Local direct-service promotions:",
        len(
            local_service_promotions
        ),
    )

    print(
        "Overall grounding:",
        grounding_ok,
    )

    print()
    print("=" * 124)
    print("EXTERNAL EVIDENCE ADJUDICATION")
    print("=" * 124)

    print()
    print("MARCO ANDRETTI")
    print(
        "  source:",
        "Autosport",
    )

    print(
        "  quote:",
        repr(
            MARCO_QUOTE
        ),
    )

    print(
        "  technical issue:",
        "ELECTRICAL",
    )

    print(
        "  issue bound to:",
        "INITIAL_RUN",
    )

    print(
        "  later second attempt:",
        "SUPPORTED",
    )

    print()
    print(
        "Service / repair operation:",
        "UNKNOWN",
    )

    print(
        "Refuel:",
        "NOT_OBSERVED",
    )

    print(
        "Cooling service:",
        "NOT_OBSERVED",
    )

    print(
        "Tire service:",
        "NOT_OBSERVED",
    )

    print(
        "Setup adjustment:",
        "NOT_OBSERVED",
    )

    print(
        "Repair action:",
        "UNKNOWN",
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "  Electrical issue != confirmed repair operation."
    )

    print(
        "  A later second attempt does not prove what "
        "service was performed between runs."
    )

    evidence_rows = [
        {
            "evidence_id":
                "R2E2-MARCO-ELECTRICAL-ISSUE",

            "phase":
                PHASE,

            "year":
                "2022",

            "driver_name":
                "Marco Andretti",

            "subject_attempt_id":
                MARCO_FIRST,

            "related_attempt_id":
                MARCO_SECOND,

            "evidence_family":
                "TECHNICAL_STATE",

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
                MARCO_QUOTE,

            "technical_issue_confirmed":
                "True",

            "technical_issue_type":
                "ELECTRICAL",

            "technical_issue_stage":
                "INITIAL_RUN",

            "later_repeat_attempt_supported":
                "True",

            "pit_return_confirmed":
                "UNKNOWN",

            "service_between_attempts_confirmed":
                "UNKNOWN",

            "refuel_confirmed":
                "NOT_OBSERVED",

            "cooling_service_confirmed":
                "NOT_OBSERVED",

            "tire_service_confirmed":
                "NOT_OBSERVED",

            "adjustment_confirmed":
                "NOT_OBSERVED",

            "repair_confirmed":
                "UNKNOWN",

            "exact_service_time":
                "UNKNOWN",

            "promotion_ready":
                str(
                    grounding_ok
                ),

            "notes":
                (
                    "Autosport explicitly states Marco Andretti "
                    "suffered an electrical issue on his initial "
                    "run and later ran again. This supports a "
                    "technical-state anomaly, but the source does "
                    "not identify the specific pit/service/repair "
                    "operation performed before the later attempt."
                ),
        }
    ]

    fields = [
        "evidence_id",
        "phase",
        "year",
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
        "technical_issue_confirmed",
        "technical_issue_type",
        "technical_issue_stage",
        "later_repeat_attempt_supported",
        "pit_return_confirmed",
        "service_between_attempts_confirmed",
        "refuel_confirmed",
        "cooling_service_confirmed",
        "tire_service_confirmed",
        "adjustment_confirmed",
        "repair_confirmed",
        "exact_service_time",
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
                "marco_first_result_grounded",

            "value":
                int(
                    first_result
                ),

            "status":
                (
                    "PASS"
                    if first_result
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "marco_second_result_grounded",

            "value":
                int(
                    second_result
                ),

            "status":
                (
                    "PASS"
                    if second_result
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "marco_first_chronology_grounded",

            "value":
                int(
                    first_chrono
                ),

            "status":
                (
                    "PASS"
                    if first_chrono
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "marco_second_chronology_grounded",

            "value":
                int(
                    second_chrono
                ),

            "status":
                (
                    "PASS"
                    if second_chrono
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "marco_second_action_grounded",

            "value":
                int(
                    marco_second_action
                ),

            "status":
                (
                    "PASS"
                    if marco_second_action
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "local_service_promotions_zero",

            "value":
                len(
                    local_service_promotions
                ),

            "status":
                (
                    "PASS"
                    if len(
                        local_service_promotions
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "technical_issue_rows",

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
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "repair_inferred_from_later_attempt",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "refuel_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "cooling_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "tire_service_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "setup_adjustment_inferred",

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
        grounding_ok
        and
        not hard_fail
    ):
        print(
            "FINAL STATUS: "
            "R2E2_MARCO_TECHNICAL_STATE_EVIDENCE_PROMOTION_READY_"
            "NO_DIRECT_SERVICE_EVIDENCE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2E2_EXTERNAL_SERVICE_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
