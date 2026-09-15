from pathlib import Path
import csv
import json


PHASE = "R2D.4A"

QUEUE_V1 = Path(
    "weather/output/"
    "queue_requeue_evidence_ledger_v1.csv"
)

R2D4_SUMMARY = Path(
    "weather/output/"
    "queue_rescue_2022_restart_time_anchor_summary_v1.csv"
)

R2D4_QA = Path(
    "weather/output/"
    "queue_rescue_2022_restart_time_anchor_v1_qa.csv"
)

OUTPUT_DIR = Path("weather/output")

FREEZE_OUT = (
    OUTPUT_DIR
    / "queue_wait_identifiability_2022_v1.csv"
)

JSON_OUT = (
    OUTPUT_DIR
    / "queue_wait_identifiability_2022_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "queue_wait_identifiability_2022_v1_qa.csv"
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
        "R2D.4A — 2022 HISTORICAL QUEUE-WAIT "
        "IDENTIFIABILITY FREEZE"
    )
    print("=" * 124)

    required = [
        QUEUE_V1,
        R2D4_SUMMARY,
        R2D4_QA,
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
            "R2D4A_QUEUE_WAIT_FREEZE_INPUT_MISSING"
        )
        return

    queue_rows = read_csv(
        QUEUE_V1
    )

    r2d4_summary = read_csv(
        R2D4_SUMMARY
    )

    r2d4_qa = read_csv(
        R2D4_QA
    )

    summary_map = {
        txt(row.get("metric")):
        txt(row.get("value"))
        for row in r2d4_summary
    }

    queue_exact_wait_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "queue_wait_seconds"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    queue_bounded_wait_rows = [
        row
        for row in queue_rows
        if (
            txt(
                row.get(
                    "queue_wait_lower_bound_seconds"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
            or
            txt(
                row.get(
                    "queue_wait_upper_bound_seconds"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
        )
    ]

    explicit_membership_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "queue_membership"
            )
        )
        in {
            "CONFIRMED",
            "CONFIRMED_GENERIC_LINE",
        }
    ]

    explicit_lane_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "queue_lane"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    explicit_position_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "queue_position"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    ordering_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "evidence_family"
            )
        )
        in {
            "RETAKE_RUN_ORDER",
            "RELATIVE_RUN_ORDER",
        }
    ]

    priority_time_anchors = int(
        summary_map.get(
            "priority_time_anchor_rows",
            "0",
        )
        or
        0
    )

    r2d4_exact = int(
        summary_map.get(
            "exact_queue_waits_derived",
            "0",
        )
        or
        0
    )

    r2d4_bounded = int(
        summary_map.get(
            "bounded_queue_waits_derived",
            "0",
        )
        or
        0
    )

    gap_used = int(
        summary_map.get(
            "inter_attempt_gap_used_as_wait",
            "0",
        )
        or
        0
    )

    print()
    print("=" * 124)
    print("IDENTIFIABILITY ASSESSMENT")
    print("=" * 124)

    print()
    print(
        "Queue evidence rows:",
        len(queue_rows),
    )

    print(
        "Explicit queue-membership rows:",
        len(
            explicit_membership_rows
        ),
    )

    print(
        "Explicit Lane rows:",
        len(
            explicit_lane_rows
        ),
    )

    print(
        "Explicit queue-position rows:",
        len(
            explicit_position_rows
        ),
    )

    print(
        "Run-order evidence rows:",
        len(
            ordering_rows
        ),
    )

    print()
    print(
        "Priority restart/time anchors:",
        priority_time_anchors,
    )

    print(
        "Exact queue-wait rows:",
        len(
            queue_exact_wait_rows
        ),
    )

    print(
        "Bounded queue-wait rows:",
        len(
            queue_bounded_wait_rows
        ),
    )

    print(
        "R2D4 exact waits derived:",
        r2d4_exact,
    )

    print(
        "R2D4 bounded waits derived:",
        r2d4_bounded,
    )

    print(
        "Inter-attempt gaps used as wait:",
        gap_used,
    )

    exact_identifiable = (
        len(
            queue_exact_wait_rows
        )
        >
        0
        or
        r2d4_exact
        >
        0
    )

    bounded_identifiable = (
        len(
            queue_bounded_wait_rows
        )
        >
        0
        or
        r2d4_bounded
        >
        0
    )

    queue_wait_status = (
        "HISTORICALLY_IDENTIFIABLE"
        if exact_identifiable
        else
        (
            "HISTORICALLY_BOUNDED"
            if bounded_identifiable
            else
            "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
        )
    )

    simulator_policy = (
        "OBSERVED"
        if exact_identifiable
        else
        (
            "BOUNDED_SENSITIVITY"
            if bounded_identifiable
            else
            "LATENT_SENSITIVITY_VARIABLE"
        )
    )

    print()
    print("=" * 124)
    print("FROZEN POLICY")
    print("=" * 124)

    print()
    print(
        "Historical exact queue wait:",
        (
            "IDENTIFIABLE"
            if exact_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Historical bounded queue wait:",
        (
            "IDENTIFIABLE"
            if bounded_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Queue membership:",
        "PARTIALLY_SUPPORTED",
    )

    print(
        "Queue position:",
        "PARTIALLY_SUPPORTED",
    )

    print(
        "Run ordering:",
        "PARTIALLY_SUPPORTED",
    )

    print()
    print(
        "Simulator treatment:",
        simulator_policy,
    )

    print()
    print(
        "Inter-attempt gap may be used as queue wait:",
        "NO",
    )

    print(
        "Queue-wait sensitivity values are historical truth:",
        "NO",
    )

    freeze_rows = [
        {
            "phase":
                PHASE,

            "year":
                "2022",

            "queue_wait_status":
                queue_wait_status,

            "exact_queue_wait_identifiable":
                str(
                    exact_identifiable
                ),

            "bounded_queue_wait_identifiable":
                str(
                    bounded_identifiable
                ),

            "queue_membership_support":
                "PARTIAL",

            "queue_position_support":
                "PARTIAL",

            "lane_support":
                "PARTIAL",

            "run_order_support":
                "PARTIAL",

            "priority_time_anchor_count":
                priority_time_anchors,

            "exact_queue_wait_row_count":
                len(
                    queue_exact_wait_rows
                ),

            "bounded_queue_wait_row_count":
                len(
                    queue_bounded_wait_rows
                ),

            "inter_attempt_gap_as_queue_wait":
                "PROHIBITED",

            "simulator_queue_wait_policy":
                simulator_policy,

            "sensitivity_values_are_observed_truth":
                "False",

            "exact_queue_replay_ready":
                "False",

            "queue_wait_model_calibration_ready":
                "False",

            "queue_wait_sensitivity_analysis_ready":
                "True",

            "notes":
                (
                    "Recovered 2022 evidence supports partial "
                    "queue membership, one explicit front-of-Lane1 "
                    "position, and limited run ordering. No exact "
                    "or bounded historical queue waits can be "
                    "identified from the recovered evidence. "
                    "Inter-attempt gaps must not be interpreted as "
                    "queue wait. Queue wait remains a latent "
                    "sensitivity variable for downstream simulation."
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

    payload = {
        "phase":
            PHASE,

        "year":
            2022,

        "queue_wait_status":
            queue_wait_status,

        "exact_queue_wait_identifiable":
            exact_identifiable,

        "bounded_queue_wait_identifiable":
            bounded_identifiable,

        "queue_membership_support":
            "PARTIAL",

        "queue_position_support":
            "PARTIAL",

        "lane_support":
            "PARTIAL",

        "run_order_support":
            "PARTIAL",

        "priority_time_anchor_count":
            priority_time_anchors,

        "exact_queue_wait_row_count":
            len(
                queue_exact_wait_rows
            ),

        "bounded_queue_wait_row_count":
            len(
                queue_bounded_wait_rows
            ),

        "inter_attempt_gap_as_queue_wait":
            "PROHIBITED",

        "simulator_queue_wait_policy":
            simulator_policy,

        "sensitivity_values_are_observed_truth":
            False,

        "exact_queue_replay_ready":
            False,

        "queue_wait_model_calibration_ready":
            False,

        "queue_wait_sensitivity_analysis_ready":
            True,
    }

    JSON_OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    JSON_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    qa_rows = [
        {
            "metric":
                "queue_ledger_rows",

            "value":
                len(
                    queue_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_rows
                    )
                    ==
                    5
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "priority_time_anchor_count_is_zero",

            "value":
                priority_time_anchors,

            "status":
                (
                    "PASS"
                    if priority_time_anchors
                    ==
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "exact_wait_rows_zero",

            "value":
                len(
                    queue_exact_wait_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_exact_wait_rows
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "bounded_wait_rows_zero",

            "value":
                len(
                    queue_bounded_wait_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_bounded_wait_rows
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "inter_attempt_gap_not_used",

            "value":
                gap_used,

            "status":
                (
                    "PASS"
                    if gap_used
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_wait_status_correct",

            "value":
                int(
                    queue_wait_status
                    ==
                    "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
                ),

            "status":
                (
                    "PASS"
                    if queue_wait_status
                    ==
                    "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "simulator_policy_latent",

            "value":
                int(
                    simulator_policy
                    ==
                    "LATENT_SENSITIVITY_VARIABLE"
                ),

            "status":
                (
                    "PASS"
                    if simulator_policy
                    ==
                    "LATENT_SENSITIVITY_VARIABLE"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "exact_queue_replay_ready",

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

    success = all(
        row[
            "status"
        ]
        ==
        "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if success:
        print(
            "FINAL STATUS: "
            "R2D4A_2022_QUEUE_WAIT_IDENTIFIABILITY_FROZEN_LATENT"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2D4A_QUEUE_WAIT_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(FREEZE_OUT)
    print(JSON_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
