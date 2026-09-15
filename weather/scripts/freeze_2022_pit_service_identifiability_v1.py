from pathlib import Path
import csv
import json


PHASE = "R2E.3"

R2E1A = Path(
    "weather/output/"
    "pit_service_rescue_2022_candidate_adjudication_v1.csv"
)

R2E2 = Path(
    "weather/output/"
    "pit_service_rescue_2022_external_technical_evidence_v1.csv"
)

R2E2_QA = Path(
    "weather/output/"
    "pit_service_rescue_2022_external_technical_evidence_v1_qa.csv"
)

OUTPUT_DIR = Path("weather/output")

FREEZE_OUT = (
    OUTPUT_DIR
    / "pit_service_identifiability_2022_v1.csv"
)

TECHNICAL_OUT = (
    OUTPUT_DIR
    / "technical_state_evidence_2022_v1.csv"
)

JSON_OUT = (
    OUTPUT_DIR
    / "pit_service_identifiability_2022_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "pit_service_identifiability_2022_v1_qa.csv"
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


def main():

    print()
    print("=" * 124)
    print(
        "R2E.3 — 2022 PIT / SERVICE "
        "IDENTIFIABILITY FREEZE"
    )
    print("=" * 124)

    required = [
        R2E1A,
        R2E2,
        R2E2_QA,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 124)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2E3_PIT_SERVICE_FREEZE_INPUT_MISSING"
        )
        return

    local_rows = read_csv(R2E1A)
    external_rows = read_csv(R2E2)
    external_qa = read_csv(R2E2_QA)

    # --------------------------------------------------
    # Validate local adjudication
    # --------------------------------------------------

    local_promotions = [
        row
        for row in local_rows
        if txt(
            row.get("promotion_ready")
        ).lower()
        ==
        "true"
    ]

    unresolved_local = [
        row
        for row in local_rows
        if txt(
            row.get("decision")
        )
        ==
        "REVIEW_REQUIRED_NO_DIRECT_SERVICE_BINDING"
    ]

    # --------------------------------------------------
    # Validate external technical evidence
    # --------------------------------------------------

    marco_rows = [
        row
        for row in external_rows
        if (
            txt(row.get("driver_name"))
            ==
            "Marco Andretti"
            and
            txt(
                row.get("technical_issue_confirmed")
            ).lower()
            ==
            "true"
            and
            txt(
                row.get("technical_issue_type")
            )
            ==
            "ELECTRICAL"
            and
            txt(
                row.get("promotion_ready")
            ).lower()
            ==
            "true"
        )
    ]

    marco_ok = (
        len(marco_rows)
        ==
        1
    )

    if marco_ok:
        marco = marco_rows[0]
    else:
        marco = {}

    repair_confirmed = (
        txt(
            marco.get(
                "repair_confirmed"
            )
        ).lower()
        ==
        "true"
    )

    pit_return_confirmed = (
        txt(
            marco.get(
                "pit_return_confirmed"
            )
        ).lower()
        ==
        "true"
    )

    service_between_confirmed = (
        txt(
            marco.get(
                "service_between_attempts_confirmed"
            )
        ).lower()
        ==
        "true"
    )

    direct_refuel = any(
        txt(
            row.get(
                "refuel_confirmed"
            )
        ).lower()
        ==
        "true"
        for row in external_rows
    )

    direct_cooling = any(
        txt(
            row.get(
                "cooling_service_confirmed"
            )
        ).lower()
        ==
        "true"
        for row in external_rows
    )

    direct_tire = any(
        txt(
            row.get(
                "tire_service_confirmed"
            )
        ).lower()
        ==
        "true"
        for row in external_rows
    )

    direct_adjustment = any(
        txt(
            row.get(
                "adjustment_confirmed"
            )
        ).lower()
        ==
        "true"
        for row in external_rows
    )

    direct_service_evidence = any([
        repair_confirmed,
        pit_return_confirmed,
        service_between_confirmed,
        direct_refuel,
        direct_cooling,
        direct_tire,
        direct_adjustment,
    ])

    print()
    print("=" * 124)
    print("EVIDENCE ASSESSMENT")
    print("=" * 124)

    print()
    print(
        "Local promotion-ready service rows:",
        len(local_promotions),
    )

    print(
        "Local unresolved direct-service rows:",
        len(unresolved_local),
    )

    print()
    print(
        "Marco electrical technical-state rows:",
        len(marco_rows),
    )

    print(
        "Marco electrical issue supported:",
        marco_ok,
    )

    print(
        "Marco later repeat attempt supported:",
        txt(
            marco.get(
                "later_repeat_attempt_supported"
            )
        )
        or
        "UNKNOWN",
    )

    print()
    print(
        "Pit return confirmed:",
        pit_return_confirmed,
    )

    print(
        "Service between attempts confirmed:",
        service_between_confirmed,
    )

    print(
        "Repair confirmed:",
        repair_confirmed,
    )

    print(
        "Refuel confirmed:",
        direct_refuel,
    )

    print(
        "Cooling service confirmed:",
        direct_cooling,
    )

    print(
        "Tire service confirmed:",
        direct_tire,
    )

    print(
        "Setup adjustment confirmed:",
        direct_adjustment,
    )

    print()
    print(
        "Any direct service evidence:",
        direct_service_evidence,
    )

    # --------------------------------------------------
    # Frozen interpretation
    # --------------------------------------------------

    service_identifiable = (
        direct_service_evidence
    )

    if service_identifiable:
        service_status = (
            "PARTIALLY_IDENTIFIABLE"
        )

        downstream_policy = (
            "USE_ONLY_SOURCE_SUPPORTED_SERVICE_STATE"
        )

    else:
        service_status = (
            "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
        )

        downstream_policy = (
            "SERVICE_STATE_UNKNOWN"
        )

    print()
    print("=" * 124)
    print("FROZEN POLICY")
    print("=" * 124)

    print()
    print(
        "Pit/service between attempts:",
        (
            "IDENTIFIABLE"
            if service_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Refuel:",
        (
            "SUPPORTED"
            if direct_refuel
            else
            "NOT_OBSERVED"
        ),
    )

    print(
        "Cooling service:",
        (
            "SUPPORTED"
            if direct_cooling
            else
            "NOT_OBSERVED"
        ),
    )

    print(
        "Tire service:",
        (
            "SUPPORTED"
            if direct_tire
            else
            "NOT_OBSERVED"
        ),
    )

    print(
        "Setup adjustment:",
        (
            "SUPPORTED"
            if direct_adjustment
            else
            "NOT_OBSERVED"
        ),
    )

    print(
        "Repair operation:",
        (
            "SUPPORTED"
            if repair_confirmed
            else
            "UNKNOWN"
        ),
    )

    print()
    print(
        "Marco electrical issue:",
        (
            "SUPPORTED"
            if marco_ok
            else
            "NOT_READY"
        ),
    )

    print()
    print(
        "Downstream service treatment:",
        downstream_policy,
    )

    print()
    print(
        "NOT_OBSERVED means confirmed NONE:",
        "NO",
    )

    print(
        "Later repeat attempt proves repair:",
        "NO",
    )

    print(
        "Queue/wait may be used to infer cooling:",
        "NO",
    )

    # --------------------------------------------------
    # Freeze main service policy
    # --------------------------------------------------

    freeze_rows = [
        {
            "phase":
                PHASE,

            "year":
                "2022",

            "service_identifiability_status":
                service_status,

            "pit_return_support":
                (
                    "SUPPORTED"
                    if pit_return_confirmed
                    else
                    "NOT_OBSERVED"
                ),

            "service_between_attempts_support":
                (
                    "SUPPORTED"
                    if service_between_confirmed
                    else
                    "NOT_OBSERVED"
                ),

            "refuel_support":
                (
                    "SUPPORTED"
                    if direct_refuel
                    else
                    "NOT_OBSERVED"
                ),

            "cooling_service_support":
                (
                    "SUPPORTED"
                    if direct_cooling
                    else
                    "NOT_OBSERVED"
                ),

            "tire_service_support":
                (
                    "SUPPORTED"
                    if direct_tire
                    else
                    "NOT_OBSERVED"
                ),

            "adjustment_support":
                (
                    "SUPPORTED"
                    if direct_adjustment
                    else
                    "NOT_OBSERVED"
                ),

            "repair_support":
                (
                    "SUPPORTED"
                    if repair_confirmed
                    else
                    "UNKNOWN"
                ),

            "technical_state_support":
                (
                    "SUPPORTED"
                    if marco_ok
                    else
                    "NOT_READY"
                ),

            "technical_issue_driver":
                (
                    "Marco Andretti"
                    if marco_ok
                    else
                    ""
                ),

            "technical_issue_type":
                (
                    "ELECTRICAL"
                    if marco_ok
                    else
                    ""
                ),

            "technical_issue_stage":
                (
                    "INITIAL_RUN"
                    if marco_ok
                    else
                    ""
                ),

            "downstream_service_policy":
                downstream_policy,

            "not_observed_means_none":
                "False",

            "later_attempt_proves_repair":
                "False",

            "queue_wait_can_infer_cooling":
                "False",

            "exact_service_reconstruction_ready":
                "False",

            "service_feature_calibration_ready":
                "False",

            "notes":
                (
                    "Recovered 2022 evidence does not identify "
                    "pit/service/refuel/cooling/tire/setup actions "
                    "between decision-relevant repeat attempts. "
                    "Marco Andretti has one supported electrical "
                    "technical-state anomaly on his initial run, "
                    "followed by a later repeat attempt, but the "
                    "specific repair or service operation remains "
                    "unknown. NOT_OBSERVED must not be interpreted "
                    "as confirmed NONE."
                ),
        }
    ]

    write_csv(
        FREEZE_OUT,
        freeze_rows,
        list(
            freeze_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Separate technical-state ledger
    # --------------------------------------------------

    technical_rows = []

    if marco_ok:

        technical_rows.append({
            "technical_state_id":
                "R2E3-2022-MARCO-ELECTRICAL-01",

            "year":
                "2022",

            "driver_name":
                "Marco Andretti",

            "subject_attempt_id":
                txt(
                    marco.get(
                        "subject_attempt_id"
                    )
                ),

            "related_attempt_id":
                txt(
                    marco.get(
                        "related_attempt_id"
                    )
                ),

            "technical_issue_confirmed":
                "True",

            "technical_issue_type":
                "ELECTRICAL",

            "technical_issue_stage":
                "INITIAL_RUN",

            "later_repeat_attempt_supported":
                txt(
                    marco.get(
                        "later_repeat_attempt_supported"
                    )
                )
                or
                "True",

            "repair_action":
                "UNKNOWN",

            "pit_return":
                "UNKNOWN",

            "refuel":
                "NOT_OBSERVED",

            "cooling_service":
                "NOT_OBSERVED",

            "tire_service":
                "NOT_OBSERVED",

            "setup_adjustment":
                "NOT_OBSERVED",

            "source_name":
                txt(
                    marco.get(
                        "source_name"
                    )
                ),

            "source_class":
                txt(
                    marco.get(
                        "source_class"
                    )
                ),

            "source_title":
                txt(
                    marco.get(
                        "source_title"
                    )
                ),

            "source_url":
                txt(
                    marco.get(
                        "source_url"
                    )
                ),

            "source_quote":
                txt(
                    marco.get(
                        "source_quote"
                    )
                ),

            "evidence_quality":
                "SOURCE_NATIVE_TECHNICAL_STATE",

            "promotion_status":
                "FROZEN_R2E3",

            "notes":
                (
                    "Electrical issue is supported; "
                    "repair/service operation remains unknown."
                ),
        })

    technical_fields = [
        "technical_state_id",
        "year",
        "driver_name",
        "subject_attempt_id",
        "related_attempt_id",
        "technical_issue_confirmed",
        "technical_issue_type",
        "technical_issue_stage",
        "later_repeat_attempt_supported",
        "repair_action",
        "pit_return",
        "refuel",
        "cooling_service",
        "tire_service",
        "setup_adjustment",
        "source_name",
        "source_class",
        "source_title",
        "source_url",
        "source_quote",
        "evidence_quality",
        "promotion_status",
        "notes",
    ]

    write_csv(
        TECHNICAL_OUT,
        technical_rows,
        technical_fields,
    )

    # --------------------------------------------------
    # JSON policy output
    # --------------------------------------------------

    payload = {
        "phase":
            PHASE,

        "year":
            2022,

        "service_identifiability_status":
            service_status,

        "pit_return_support":
            (
                "SUPPORTED"
                if pit_return_confirmed
                else
                "NOT_OBSERVED"
            ),

        "service_between_attempts_support":
            (
                "SUPPORTED"
                if service_between_confirmed
                else
                "NOT_OBSERVED"
            ),

        "refuel_support":
            (
                "SUPPORTED"
                if direct_refuel
                else
                "NOT_OBSERVED"
            ),

        "cooling_service_support":
            (
                "SUPPORTED"
                if direct_cooling
                else
                "NOT_OBSERVED"
            ),

        "tire_service_support":
            (
                "SUPPORTED"
                if direct_tire
                else
                "NOT_OBSERVED"
            ),

        "adjustment_support":
            (
                "SUPPORTED"
                if direct_adjustment
                else
                "NOT_OBSERVED"
            ),

        "repair_support":
            (
                "SUPPORTED"
                if repair_confirmed
                else
                "UNKNOWN"
            ),

        "technical_state_support":
            (
                "SUPPORTED"
                if marco_ok
                else
                "NOT_READY"
            ),

        "technical_issue":
            {
                "driver":
                    "Marco Andretti"
                    if marco_ok
                    else None,

                "type":
                    "ELECTRICAL"
                    if marco_ok
                    else None,

                "stage":
                    "INITIAL_RUN"
                    if marco_ok
                    else None,
            },

        "downstream_service_policy":
            downstream_policy,

        "not_observed_means_none":
            False,

        "later_attempt_proves_repair":
            False,

        "queue_wait_can_infer_cooling":
            False,

        "exact_service_reconstruction_ready":
            False,
    }

    JSON_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    qa_rows = [
        {
            "metric":
                "local_service_promotions_zero",

            "value":
                len(
                    local_promotions
                ),

            "status":
                (
                    "PASS"
                    if len(
                        local_promotions
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "local_unresolved_direct_service_zero",

            "value":
                len(
                    unresolved_local
                ),

            "status":
                (
                    "PASS"
                    if len(
                        unresolved_local
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "marco_electrical_state_exactly_one",

            "value":
                len(
                    marco_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        marco_rows
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "direct_service_evidence_zero",

            "value":
                int(
                    direct_service_evidence
                ),

            "status":
                (
                    "PASS"
                    if not direct_service_evidence
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "service_status_not_identifiable",

            "value":
                int(
                    service_status
                    ==
                    "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
                ),

            "status":
                (
                    "PASS"
                    if service_status
                    ==
                    "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "repair_not_inferred",

            "value":
                int(
                    not repair_confirmed
                ),

            "status":
                (
                    "PASS"
                    if not repair_confirmed
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "technical_state_ledger_rows_is_1",

            "value":
                len(
                    technical_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        technical_rows
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "not_observed_not_none_policy",

            "value":
                1,

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

    success = all(
        row["status"]
        ==
        "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if success:
        print(
            "FINAL STATUS: "
            "R2E3_2022_PIT_SERVICE_IDENTIFIABILITY_FROZEN_"
            "TECHNICAL_STATE_SUPPORTED_SERVICE_UNKNOWN"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2E3_PIT_SERVICE_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(FREEZE_OUT)
    print(TECHNICAL_OUT)
    print(JSON_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
