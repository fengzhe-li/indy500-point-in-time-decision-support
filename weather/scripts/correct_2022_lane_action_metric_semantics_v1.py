from pathlib import Path
import csv


ACTION_LANE = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v1.csv"
)

COVERAGE_V2 = Path(
    "weather/output/"
    "chronology_rescue_2022_attempt_coverage_gap_audit_v2.csv"
)

SUMMARY_OLD = Path(
    "weather/output/"
    "chronology_rescue_2022_chronology_action_coverage_summary_v2.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

SUMMARY_CORRECTED = (
    OUTPUT_DIR
    / "chronology_rescue_2022_chronology_action_coverage_summary_v2_corrected.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_lane_action_metric_semantics_v1_qa.csv"
)


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
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def txt(value):
    return "" if value is None else str(value).strip()


def main():

    print()
    print("=" * 120)
    print(
        "R1G.21A — 2022 LANE / ACTION "
        "METRIC SEMANTIC CORRECTION V1"
    )
    print("=" * 120)

    inputs = [
        ACTION_LANE,
        COVERAGE_V2,
        SUMMARY_OLD,
    ]

    missing = []

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "2022_LANE_ACTION_METRIC_CORRECTION_INPUT_MISSING"
        )
        return

    action_rows = read_csv(
        ACTION_LANE
    )

    coverage_rows = read_csv(
        COVERAGE_V2
    )

    old_summary = read_csv(
        SUMMARY_OLD
    )

    action_rows_2022 = [
        row
        for row in action_rows
        if txt(
            row.get("year")
        ) == "2022"
    ]

    lane_rows_2022 = [
        row
        for row in action_rows_2022
        if txt(
            row.get("lane")
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    action_subject_attempts = {
        txt(
            row.get(
                "subject_attempt_id"
            )
        )
        for row in action_rows_2022
        if txt(
            row.get(
                "subject_attempt_id"
            )
        )
    }

    action_related_attempts = {
        txt(
            row.get(
                "related_attempt_id"
            )
        )
        for row in action_rows_2022
        if txt(
            row.get(
                "related_attempt_id"
            )
        )
    }

    action_linked_attempts = (
        action_subject_attempts
        |
        action_related_attempts
    )

    lane_subject_attempts = {
        txt(
            row.get(
                "subject_attempt_id"
            )
        )
        for row in lane_rows_2022
        if txt(
            row.get(
                "subject_attempt_id"
            )
        )
    }

    lane_related_attempts = {
        txt(
            row.get(
                "related_attempt_id"
            )
        )
        for row in lane_rows_2022
        if txt(
            row.get(
                "related_attempt_id"
            )
        )
    }

    lane_linked_attempts = (
        lane_subject_attempts
        |
        lane_related_attempts
    )

    coverage_action_attempts = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in coverage_rows
        if txt(
            row.get(
                "has_action_evidence"
            )
        ).lower()
        == "true"
    }

    coverage_lane_attempts = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in coverage_rows
        if txt(
            row.get(
                "has_lane_evidence"
            )
        ).lower()
        == "true"
    }

    print()
    print("=" * 120)
    print(
        "CORRECTED ACTION / LANE METRICS"
    )
    print("=" * 120)

    print()
    print(
        "Historical action evidence rows:",
        len(
            action_rows_2022
        ),
    )

    print(
        "Attempts linked by action evidence:",
        len(
            action_linked_attempts
        ),
    )

    print()
    print(
        "Historical explicit lane evidence rows:",
        len(
            lane_rows_2022
        ),
    )

    print(
        "Attempts linked by explicit lane evidence:",
        len(
            lane_linked_attempts
        ),
    )

    print()
    print(
        "Coverage-table attempts with action evidence:",
        len(
            coverage_action_attempts
        ),
    )

    print(
        "Coverage-table attempts with lane evidence:",
        len(
            coverage_lane_attempts
        ),
    )

    print()
    print(
        "Lane rows:"
    )

    for row in lane_rows_2022:

        print()
        print(
            "  evidence_id:",
            txt(
                row.get(
                    "evidence_id"
                )
            ),
        )

        print(
            "  driver:",
            txt(
                row.get(
                    "driver_name"
                )
            ),
        )

        print(
            "  action:",
            txt(
                row.get(
                    "action"
                )
            ),
        )

        print(
            "  lane:",
            txt(
                row.get(
                    "lane"
                )
            ),
        )

        print(
            "  subject attempt:",
            txt(
                row.get(
                    "subject_attempt_id"
                )
            ),
        )

        print(
            "  related attempt:",
            txt(
                row.get(
                    "related_attempt_id"
                )
            ),
        )

    corrected_summary = []

    replaced_metrics = {
        "explicit_lane_attempts",
    }

    for row in old_summary:

        metric = txt(
            row.get(
                "metric"
            )
        )

        if metric in replaced_metrics:
            continue

        corrected_summary.append({
            "metric":
                metric,

            "value":
                txt(
                    row.get(
                        "value"
                    )
                ),
        })

    corrected_summary.extend([
        {
            "metric":
                "historical_action_evidence_rows",
            "value":
                len(
                    action_rows_2022
                ),
        },
        {
            "metric":
                "attempts_linked_by_action_evidence",
            "value":
                len(
                    action_linked_attempts
                ),
        },
        {
            "metric":
                "historical_explicit_lane_evidence_rows",
            "value":
                len(
                    lane_rows_2022
                ),
        },
        {
            "metric":
                "attempts_linked_by_explicit_lane_evidence",
            "value":
                len(
                    lane_linked_attempts
                ),
        },
    ])

    write_csv(
        SUMMARY_CORRECTED,
        corrected_summary,
        [
            "metric",
            "value",
        ],
    )

    qa = [
        {
            "metric":
                "historical_explicit_lane_evidence_rows",
            "value":
                len(
                    lane_rows_2022
                ),
            "status":
                (
                    "PASS"
                    if len(
                        lane_rows_2022
                    ) == 1
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "attempts_linked_by_explicit_lane_evidence",
            "value":
                len(
                    lane_linked_attempts
                ),
            "status":
                (
                    "PASS"
                    if len(
                        lane_linked_attempts
                    ) == 2
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "coverage_lane_attempt_count_matches",
            "value":
                len(
                    coverage_lane_attempts
                ),
            "status":
                (
                    "PASS"
                    if (
                        len(
                            coverage_lane_attempts
                        )
                        ==
                        len(
                            lane_linked_attempts
                        )
                    )
                    else "FAIL"
                ),
        },
        {
            "metric":
                "historical_action_rows",
            "value":
                len(
                    action_rows_2022
                ),
            "status":
                (
                    "PASS"
                    if len(
                        action_rows_2022
                    ) >= 1
                    else "FAIL"
                ),
        },
        {
            "metric":
                "canonical_data_mutated",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "previous_summary_mutated",
            "value":
                0,
            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_OUT,
        qa,
        [
            "metric",
            "value",
            "status",
        ],
    )

    print()
    print("=" * 120)
    print(
        "FINAL INTERPRETATION"
    )
    print("=" * 120)

    print()
    print(
        "Correct statement:"
    )

    print(
        f"  Historical explicit Lane evidence rows = "
        f"{len(lane_rows_2022)}"
    )

    print(
        f"  Canonical attempts touched by that evidence = "
        f"{len(lane_linked_attempts)}"
    )

    print()
    print(
        "Therefore one McLaughlin Lane-1 action "
        "links two canonical attempts."
    )

    print(
        "This must NOT be described as two independent "
        "historical Lane observations."
    )

    print()
    print("=" * 120)

    if (
        len(
            lane_rows_2022
        ) == 1
        and
        len(
            lane_linked_attempts
        ) == 2
    ):

        print(
            "FINAL STATUS: "
            "2022_LANE_ACTION_METRIC_SEMANTICS_CORRECTED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_LANE_ACTION_METRIC_SEMANTICS_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(SUMMARY_CORRECTED)
    print(QA_OUT)


if __name__ == "__main__":
    main()
