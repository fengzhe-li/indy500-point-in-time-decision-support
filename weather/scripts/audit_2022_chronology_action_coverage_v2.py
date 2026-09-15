from pathlib import Path
import csv
from collections import defaultdict, Counter


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

LEDGER_V3 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v3.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

ACTION_LANE = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v1.csv"
)


OUTPUT_DIR = Path(
    "weather/output"
)

COVERAGE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_attempt_coverage_gap_audit_v2.csv"
)

PAIR_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_coverage_v1.csv"
)

PRIORITY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_next_rescue_priority_v2.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_chronology_action_coverage_summary_v2.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_chronology_action_coverage_v2_qa.csv"
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


def txt(v):
    return "" if v is None else str(v).strip()


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


def is_2022(row):
    return (
        txt(row.get("year")) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def to_int(v, default=999):
    try:
        return int(float(txt(v)))
    except Exception:
        return default


def get_constraint_class(row):
    return (
        txt(
            row.get(
                "constraint_class"
            )
        )
        or
        "UNKNOWN"
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.21 — 2022 CHRONOLOGY + ACTION/LANE "
        "COVERAGE AUDIT V2"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        LEDGER_V3,
        RESULT_MATCHES,
        ACTION_LANE,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

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
            "2022_CHRONOLOGY_ACTION_COVERAGE_AUDIT_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    ledger = read_csv(
        LEDGER_V3
    )

    result_matches = read_csv(
        RESULT_MATCHES
    )

    action_lane = read_csv(
        ACTION_LANE
    )

    canonical_2022 = [
        row
        for row in canonical
        if is_2022(row)
    ]

    ledger_2022 = [
        row
        for row in ledger
        if txt(
            row.get("year")
        ) == "2022"
    ]

    action_2022 = [
        row
        for row in action_lane
        if txt(
            row.get("year")
        ) == "2022"
    ]

    print()
    print(
        "CANONICAL 2022 ATTEMPTS:",
        len(canonical_2022),
    )

    print(
        "2022 CHRONOLOGY LEDGER ROWS:",
        len(ledger_2022),
    )

    print(
        "2022 ACTION/LANE ROWS:",
        len(action_2022),
    )

    print(
        "OFFICIAL RESULT LINKS:",
        len(result_matches),
    )

    # ========================================================
    # INDEXES
    # ========================================================

    evidence_by_attempt = defaultdict(list)

    for row in ledger_2022:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        if aid:
            evidence_by_attempt[
                aid
            ].append(row)

    action_by_attempt = defaultdict(list)

    for row in action_2022:

        subject = txt(
            row.get(
                "subject_attempt_id"
            )
        )

        related = txt(
            row.get(
                "related_attempt_id"
            )
        )

        if subject:
            action_by_attempt[
                subject
            ].append(row)

        if related:
            action_by_attempt[
                related
            ].append(row)

    result_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in result_matches
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    # ========================================================
    # ATTEMPT COVERAGE
    # ========================================================

    coverage_rows = []

    for can in canonical_2022:

        aid = txt(
            can.get(
                "attempt_id"
            )
        )

        evidence = evidence_by_attempt.get(
            aid,
            [],
        )

        actions = action_by_attempt.get(
            aid,
            [],
        )

        official = result_by_attempt.get(
            aid,
            {},
        )

        chronology_rows = [
            row
            for row in evidence
            if truthy(
                row.get(
                    "chronology_usable"
                )
            )
        ]

        classes = sorted(
            {
                get_constraint_class(row)
                for row in chronology_rows
            }
        )

        has_bounded = any(
            cls in {
                "BOUNDED_INTERVAL",
                "DERIVED_BOUNDED_INTERVAL",
            }
            for cls in classes
        )

        has_ordering = (
            "ORDERING_ONLY"
            in classes
        )

        has_approx = (
            "APPROXIMATE_OBSERVED"
            in classes
        )

        action_values = sorted(
            {
                txt(
                    row.get(
                        "action"
                    )
                )
                for row in actions
                if txt(
                    row.get(
                        "action"
                    )
                )
            }
        )

        lane_values = sorted(
            {
                txt(
                    row.get(
                        "lane"
                    )
                )
                for row in actions
                if txt(
                    row.get(
                        "lane"
                    )
                )
                not in {
                    "",
                    "UNKNOWN",
                }
            }
        )

        official_status = txt(
            official.get(
                "official_status"
            )
        )

        attempt_index = to_int(
            can.get(
                "car_attempt_index"
            ),
            default=0,
        )

        repeated = (
            attempt_index >= 2
        )

        decision_status = (
            official_status
            in {
                "Withdrawn",
                "Failed Attempt",
                "Waved Off",
                "No Attempt",
                "Incomplete",
                "Retired",
            }
        )

        if chronology_rows:

            if has_bounded:
                chronology_status = (
                    "TIME_BOUNDED"
                )

            elif has_approx:
                chronology_status = (
                    "APPROXIMATE_TIME"
                )

            elif has_ordering:
                chronology_status = (
                    "ORDERING_ONLY"
                )

            else:
                chronology_status = (
                    "OTHER_CHRONOLOGY"
                )

        else:
            chronology_status = (
                "NO_CHRONOLOGY"
            )

        has_action = bool(
            action_values
        )

        has_lane = bool(
            lane_values
        )

        # ====================================================
        # PRIORITY
        # ====================================================

        if (
            not chronology_rows
            and
            (
                repeated
                or
                decision_status
                or
                txt(
                    can.get(
                        "attempt_class"
                    )
                )
                == "D_CHRONOLOGY_ONLY"
            )
        ):

            priority = "HIGH"

            reason = (
                "Decision-relevant attempt has no chronology evidence."
            )

        elif (
            chronology_rows
            and
            decision_status
            and
            not has_action
        ):

            priority = "HIGH"

            reason = (
                "Chronology exists but historical action/lane "
                "semantics remain unresolved."
            )

        elif (
            repeated
            and
            chronology_rows
            and
            not has_action
        ):

            priority = "MEDIUM"

            reason = (
                "Repeated attempt chronology exists but "
                "action/lane semantics remain unresolved."
            )

        elif not chronology_rows:

            priority = "MEDIUM"

            reason = (
                "Ordinary attempt has no chronology evidence."
            )

        else:

            priority = "LOW"

            reason = (
                "Chronology coverage already present."
            )

        coverage_rows.append({
            "attempt_id":
                aid,

            "car_number":
                txt(
                    can.get(
                        "car_number"
                    )
                ),

            "driver_name":
                txt(
                    can.get(
                        "driver_name"
                    )
                ),

            "car_attempt_index":
                txt(
                    can.get(
                        "car_attempt_index"
                    )
                ),

            "speed_mph":
                txt(
                    can.get(
                        "four_lap_average_speed_mph"
                    )
                ),

            "attempt_class":
                txt(
                    can.get(
                        "attempt_class"
                    )
                ),

            "official_status":
                official_status,

            "chronology_rows":
                len(
                    chronology_rows
                ),

            "chronology_classes":
                "|".join(
                    classes
                ),

            "chronology_status":
                chronology_status,

            "has_action_evidence":
                has_action,

            "actions":
                "|".join(
                    action_values
                ),

            "has_lane_evidence":
                has_lane,

            "lanes":
                "|".join(
                    lane_values
                ),

            "repeated_attempt":
                repeated,

            "decision_status_candidate":
                decision_status,

            "rescue_priority":
                priority,

            "rescue_reason":
                reason,
        })

    # ========================================================
    # REPEAT PAIR COVERAGE
    # ========================================================

    attempts_by_car = defaultdict(list)

    for row in canonical_2022:

        idx = to_int(
            row.get(
                "car_attempt_index"
            ),
            default=0,
        )

        if idx >= 1:

            attempts_by_car[
                txt(
                    row.get(
                        "car_number"
                    )
                )
            ].append(row)

    pair_rows = []

    for car, rows in attempts_by_car.items():

        ordered = sorted(
            rows,
            key=lambda row: to_int(
                row.get(
                    "car_attempt_index"
                ),
                999,
            ),
        )

        if len(ordered) < 2:
            continue

        first = ordered[0]
        second = ordered[1]

        first_id = txt(
            first.get(
                "attempt_id"
            )
        )

        second_id = txt(
            second.get(
                "attempt_id"
            )
        )

        first_has_chronology = bool(
            evidence_by_attempt.get(
                first_id
            )
        )

        second_has_chronology = bool(
            evidence_by_attempt.get(
                second_id
            )
        )

        action_rows = []

        for row in action_2022:

            subject = txt(
                row.get(
                    "subject_attempt_id"
                )
            )

            related = txt(
                row.get(
                    "related_attempt_id"
                )
            )

            if (
                subject == first_id
                and
                related == second_id
            ):
                action_rows.append(row)

        pair_rows.append({
            "car_number":
                car,

            "driver_name":
                txt(
                    first.get(
                        "driver_name"
                    )
                ),

            "first_attempt_id":
                first_id,

            "first_speed_mph":
                txt(
                    first.get(
                        "four_lap_average_speed_mph"
                    )
                ),

            "second_attempt_id":
                second_id,

            "second_speed_mph":
                txt(
                    second.get(
                        "four_lap_average_speed_mph"
                    )
                ),

            "first_has_chronology":
                first_has_chronology,

            "second_has_chronology":
                second_has_chronology,

            "both_attempts_have_chronology":
                (
                    first_has_chronology
                    and
                    second_has_chronology
                ),

            "pair_has_action_evidence":
                bool(
                    action_rows
                ),

            "pair_actions":
                "|".join(
                    sorted(
                        {
                            txt(
                                row.get(
                                    "action"
                                )
                            )
                            for row in action_rows
                            if txt(
                                row.get(
                                    "action"
                                )
                            )
                        }
                    )
                ),

            "pair_lanes":
                "|".join(
                    sorted(
                        {
                            txt(
                                row.get(
                                    "lane"
                                )
                            )
                            for row in action_rows
                            if txt(
                                row.get(
                                    "lane"
                                )
                            )
                            not in {
                                "",
                                "UNKNOWN",
                            }
                        }
                    )
                ),
        })

    # ========================================================
    # COUNTS
    # ========================================================

    chronology_covered = sum(
        1
        for row in coverage_rows
        if row[
            "chronology_rows"
        ] > 0
    )

    chronology_uncovered = (
        len(
            coverage_rows
        )
        -
        chronology_covered
    )

    decision_total = sum(
        1
        for row in coverage_rows
        if row[
            "decision_status_candidate"
        ]
    )

    decision_chronology = sum(
        1
        for row in coverage_rows
        if (
            row[
                "decision_status_candidate"
            ]
            and
            row[
                "chronology_rows"
            ] > 0
        )
    )

    decision_action = sum(
        1
        for row in coverage_rows
        if (
            row[
                "decision_status_candidate"
            ]
            and
            row[
                "has_action_evidence"
            ]
        )
    )

    repeated_total = sum(
        1
        for row in coverage_rows
        if row[
            "repeated_attempt"
        ]
    )

    repeated_chronology = sum(
        1
        for row in coverage_rows
        if (
            row[
                "repeated_attempt"
            ]
            and
            row[
                "chronology_rows"
            ] > 0
        )
    )

    full_repeat_pairs = sum(
        1
        for row in pair_rows
        if row[
            "both_attempts_have_chronology"
        ]
    )

    action_pairs = sum(
        1
        for row in pair_rows
        if row[
            "pair_has_action_evidence"
        ]
    )

    lane_rows = sum(
        1
        for row in coverage_rows
        if row[
            "has_lane_evidence"
        ]
    )

    priority_counts = Counter(
        row[
            "rescue_priority"
        ]
        for row in coverage_rows
    )

    priority_rank = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    priority_rows = sorted(
        coverage_rows,
        key=lambda row: (
            priority_rank.get(
                row[
                    "rescue_priority"
                ],
                9,
            ),
            0
            if row[
                "decision_status_candidate"
            ]
            else 1,
            0
            if row[
                "repeated_attempt"
            ]
            else 1,
            row[
                "driver_name"
            ],
            to_int(
                row[
                    "car_attempt_index"
                ],
                999,
            ),
        ),
    )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "2022 UPDATED COVERAGE SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Chronology coverage:",
        f"{chronology_covered}/44",
        f"({chronology_covered / 44 * 100:.2f}%)",
    )

    print(
        "Chronology uncovered:",
        chronology_uncovered,
    )

    print()
    print(
        "Repeated attempts total:",
        repeated_total,
    )

    print(
        "Repeated attempts with chronology:",
        repeated_chronology,
    )

    print(
        "Repeat pairs total:",
        len(
            pair_rows
        ),
    )

    print(
        "Repeat pairs with chronology on both attempts:",
        full_repeat_pairs,
    )

    print(
        "Repeat pairs with historical action evidence:",
        action_pairs,
    )

    print()
    print(
        "Decision-status candidates:",
        decision_total,
    )

    print(
        "Decision-status candidates with chronology:",
        decision_chronology,
    )

    print(
        "Decision-status candidates with action evidence:",
        decision_action,
    )

    print(
        "Attempts with explicit historical lane evidence:",
        lane_rows,
    )

    print()
    print(
        "Priority counts:",
        dict(
            priority_counts
        ),
    )

    # ========================================================
    # REPEAT PAIRS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "REPEAT-PAIR COVERAGE"
    )
    print("=" * 120)

    for row in pair_rows:

        print()
        print(
            row[
                "driver_name"
            ],
            "| car",
            row[
                "car_number"
            ],
        )

        print(
            "  first:",
            row[
                "first_speed_mph"
            ],
            "| chronology:",
            row[
                "first_has_chronology"
            ],
        )

        print(
            "  second:",
            row[
                "second_speed_mph"
            ],
            "| chronology:",
            row[
                "second_has_chronology"
            ],
        )

        print(
            "  action evidence:",
            row[
                "pair_has_action_evidence"
            ],
        )

        print(
            "  actions:",
            row[
                "pair_actions"
            ],
        )

        print(
            "  lanes:",
            row[
                "pair_lanes"
            ],
        )

    # ========================================================
    # NEXT HIGH PRIORITY TARGETS
    # ========================================================

    high_priority = [
        row
        for row in priority_rows
        if row[
            "rescue_priority"
        ] == "HIGH"
    ]

    print()
    print("=" * 120)
    print(
        "UPDATED HIGH-PRIORITY TARGETS"
    )
    print("=" * 120)

    for row in high_priority:

        print()
        print(
            row[
                "driver_name"
            ],
            "| car",
            row[
                "car_number"
            ],
        )

        print(
            "  attempt index:",
            repr(
                row[
                    "car_attempt_index"
                ]
            ),
        )

        print(
            "  speed:",
            repr(
                row[
                    "speed_mph"
                ]
            ),
        )

        print(
            "  official status:",
            repr(
                row[
                    "official_status"
                ]
            ),
        )

        print(
            "  chronology:",
            row[
                "chronology_status"
            ],
        )

        print(
            "  action evidence:",
            row[
                "has_action_evidence"
            ],
        )

        print(
            "  lane evidence:",
            row[
                "has_lane_evidence"
            ],
        )

        print(
            "  reason:",
            row[
                "rescue_reason"
            ],
        )

    # ========================================================
    # WRITE
    # ========================================================

    coverage_fields = [
        "attempt_id",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "speed_mph",
        "attempt_class",
        "official_status",
        "chronology_rows",
        "chronology_classes",
        "chronology_status",
        "has_action_evidence",
        "actions",
        "has_lane_evidence",
        "lanes",
        "repeated_attempt",
        "decision_status_candidate",
        "rescue_priority",
        "rescue_reason",
    ]

    write_csv(
        COVERAGE_OUT,
        coverage_rows,
        coverage_fields,
    )

    write_csv(
        PRIORITY_OUT,
        priority_rows,
        coverage_fields,
    )

    write_csv(
        PAIR_OUT,
        pair_rows,
        [
            "car_number",
            "driver_name",
            "first_attempt_id",
            "first_speed_mph",
            "second_attempt_id",
            "second_speed_mph",
            "first_has_chronology",
            "second_has_chronology",
            "both_attempts_have_chronology",
            "pair_has_action_evidence",
            "pair_actions",
            "pair_lanes",
        ],
    )

    summary_rows = [
        {
            "metric":
                "canonical_attempts",
            "value":
                44,
        },
        {
            "metric":
                "chronology_covered_attempts",
            "value":
                chronology_covered,
        },
        {
            "metric":
                "chronology_uncovered_attempts",
            "value":
                chronology_uncovered,
        },
        {
            "metric":
                "repeated_attempts_total",
            "value":
                repeated_total,
        },
        {
            "metric":
                "repeated_attempts_with_chronology",
            "value":
                repeated_chronology,
        },
        {
            "metric":
                "repeat_pairs_total",
            "value":
                len(
                    pair_rows
                ),
        },
        {
            "metric":
                "repeat_pairs_both_attempts_chronology",
            "value":
                full_repeat_pairs,
        },
        {
            "metric":
                "repeat_pairs_with_action_evidence",
            "value":
                action_pairs,
        },
        {
            "metric":
                "decision_status_candidates_total",
            "value":
                decision_total,
        },
        {
            "metric":
                "decision_status_candidates_with_chronology",
            "value":
                decision_chronology,
        },
        {
            "metric":
                "decision_status_candidates_with_action",
            "value":
                decision_action,
        },
        {
            "metric":
                "explicit_lane_attempts",
            "value":
                lane_rows,
        },
        {
            "metric":
                "high_priority_targets",
            "value":
                priority_counts.get(
                    "HIGH",
                    0,
                ),
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

    # ========================================================
    # QA
    # ========================================================

    duplicate_attempt_ids = (
        len(
            coverage_rows
        )
        -
        len(
            {
                row[
                    "attempt_id"
                ]
                for row in coverage_rows
            }
        )
    )

    qa = [
        {
            "metric":
                "canonical_attempt_rows",
            "value":
                len(
                    coverage_rows
                ),
            "status":
                (
                    "PASS"
                    if len(
                        coverage_rows
                    ) == 44
                    else "FAIL"
                ),
        },
        {
            "metric":
                "duplicate_attempt_ids",
            "value":
                duplicate_attempt_ids,
            "status":
                (
                    "PASS"
                    if duplicate_attempt_ids == 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "chronology_covered_attempts",
            "value":
                chronology_covered,
            "status":
                (
                    "PASS"
                    if chronology_covered >= 10
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "historical_action_rows",
            "value":
                len(
                    action_2022
                ),
            "status":
                (
                    "PASS"
                    if len(
                        action_2022
                    ) >= 1
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "historical_lane_rows",
            "value":
                lane_rows,
            "status":
                (
                    "PASS"
                    if lane_rows >= 1
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "result_row_order_used_as_chronology",
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
                "canonical_data_mutated",
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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "2022 chronology coverage:",
        f"{chronology_covered}/44 "
        f"({chronology_covered / 44 * 100:.2f}%)",
    )

    print(
        "Full repeat-pair chronology coverage:",
        f"{full_repeat_pairs}/"
        f"{len(pair_rows)}",
    )

    print(
        "Historical action-covered repeat pairs:",
        f"{action_pairs}/"
        f"{len(pair_rows)}",
    )

    print(
        "Explicit historical lane evidence rows:",
        lane_rows,
    )

    print(
        "Remaining HIGH-priority targets:",
        len(
            high_priority
        ),
    )

    print()
    print(
        "No result-row ordering was used as chronology."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        len(
            coverage_rows
        ) == 44
        and
        duplicate_attempt_ids == 0
        and
        chronology_covered >= 10
    ):

        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_ACTION_COVERAGE_AUDIT_V2_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_ACTION_COVERAGE_AUDIT_V2_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(COVERAGE_OUT)
    print(PAIR_OUT)
    print(PRIORITY_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
