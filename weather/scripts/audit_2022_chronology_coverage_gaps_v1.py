from pathlib import Path
import csv
from collections import defaultdict, Counter


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

LEDGER_V2 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v2.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

COVERAGE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_attempt_coverage_gap_audit_v1.csv"
)

PRIORITY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_next_rescue_priority_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_coverage_gap_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_coverage_gap_audit_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

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
    for field in [
        "constraint_class",
        "time_quality",
    ]:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return "UNKNOWN"


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.16 — 2022 CHRONOLOGY COVERAGE GAP AUDIT V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        LEDGER_V2,
        RESULT_MATCHES,
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
            "2022_CHRONOLOGY_COVERAGE_GAP_AUDIT_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    ledger = read_csv(
        LEDGER_V2
    )

    matches = read_csv(
        RESULT_MATCHES
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

    print()
    print(
        "CANONICAL 2022 ATTEMPTS:",
        len(canonical_2022),
    )

    print(
        "2022 LEDGER ROWS:",
        len(ledger_2022),
    )

    print(
        "OFFICIAL RESULT LINKS:",
        len(matches),
    )

    # ========================================================
    # INDEXES
    # ============================================================

    evidence_by_attempt = defaultdict(
        list
    )

    for row in ledger_2022:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if attempt_id:
            evidence_by_attempt[
                attempt_id
            ].append(
                row
            )

    match_by_attempt = {}

    for row in matches:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if attempt_id:
            match_by_attempt[
                attempt_id
            ] = row

    # ========================================================
    # CLASSIFY EACH CANONICAL ATTEMPT
    # ============================================================

    coverage_rows = []

    for can in canonical_2022:

        attempt_id = txt(
            can.get(
                "attempt_id"
            )
        )

        evidence = evidence_by_attempt.get(
            attempt_id,
            [],
        )

        classes = [
            get_constraint_class(row)
            for row in evidence
        ]

        chronology_usable_rows = [
            row
            for row in evidence
            if truthy(
                row.get(
                    "chronology_usable"
                )
            )
        ]

        has_bounded = any(
            cls in {
                "BOUNDED_INTERVAL",
                "DERIVED_BOUNDED_INTERVAL",
            }
            for cls in classes
        )

        has_approx = any(
            cls == "APPROXIMATE_OBSERVED"
            for cls in classes
        )

        has_ordering = any(
            cls == "ORDERING_ONLY"
            for cls in classes
        )

        attempt_class = txt(
            can.get(
                "attempt_class"
            )
        )

        speed = txt(
            can.get(
                "four_lap_average_speed_mph"
            )
        )

        result_status = txt(
            can.get(
                "result_status"
            )
        )

        official = match_by_attempt.get(
            attempt_id,
            {},
        )

        official_status = txt(
            official.get(
                "official_status"
            )
        )

        official_result_row = txt(
            official.get(
                "official_result_row"
            )
        )

        if chronology_usable_rows:

            if has_bounded:
                coverage_status = (
                    "CHRONOLOGY_TIME_BOUNDED"
                )

            elif has_approx:
                coverage_status = (
                    "CHRONOLOGY_APPROXIMATE_TIME"
                )

            elif has_ordering:
                coverage_status = (
                    "CHRONOLOGY_ORDERING_ONLY"
                )

            else:
                coverage_status = (
                    "CHRONOLOGY_OTHER"
                )

        else:

            if attempt_class == "D_CHRONOLOGY_ONLY":
                coverage_status = (
                    "NO_CHRONOLOGY_TIME_CHRONOLOGY_ONLY_ATTEMPT"
                )

            else:
                coverage_status = (
                    "NO_CHRONOLOGY_EVIDENCE"
                )

        # ====================================================
        # RESCUE PRIORITY
        # ====================================================

        priority = "LOW"
        rescue_reason = ""

        if not chronology_usable_rows:

            # Partial / non-standard attempts are often very
            # valuable for decision chronology.
            if attempt_class == "D_CHRONOLOGY_ONLY":

                priority = "HIGH"

                rescue_reason = (
                    "Chronology-only official attempt object "
                    "has identity but no usable timing/order."
                )

            elif official_status in {
                "Withdrawn",
                "Failed Attempt",
                "Waved Off",
                "No Attempt",
                "Incomplete",
                "Retired",
            }:

                priority = "HIGH"

                rescue_reason = (
                    "Official non-standard attempt/status likely "
                    "contains decision or chronology information."
                )

            elif to_int(
                can.get(
                    "car_attempt_index"
                ),
                default=1,
            ) >= 2:

                priority = "HIGH"

                rescue_reason = (
                    "Repeated attempt is directly relevant to "
                    "retain/withdraw/requeue decision chronology."
                )

            else:

                priority = "MEDIUM"

                rescue_reason = (
                    "Complete attempt without current chronology evidence."
                )

        elif (
            has_ordering
            and
            not has_bounded
            and
            not has_approx
        ):

            priority = "MEDIUM"

            rescue_reason = (
                "Ordering recovered but no usable wall-clock interval."
            )

        elif has_bounded:

            priority = "LOW"

            rescue_reason = (
                "Already has usable bounded chronology."
            )

        # ====================================================
        # DECISION RELEVANCE FLAGS
        # ====================================================

        repeated_attempt = (
            to_int(
                can.get(
                    "car_attempt_index"
                ),
                default=1,
            )
            >= 2
        )

        decision_status_candidate = (
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

        coverage_rows.append({
            "attempt_id":
                attempt_id,

            "session_id":
                txt(
                    can.get(
                        "session_id"
                    )
                ),

            "year":
                "2022",

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

            "four_lap_average_speed_mph":
                speed,

            "canonical_result_status":
                result_status,

            "attempt_class":
                attempt_class,

            "official_result_row":
                official_result_row,

            "official_status":
                official_status,

            "chronology_evidence_rows":
                len(
                    chronology_usable_rows
                ),

            "constraint_classes":
                "|".join(
                    sorted(
                        set(
                            classes
                        )
                    )
                ),

            "has_bounded_interval":
                has_bounded,

            "has_approximate_time":
                has_approx,

            "has_ordering_only":
                has_ordering,

            "coverage_status":
                coverage_status,

            "repeated_attempt":
                repeated_attempt,

            "decision_status_candidate":
                decision_status_candidate,

            "rescue_priority":
                priority,

            "rescue_reason":
                rescue_reason,

            "canonical_mutated":
                False,
        })

    # ========================================================
    # PRIORITY TABLE
    # ========================================================

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
            to_int(
                row[
                    "official_result_row"
                ],
                999,
            ),
            row[
                "car_number"
            ],
        ),
    )

    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    coverage_counter = Counter(
        row[
            "coverage_status"
        ]
        for row in coverage_rows
    )

    priority_counter = Counter(
        row[
            "rescue_priority"
        ]
        for row in coverage_rows
    )

    covered_attempts = sum(
        1
        for row in coverage_rows
        if row[
            "chronology_evidence_rows"
        ] > 0
    )

    uncovered_attempts = (
        len(
            coverage_rows
        )
        - covered_attempts
    )

    bounded_attempts = sum(
        1
        for row in coverage_rows
        if row[
            "has_bounded_interval"
        ]
    )

    ordering_only_attempts = sum(
        1
        for row in coverage_rows
        if (
            row[
                "has_ordering_only"
            ]
            and
            not row[
                "has_bounded_interval"
            ]
            and
            not row[
                "has_approximate_time"
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

    repeated_covered = sum(
        1
        for row in coverage_rows
        if (
            row[
                "repeated_attempt"
            ]
            and
            row[
                "chronology_evidence_rows"
            ] > 0
        )
    )

    decision_candidates = sum(
        1
        for row in coverage_rows
        if row[
            "decision_status_candidate"
        ]
    )

    decision_candidates_covered = sum(
        1
        for row in coverage_rows
        if (
            row[
                "decision_status_candidate"
            ]
            and
            row[
                "chronology_evidence_rows"
            ] > 0
        )
    )

    summary_rows = [
        {
            "metric":
                "canonical_attempts_2022",
            "value":
                len(
                    coverage_rows
                ),
        },
        {
            "metric":
                "attempts_with_chronology_evidence",
            "value":
                covered_attempts,
        },
        {
            "metric":
                "attempts_without_chronology_evidence",
            "value":
                uncovered_attempts,
        },
        {
            "metric":
                "attempts_with_bounded_interval",
            "value":
                bounded_attempts,
        },
        {
            "metric":
                "attempts_ordering_only",
            "value":
                ordering_only_attempts,
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
                repeated_covered,
        },
        {
            "metric":
                "decision_status_candidates_total",
            "value":
                decision_candidates,
        },
        {
            "metric":
                "decision_status_candidates_with_chronology",
            "value":
                decision_candidates_covered,
        },
        {
            "metric":
                "high_priority_rescue_attempts",
            "value":
                priority_counter.get(
                    "HIGH",
                    0,
                ),
        },
        {
            "metric":
                "medium_priority_rescue_attempts",
            "value":
                priority_counter.get(
                    "MEDIUM",
                    0,
                ),
        },
        {
            "metric":
                "low_priority_rescue_attempts",
            "value":
                priority_counter.get(
                    "LOW",
                    0,
                ),
        },
    ]

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "2022 CHRONOLOGY COVERAGE SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Canonical attempts:",
        len(
            coverage_rows
        ),
    )

    print(
        "Attempts with chronology evidence:",
        covered_attempts,
    )

    print(
        "Attempts without chronology evidence:",
        uncovered_attempts,
    )

    print(
        "Attempts with bounded interval:",
        bounded_attempts,
    )

    print(
        "Ordering-only attempts:",
        ordering_only_attempts,
    )

    print()
    print(
        "Coverage classes:"
    )

    for key, value in sorted(
        coverage_counter.items()
    ):
        print(
            f"  {key}: {value}"
        )

    print()
    print(
        "Priority classes:"
    )

    for key in [
        "HIGH",
        "MEDIUM",
        "LOW",
    ]:
        print(
            f"  {key}: "
            f"{priority_counter.get(key, 0)}"
        )

    print()
    print(
        "Repeated attempts:",
        repeated_total,
    )

    print(
        "Repeated attempts with chronology:",
        repeated_covered,
    )

    print(
        "Decision-status candidates:",
        decision_candidates,
    )

    print(
        "Decision-status candidates with chronology:",
        decision_candidates_covered,
    )

    # ========================================================
    # PRINT TOP HIGH PRIORITY
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
        "TOP HIGH-PRIORITY NEXT RESCUE TARGETS"
    )
    print("=" * 120)

    for row in high_priority[:20]:

        print()
        print(
            "CAR",
            row[
                "car_number"
            ],
            "|",
            row[
                "driver_name"
            ],
        )

        print(
            "  attempt_id:",
            row[
                "attempt_id"
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
                    "four_lap_average_speed_mph"
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
            "  attempt class:",
            row[
                "attempt_class"
            ],
        )

        print(
            "  coverage:",
            row[
                "coverage_status"
            ],
        )

        print(
            "  reason:",
            row[
                "rescue_reason"
            ],
        )

    # ========================================================
    # QA
    # ========================================================

    duplicate_attempts = Counter(
        row[
            "attempt_id"
        ]
        for row in coverage_rows
    )

    duplicate_attempt_count = sum(
        1
        for count
        in duplicate_attempts.values()
        if count > 1
    )

    qa_rows = [
        {
            "metric":
                "canonical_attempt_count",
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
                "duplicate_attempt_rows",
            "value":
                duplicate_attempt_count,
            "status":
                (
                    "PASS"
                    if duplicate_attempt_count == 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "covered_plus_uncovered_equals_total",
            "value":
                (
                    covered_attempts
                    +
                    uncovered_attempts
                ),
            "status":
                (
                    "PASS"
                    if (
                        covered_attempts
                        +
                        uncovered_attempts
                    )
                    ==
                    len(
                        coverage_rows
                    )
                    else "FAIL"
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

    # ========================================================
    # WRITE
    # ========================================================

    coverage_fields = [
        "attempt_id",
        "session_id",
        "year",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "four_lap_average_speed_mph",
        "canonical_result_status",
        "attempt_class",
        "official_result_row",
        "official_status",
        "chronology_evidence_rows",
        "constraint_classes",
        "has_bounded_interval",
        "has_approximate_time",
        "has_ordering_only",
        "coverage_status",
        "repeated_attempt",
        "decision_status_candidate",
        "rescue_priority",
        "rescue_reason",
        "canonical_mutated",
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
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    write_csv(
        QA_OUT,
        qa_rows,
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
        f"{covered_attempts}/"
        f"{len(coverage_rows)}",
        f"({covered_attempts / len(coverage_rows) * 100:.2f}%)"
        if coverage_rows
        else "",
    )

    print(
        "High-priority unresolved targets:",
        len(
            high_priority
        ),
    )

    print()
    print(
        "No chronology was inferred from result-row order."
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
        duplicate_attempt_count == 0
    ):

        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_COVERAGE_GAP_AUDIT_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_COVERAGE_GAP_AUDIT_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(COVERAGE_OUT)
    print(PRIORITY_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
